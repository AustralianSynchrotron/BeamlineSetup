'''
#IMPORT LIBRARIES AND SET UP PATHS
'''

import wx, sys, logging, wx.lib.dialogs, ssh, epics, urllib, ast, shutil, time, os, subprocess, getpass
from os.path import isfile as isfile
from os.path import isdir as isdir
from subprocess import call, Popen, PIPE, STDOUT, check_output
from SetUp import SetUp as SetUp
from redisobj import RedisHashMap
#from PIL import Image

#try: 
#    sys.path.index('/xray/progs/mxpylib')
#except (ValueError, TypeError):
#    sys.path.insert(0,'/xray/progs/mxpylib')

try: 
    sys.path.index('/xray/progs/Python/libraries/')
except (ValueError, TypeError):
    sys.path.insert(0,'/xray/progs/Python/libraries/')

from beamline import variables as blconfig


class Align():
    """Sets up for a new rotation axis alignment job
    
    The Setup class functions are for setting up for a new rotation axis alignment
    job.
    """
    
    '''
    Constructor
    '''
    def __init__(self,param_dict):
        self.user = getpass.getuser()
        self.delete_list = []
        self.correcting = "Yes"
        self.param_dict = param_dict
        ###start a log file
        self.logger = logging.getLogger('beamline_setup')
        self.logger.info('Starting a new rotation axis alignment job')

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
        response = wx.lib.dialogs.messageDialog(title='Rotation Axis', message='Please mount and centre a normal loop or acupuncture needle. Cancel will cause this step to skip.')
        #app.Yield()
        #del app
        if response.returnedString == "Cancel":
            self.logger.info('Skipping rotation axis due to user input')
            sys.exit()

        ###define camera IP addresses and Omega axis PV for beamlines
        if blconfig.ID == "MX1":
            self.pixel_micron_conversion = -1.7333
            self.slump_tolerance = 10
            self.camera_url = "http://10.109.2.36:8080/XTAL.OVER.jpg"
            self.omega_pv = "SR03BM01GON01:OMEGA_MTR_SP"
            self.goni_y_sp = "SR03BM01GON01:Y_MTR_SP"
            self.goni_y_mon = "SR03BM01GON01:Y_MTR_MON"
            self.goni_y_proc = "SR03BM01GON01:Y_MTR_MV_CMD.PROC "
            #self.roistartx_pv = epics.PV("03BM:XTAL:ROI1:MinX_RBV")
            #self.roistarty_pv = epics.PV("03BM:XTAL:ROI1:MinY_RBV")
            #self.roisizex_pv = epics.PV("03BM:XTAL:ROI1:SizeX_RBV")
            #self.roisizey_pv = epics.PV("03BM:XTAL:ROI1:SizeY_RBV")
            self.crosshairx_pv = epics.PV("03BM:XTAL:cursor1:CursorX")
            self.crosshairy_pv = epics.PV("03BM:XTAL:cursor1:CursorY")
        
        else:
            #self.pixel_micron_conversion = -2.8003
            self.pixel_micron_conversion = -2.9264
            self.slump_tolerance = 3
            self.camera_url = "http://10.108.2.53:8080/XTAL.OVER.jpg"
            self.omega_pv = "SR03ID01GON01:OMEGA_MTR_SP"
            self.goni_y_sp = "SR03ID01GON01:Y_MTR_SP"
            self.goni_y_mon = "SR03ID01GON01:Y_MTR_MON"
            self.goni_y_proc = "SR03ID01GON01:Y_MTR_MV_CMD.PROC "
            #self.roistartx_pv = epics.PV("03ID:XTAL:ROI1:MinX_RBV")
            #self.roistarty_pv = epics.PV("03ID:XTAL:ROI1:MinY_RBV")
            #self.roisizex_pv = epics.PV("03ID:XTAL:ROI1:SizeX_RBV")
            #self.roisizey_pv = epics.PV("03ID:XTAL:ROI1:SizeY_RBV")
            self.crosshairx_pv = epics.PV("03ID:XTAL:cursor1:CursorX")
            self.crosshairy_pv = epics.PV("03ID:XTAL:cursor1:CursorY")
        
        ###get values for xtal pic parameters
        try:
            #self.roistartx = int(self.roistartx_pv.get())
            #self.roistarty = int(self.roistarty_pv.get())
            #self.roisizex = int(self.roisizex_pv.get())
            #self.roisizey = int(self.roisizey_pv.get())
            self.crosshairx = int(self.crosshairx_pv.get())
            self.crosshairy = int(self.crosshairy_pv.get())
        except:
            sys.exit("can't get crystal pics settings")
    
    
    def Take_Images(self, angles):
        if self.correcting == "No":
            return
        else:
            self.logger.info('Taking images')
            
        self.angles = angles
        self.logger.info('taking images at '+str(' '.join(map(str, self.angles)))+' degrees')
        self.imagenames = []
        self.montage_command = []

        for angle in self.angles:
            imagename = '/var/tmp/'+str(self.user)+'_rotation_axis_'+str(angle).zfill(4)+'deg.jpg'
            self.delete_list.append(imagename)
            self.imagenames.append(imagename)
            self.montage_command.append('\( '+str(imagename)+' -set label "Postion at '+str(angle)+' degrees" \) ')
            epics.caput(self.omega_pv,angle, wait=True)
            imagefile = urllib.urlopen(self.camera_url)
            image = imagefile.read()
            outfile =open(imagename, 'w')
            outfile.write(image)
            outfile.close()
            self.logger.info('written '+str(imagename))

        
    def Analyse_Images(self):
        if self.correcting == "No":
            return
        else:
            self.logger.info('Analysing images')

         ###get image size
        self.imagenames.sort()
        im_command = 'identify '+str(self.imagenames[0])
        im_return = check_output(im_command, shell=True)
        
        self.imagesizex = int(im_return.split(' ')[2].split('x')[0])
        self.imagesizey = int(im_return.split(' ')[2].split('x')[1])

        ###FOR IMAGES 0 and 180

        ###make the search space image
        self.logger.info('finding rotation axis mis-setting from images at 0 and 180 degrees')
        self.searchspace_image = '/var/tmp/'+str(self.user)+'_searchspace.jpg'
        self.delete_list.append('/var/tmp/'+str(self.user)+'_searchspace.jpg')
        xsize = int(self.imagesizex / 16)
        #ysize = int(self.imagesizey)
        ysize = int(2 * min((self.imagesizey - self.crosshairy),self.crosshairy))
        self.si_ysize = ysize
        xoffset = int(self.crosshairx - (xsize / 2))
        yoffset = int(self.crosshairy - ysize / 2)

        im_command = 'convert -crop '+str(xsize)+'x'+str(ysize)+'+'+str(xoffset)+'+'+str(yoffset)+' '+str(self.imagenames[0])+' '+str(self.searchspace_image)
        call(im_command, shell=True)

        ###make the moving search image
        self.moving_image = '/var/tmp/'+str(self.user)+'_movingimage.jpg'
        self.delete_list.append(self.moving_image)
        xsize = int(self.imagesizex / 16)
        ysize = int(self.imagesizey / 2)
        self.mi_ysize = ysize
        xoffset = int(self.crosshairx - (xsize / 2))
        #yoffset = int((self.imagesizey - ysize) / 2)
        yoffset = int(self.crosshairy - ysize / 2)
        #yoffset = 0
        
        im_command = 'convert -crop '+str(xsize)+'x'+str(ysize)+'+'+str(xoffset)+'+'+str(yoffset)+' -flip '+str(self.imagenames[2])+' '+str(self.moving_image)
        call(im_command, shell=True)


        ###superimpose the two
        im_command = 'compare -metric RMSE -subimage-search '+str(self.searchspace_image)+' '+str(self.moving_image)+' /var/tmp/'+str(self.user)+'_temp.gif'
        self.delete_list.append('/var/tmp/'+str(self.user)+'_temp.gif')
        p = Popen(im_command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        im_output = p.stdout.read()
        self.search_offset = int(im_output.split(' ')[3].split(',')[1])

        ###calculate offset in pixels
        ideal_offset = (self.si_ysize - self.mi_ysize) / 2
        self.axis_offset = ( ideal_offset - self.search_offset ) / self.pixel_micron_conversion
        
        self.logger.info('rotation axis is off by '+str(self.axis_offset)+' microns.')

        ###FOR IMAGES 90 and 270
        self.logger.info('finding the magnitude of slump in the sample stages from images at 90 and 270 microns')
        ###make the search space image
        self.searchspace_image = '/var/tmp/'+str(self.user)+'_searchspace.jpg'
        self.delete_list.append(self.searchspace_image)
        xsize = int(self.imagesizex / 16)
        #ysize = int(self.imagesizey)
        ysize = int(2 * min((self.imagesizey - self.crosshairy),self.crosshairy))
        self.si_ysize = ysize
        xoffset = int(self.crosshairx - (xsize / 2))
        yoffset = int(self.crosshairy - ysize / 2)

        im_command = 'convert -crop '+str(xsize)+'x'+str(ysize)+'+'+str(xoffset)+'+'+str(yoffset)+' '+str(self.imagenames[1])+' '+str(self.searchspace_image)
        call(im_command, shell=True)

        ###make the moving search image
        self.moving_image = '/var/tmp/'+str(self.user)+'_movingimage.jpg'
        self.delete_list.append(self.moving_image)
        xsize = int(self.imagesizex / 16)
        ysize = int(self.imagesizey / 2)
        self.mi_ysize = ysize
        xoffset = int(self.crosshairx - (xsize / 2))
        #yoffset = int((self.imagesizey - ysize) / 2)
        yoffset = int(self.crosshairy - ysize / 2)
        #yoffset = 0
        
        im_command = 'convert -crop '+str(xsize)+'x'+str(ysize)+'+'+str(xoffset)+'+'+str(yoffset)+' -flip '+str(self.imagenames[3])+' '+str(self.moving_image)
        call(im_command, shell=True)


        ###superimpose the two
        im_command = 'compare -metric RMSE -subimage-search '+str(self.searchspace_image)+' '+str(self.moving_image)+' /var/tmp/'+str(self.user)+'_temp.gif'
        self.delete_list.append('/var/tmp/'+str(self.user)+'_temp.gif')
        p = Popen(im_command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        im_output = p.stdout.read()
        self.search_offset = int(im_output.split(' ')[3].split(',')[1])

        ###calculate offset in pixels
        ideal_offset = (self.si_ysize - self.mi_ysize) / 2
        self.slump = ( ( ideal_offset - self.search_offset ) / self.pixel_micron_conversion ) - self.axis_offset
        self.param_dict['rotationaxis_slump'] = self.slump
        self.logger.info('found a slump of '+str(self.slump)+' microns in sample stages')


    def Correct_Axis(self):
        self.old_sp = round(epics.caget(self.goni_y_mon),3)
        self.param_dict['rotationaxis_old_posn'] = self.old_sp
        self.new_sp = round((float(self.old_sp) + float(self.axis_offset)),3)
        self.param_dict['rotationaxis_new_posn'] = self.new_sp
        #self.new_sp = round((float(self.old_sp) + float(-30.5775)),3)

        #self.montage_command.reverse()
        timestamp = time.strftime("%d-%m-%Y %H:%M:%S")
        im_command = 'montage -font Bookman-DemiItalic '+' '.join(self.montage_command)+' -title "Rotation axis alignment performed on '+str(timestamp)+' " -tile 2x2 -frame 5 -geometry "400x400+5+5" /var/tmp/'+str(self.user)+'_rotation_axis_montage.jpg'
        self.delete_list.append('/var/tmp/'+str(self.user)+'_rotation_axis_montage.jpg')
        call(im_command, shell=True)

        #im = Image.open('/var/tmp/'+str(self.user)+'_rotation_axis_montage.jpg')
        #im.show()

        command = 'eog /var/tmp/'+str(self.user)+'_rotation_axis_montage.jpg&'
        subprocess.call(command, shell=True)
        
        #app = wx.PySimpleApp()
        response = wx.lib.dialogs.messageDialog(title='YES/NO', message='Do you want to move goni base Y from '+str(self.old_sp)+' to '+str(self.new_sp)+'?', aStyle=wx.YES_NO)
        #wx.app.Yield() #this doesn't work, need to work out how to refer to app
        if response.accepted:
            self.logger.info('moving goni base Y from '+str(self.old_sp)+' to '+str(self.new_sp))
            self.correcting = "Yes"
            epics.caput(self.goni_y_sp,self.new_sp)
            epics.caput(self.goni_y_proc,1)
            ###will have to retake images for log
        else:
            self.correcting = "No"
            self.logger.info('will not move goni base Y')

        if abs(self.slump) > self.slump_tolerance:
            self.logger.info('The slump in the sample stages is larger than '+str(self.slump_tolerance)+' microns, you should fix this.')
        else:
            self.logger.info('The slump in the sample stages is within the tolerance threshold of '+str(self.slump_tolerance)+' microns.')

    def Save_Results(self):
        if self.correcting == "No":
            #self.logger.info('Will not save images in log')
            #return
            self.logger.info('Saving images to log')
        else:
            self.montage_command.reverse()
            self.logger.info('Taking new images for the log')

        ###crop images

        for imagename in self.imagenames:
            shutil.copyfile(imagename, '/var/tmp/'+str(self.user)+'_temp.jpg')
            self.delete_list.append('/var/tmp/'+str(self.user)+'_temp.jpg')
            im_command = 'identify /var/tmp/'+str(self.user)+'_temp.jpg'
            p = Popen(im_command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
            im_output = p.stdout.read().split(' ')[2].split('x')
            sizex = 400
            sizey = 400
            offsetx = (( int(im_output[0]) - 400 ) / 2 )
            offsety = (( int(im_output[1]) - 400 ) / 2 )

            im_command = 'convert /var/tmp/'+str(self.user)+'_temp.jpg -crop '+str(sizex)+'x'+str(sizey)+'+'+str(offsetx)+'+'+str(offsety)+' '+str(imagename)
            call(im_command, shell=True)
            self.logger.info('Cropped image '+str(imagename))


        timestamp = time.strftime("%d-%m-%Y %H:%M:%S")
        im_command = 'montage -font Bookman-DemiItalic '+' '.join(self.montage_command)+' -title "Rotation axis alignment performed on '+str(timestamp)+' " -tile 2x2 -frame 5 -geometry "400x400+5+5" /var/tmp/'+str(self.user)+'_rotation_axis_montage.jpg'
        self.delete_list.append('/var/tmp/'+str(self.user)+'_rotation_axis_montage.jpg')
        call(im_command, shell=True)

        ###transfer output image to users calibration dir
        timestamp = time.strftime("%y-%m-%d-%H-%M")
        ###transfer output image to /data/home/calibration dir
        local_file = '/var/tmp/'+str(self.user)+'_rotation_axis_montage.jpg'
        remote_file2 = '/data/home/calibration/rotation_axis_montage.jpg'
        remote_file3 = '/data/home/calibration/rotation_axis/'+str(timestamp)+'_rotation_axis_montage.jpg'
        sshc = ssh.SSHClient()
        sshc.set_missing_host_key_policy(ssh.AutoAddPolicy())
        sshc.connect('localhost', username='blctl', password=str(self.param_dict['password']))
        stdin, stdout, stderr = sshc.exec_command('cp '+local_file+' '+remote_file2)
        self.logger.info('Wrote output to '+str(remote_file2))
        stdin, stdout, stderr = sshc.exec_command('cp '+local_file+' '+remote_file3)
        self.logger.info('Wrote output to '+str(remote_file3))
        sshc.close()

        self.imagenames.reverse()
        
        #define right hashmap for right beamline
        if blconfig.ID == "MX1":
            self.mymap = RedisHashMap('mx1_beamline_setup')            
        else:
            self.mymap = RedisHashMap('mx2_beamline_setup')

        self.mymap['RotationAxisDate'] = time.time()

    def CleanTempFiles(self):
        time.sleep(2)#it was deleting the temp files before they'd been copied to /data/home/calibration!
        no_duplicates = list(set(self.delete_list))
        #all files in delete_list are in /var/tmp/ dir
        for file in no_duplicates:
            try:
                os.remove(file)
                self.logger.info('Removed file '+file)
            except:
                self.logger.info('Could not delete '+file)

    def Output_Results(self):
        return self.param_dict
        


if __name__ == '__main__':
    app = wx.PySimpleApp()
    align = Align('NotDefined')
    align.Take_Images([0,90,180,270])
    align.Analyse_Images()
    align.Correct_Axis()
    align.Take_Images([270,180,90,0])
    align.Analyse_Images()
    align.Save_Results()
    align.CleanTempFiles()
    del app


