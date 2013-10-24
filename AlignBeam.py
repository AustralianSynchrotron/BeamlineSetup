'''
#IMPORT LIBRARIES AND SET UP PATHS
'''

import wx, sys, logging, wx.lib.dialogs, ssh, epics, urllib, ast, time, os, getpass
from time import strftime
from os.path import isfile as isfile
from os.path import isdir as isdir
from subprocess import call, Popen, PIPE, STDOUT, check_output
from SetUp import SetUp as SetUp
from redisobj import RedisHashMap
###define beamline specific variables such as beamline, EPN etc
#from epics import PV as PV

try: 
    sys.path.index('/xray/progs/mxpylib')
except (ValueError, TypeError):
    sys.path.insert(0,'/xray/progs/mxpylib')

try: 
    sys.path.index('/xray/progs/Python/libraries/')
except (ValueError, TypeError):
    sys.path.insert(0,'/xray/progs/Python/libraries/')

from beamline import variables as blconfig


class Align():
    """Sets up for a new beam alignment job
    
    The Setup class functions prompt for the beam to be manually aligned on a
    YAG at the sample position and take images for the log.
    """
    
    '''
    Constructor
    '''
    def __init__(self,param_dict):
        self.user = getpass.getuser()
        self.delete_list = []
        self.param_dict = param_dict
        ###start a log file
        self.logger = logging.getLogger('beamline_setup')
        self.logger.info('Starting a new beam alignment job')

        try:
            if 'password' in self.param_dict:
                pass
            else:
                m = SetUp()
                m.DefineParameters()
                m.GetPassword()
                self.param_dict = m.ReturnDictionary()
        except:
            m = SetUp()
            m.DefineParameters()
            m.GetPassword()
            self.param_dict = m.ReturnDictionary()

        #app = wx.PySimpleApp()
        response = wx.lib.dialogs.messageDialog(title='Beam Alignment', message='Please mount a YAG at the sample position, align the beam and set references for beamsteering. Leave the YAG in position and the shutters open for harvesting images. Cancel will cause this step to skip.')
        #app.Yield()
        #del app

        if response.returnedString == "Cancel":
            self.logger.info('Skipping beam alignment due to user input')
            sys.exit()

        ###define camera IP addresses and Omega axis PV for beamlines
        if blconfig.ID == "MX1":
            self.samplecamera_url = "http://10.109.2.36:8080/XTAL.OVER.jpg"
            self.beamcamera_url = "http://10.109.2.36:8080/BEAM.MJPG.jpg"
            self.shutterpv = "SR03BM01SH01:SHUT_CMD"
            self.open = 0
            self.close = 1
        else:
            self.samplecamera_url = "http://10.108.2.53:8080/XTAL.OVER.jpg"
            self.beamcamera_url = "http://10.108.2.53:8080/BEAM.MJPG.jpg"
            self.shutterpv = "SR03ID01SH01:SHUT_CMD"        
            self.open = 0
            self.close = 1
            self.collimatorpv = "SR03ID01HU03COL01:MCOL_SP"
            collpos = epics.caget(self.collimatorpv)
            if collpos != 5:
                #app = wx.PySimpleApp()
                response = wx.lib.dialogs.messageDialog(title='Align beam', message='The microcollimator is not at full beam, would you like to move to full beam?')
                #app.Yield()
                #del app
                if response.returnedString == 'Yes':
                    epics.caput(self.collimatorpv,5,wait=True)
                    self.logger.info('Moved collimator to position 5')
                else:
                    self.logger.info('Left collimator at position '+str(collpos))

    def TakeImages(self):
        self.beamimage_sample = '/var/tmp/'+str(self.user)+'_temp.jpg'
        self.delete_list.append('/var/tmp/'+str(self.user)+'_temp.jpg')
        epics.caput(self.shutterpv,self.open)
        time.sleep(1)
        imagefile = urllib.urlopen(self.samplecamera_url)
        image = imagefile.read()
        outfile =open(self.beamimage_sample, 'w')
        outfile.write(image)
        outfile.close()
        self.logger.info('written '+str(self.beamimage_sample))
        im_command = 'identify /var/tmp/'+str(self.user)+'_temp.jpg'
        p = Popen(im_command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        im_output = p.stdout.read().split(' ')[2].split('x')
        sampleimage_x = int(im_output[0])
        sampleimage_y = int(im_output[1])

        self.beamimage_shutter = '/var/tmp/'+str(self.user)+'_beamimage.jpg'
        self.delete_list.append(self.beamimage_shutter)
        epics.caput(self.shutterpv,self.close)
        time.sleep(3)
        imagefile = urllib.urlopen(self.beamcamera_url)
        image = imagefile.read()
        outfile =open(self.beamimage_shutter, 'w')
        outfile.write(image)
        outfile.close()
        self.logger.info('written '+str(self.beamimage_shutter))
        im_command = 'identify /var/tmp/'+str(self.user)+'_beamimage.jpg'
        p = Popen(im_command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        im_output = p.stdout.read().split(' ')[2].split('x')
        self.beamimage_x = int(im_output[0])
        self.beamimage_y = int(im_output[1])

        offset_x = int(( sampleimage_x - self.beamimage_x ) / 2)
        offset_y = int(( sampleimage_y - self.beamimage_y ) / 2)
        im_command = 'convert /var/tmp/'+str(self.user)+'_temp.jpg -crop '+str(self.beamimage_x)+'x'+str(self.beamimage_y)+'+'+str(offset_x)+'+'+str(offset_y)+' /var/tmp/'+str(self.user)+'_sampleimage.jpg'
        self.delete_list.append('/var/tmp/'+str(self.user)+'_sampleimage.jpg')
        call(im_command, shell=True)
        self.logger.info('Cropped sample YAG image to be same size as beam YAG image')

    def SaveResults(self):
        self.logger.info('Preparing image for the log')
        timestamp = strftime("%d-%m-%Y %H:%M:%S")
        im_command = 'montage -font Bookman-DemiItalic \( /var/tmp/'+str(self.user)+'_sampleimage.jpg -set label "Beam image at sample position" \) \( /var/tmp/'+str(self.user)+'_beamimage.jpg -set label "Beam image at the steering YAG" \) -title "Beam alignment performed on '+str(timestamp)+'" -tile 2x1 -frame 5 -geometry "'+str(self.beamimage_x)+'x'+str(self.beamimage_y)+'+5+5" /var/tmp/'+str(self.user)+'_beamalignment_montage.jpg'
        self.delete_list.append('/var/tmp/'+str(self.user)+'_beamalignment_montage.jpg')
        call(im_command, shell=True)
        ###transfer output image to users calibration dir
        timestamp = strftime("%y-%m-%d-%H-%M")
        #local_file = '/var/tmp/'+str(self.user)+'_beamalignment_montage.jpg'
        #remote_file1 = str(self.param_dict['calibrationDir'])+'beam_image/beamalignment_montage.jpg'
        #t = ssh.Transport((self.param_dict['fileserverIP'],22))
        #t.connect(username=str(self.param_dict['username']), password=str(self.param_dict['password']))
        #sftp = ssh.SFTPClient.from_transport(t)
        #sftp.put(local_file, remote_file1)
        #t.close()

        ###transfer output image to /data/home/calibration dir
        local_file = '/var/tmp/'+str(self.user)+'_beamalignment_montage.jpg'
        remote_file2 = '/data/home/calibration/beamalignment_montage.jpg'
        remote_file3 = '/data/home/calibration/beam_image/'+str(timestamp)+'beamalignment_montage.jpg'
        sshc = ssh.SSHClient()
        sshc.set_missing_host_key_policy(ssh.AutoAddPolicy())
        sshc.connect('localhost', username='blctl', password=str(self.param_dict['password']))
        stdin, stdout, stderr = sshc.exec_command('cp '+local_file+' '+remote_file2)
        self.logger.info('written '+remote_file2)
        stdin, stdout, stderr = sshc.exec_command('cp '+local_file+' '+remote_file3)
        self.logger.info('written '+remote_file3)        
        sshc.close()

        #define right hashmap for right beamline
        if blconfig.ID == "MX1":
            self.mymap = RedisHashMap('mx1_beamline_setup')            
        else:
            self.mymap = RedisHashMap('mx2_beamline_setup')

        self.mymap['AlignBeamDate'] = time.time()

    def CleanTempFiles(self):
        time.sleep(2)#it was deleting the temp files before they'd been copied to /data/home/calibration!
        no_duplicates = list(set(self.delete_list))
        for file in no_duplicates:
            os.remove(file)
            #try:
            #    os.remove(file)
            #except:
            #    self.logger.info('Could not delete '+file)

    def Output_Results(self):
        return self.param_dict

if __name__ == '__main__':
    app = wx.PySimpleApp()
    align = Align('NotDefined')
    align.TakeImages()
    align.SaveResults()
    del app


