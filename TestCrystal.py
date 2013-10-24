'''
#IMPORT LIBRARIES AND SET UP PATHS
'''
import wx, sys, logging, wx.lib.dialogs, ssh, epics, ast, time, glob, re, os, math, requests, glob, getpass
from scipy import optimize
from numpy import mat
from os.path import isfile as isfile
from os.path import isdir as isdir
#from subprocess import call, Popen, PIPE, STDOUT, check_output
from SetUp import SetUp as SetUp
from redisobj import RedisHashMap

#try: 
#    sys.path.index('/xray/progs/mxpylib')
#except (ValueError, TypeError):
#    sys.path.insert(0,'/xray/progs/mxpylib')

try: 
    sys.path.index('/xray/progs/Python/libraries/')
except (ValueError, TypeError):
    sys.path.insert(0,'/xray/progs/Python/libraries/')

from beamline import variables as blconfig
import beamline
import dcss

class TestCrystal():
    """Sets up for collecting a test crystal
    
    The TestCrystal script prompts a staff member to mount a protein crystal
    and populates the BluIce tab0 fields appropriately.
    
    """
    
    '''
    Constructor
    '''
    def __init__(self,param_dict):
        self.user = getpass.getuser()
        self.delete_list = []
        self.param_dict = param_dict
        self.skip = 'No'
        ###start a log file
        self.logger = logging.getLogger('beamline_setup')
        self.logger.info('Running TestCrystal script')

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

    def SetupSnapshots(self):
        if self.skip == 'Yes':
            return
        ###Work out the next index number for tab0 tescrystal images in cal dir
        try:
            os.chdir(self.param_dict['calibrationDir']+'test_crystal')
            filelist=glob.glob('testcrystal_0*'+'.img')
            if len(filelist) < 1:
                self.index = 1
            else:
                self.index = int(re.split(r'[_.]', filelist[-1])[-2])
        except:
            self.logger.error('the test_crystal dir did not exist')
            self.index = 1

        ###Get the position of the last crystal mounted
        if 'LastCrystal' in self.param_dict.keys():
            self.lastcrystal = str(self.param_dict['LastCrystal'])
        else:
            try:
                self.lastcrystal = file('/data/home/calibration/lastcrystal.txt', "r").readlines()[-1].rstrip()
            except:
                self.lastcrystal = 'unknown'

            
        ###Use bluice DCSS access to populate tab0 for test images
        #app = wx.PySimpleApp()
        response = wx.lib.dialogs.messageDialog(title='TestCrystal', message='Do you want to populate tab0 fields for collecting snapshots from a test crystal?\nThe last crystal to be collected by staff was: '+self.lastcrystal+'.\nCancel skips this step\nOk will populate tab0 fields with the correct settings but will not automatically start collection.')
        #app.Yield()
        #del app

        if response.returnedString == "Cancel":
            self.logger.info('Will not change tab0 fields.')
            self.skip = "Yes"
        else:
            self.logger.info('Populating tab0 with test crystal settings')
            self.skip = "No"

        if blconfig.ID == "MX1":
            self.distance=171
        else:
            self.distance=264

        self.dcssArgs = {'status': None,
        'exposure_time': 1,
        'attenuation': 95,
        'run': 0,
        'start_frame': self.index,
        'start_angle': None,
        'debug': False,
        'end_angle': None,
        'collect': False,
        'energy1': beamline.energy.eV,
        'next_frame': 0,
        'delta': 1,
        'directory': self.param_dict['calibrationDir']+'test_crystal',
        'file_root': 'testcrystal',
        'beam_stop': None,
        'distance': self.distance}


        if self.skip == "No":
            runs = dcss.runs.Runs()
            runs.set_run('run%s' % self.dcssArgs['run'], **self.dcssArgs)
            #runs.start_run(self.dcssArgs['run'])

        ###Use bluice DCSS access to populate tab0 for test images
        #app = wx.PySimpleApp()
        response = wx.lib.dialogs.messageDialog(title='TestCrystal', message='Please take snapshots and optimise settings. Click OK when you are ready to collect a dataset. Cancel will skip this.')
        #app.Yield()
        #del app

        if response.returnedString == "Cancel":
            self.logger.info('Will not collect a dataset')
            self.skip = "Yes"
        else:
            self.logger.info('Collecting a test crystal dataset')
            self.skip = "No"


    def CollectDataset(self):
        if self.skip == "Yes":
            return

        ###Work out the next index number for tab1 tescrystal images in cal dir
        try:
            os.chdir(self.param_dict['calibrationDir']+'test_crystal')
            filelist=glob.glob('testcrystal_1*'+'.img')
            if len(filelist) < 1:
                self.index = 1
            else:
                self.index = int(re.split(r'[_.]', filelist[-1])[-2])
        except:
            self.index = 1
        runs = dcss.runs.Runs()
        tabzero_dict = runs.return_runs()['run0']

        self.dcssArgs = {'status': None,
        'exposure_time': tabzero_dict['exposure_time'],
        'attenuation': tabzero_dict['attenuation'],
        'run': 1,
        'start_frame': self.index,
        'start_angle': 0,
        'debug': False,
        'end_angle': 180,
        'collect': False,
        'energy1': beamline.energy.eV,
        'next_frame': 0,
        'delta': tabzero_dict['delta'],
        'directory': self.param_dict['calibrationDir']+'test_crystal',
        'file_root': 'testcrystal',
        'beam_stop': tabzero_dict['beam_stop'],
        'distance': tabzero_dict['distance']}

        if self.skip == "No":
            runs = dcss.runs.Runs()
            runs.set_run('run%s' % self.dcssArgs['run'], **self.dcssArgs)
            runs.start_run(self.dcssArgs['run'])
            self.logger.info('Testcrystal dataset is finished')
            time.sleep(5) #give a delay between dataset finishing and checking processing

            
    def WaitForProcessing(self):
        if self.skip == "Yes":
            return

        def results():
            headers = {'accept': 'application/json'}
            return requests.get('http://processing/processing?limit=1&type=dataset', headers=headers)

        ###wait for processing to start
        self.logger.info('waiting for processing to start')
        test = True
        counter = 0
        while test:
            try:
                self.skip = "No"
                r = results()
                dataset_name = r.json['results'][0]['sample']['name']
                test = False
            except:
                self.skip = "Yes"
                counter += 1
                time.sleep(5)
                if counter > 20:
                    test = False

            if self.skip == "Yes":
                self.logger.error('timeout while waiting for processing to start')
                return

        ###check that its the right dataset
        if r.json['results'][0]['sample']['name'] == 'testcrystal_1':
            self.logger.info('autoprocessing started')

            ###A Progress Dialog!
            max = 48 #3-3.5 mins for a dataset, set max at 4 mins
            #app = wx.PySimpleApp()
            dlg = wx.ProgressDialog(title='TestCrystal',message='Waiting for autoprocessing...', maximum=max, style = wx.PD_APP_MODAL | wx.PD_CAN_ABORT)
            count = 0

            ###wait for autoprocessing to complete 
            self.completed = False
            while not self.completed and dlg.Update(count):#while completed = False and no cancel
                time.sleep(5)
                count += 1
                r = results()
                self.completed = r.json['results'][0]['completed']

            dlg.Destroy()
            #app.Yield()
            #del app

            if r.json['results'][0]['completed'] and r.json['results'][0]['success']:
                self.spacegroup = r.json['results'][0]['space_group']
                self.processing_dir = r.json['results'][0]['processing_dir'].rstrip()+'/'
                self.logger.info('Processing complete and successful')
                self.skip = 'No'
            else:
                self.logger.info('Cannot resolve processing results')
                self.skip = 'Yes'
                
    def HarvestResults(self):
        if self.skip == "Yes":
            #app = wx.PySimpleApp()
            response = wx.lib.dialogs.dirDialog(message='Choose a processing folder associated with testcrystal processing', path=blconfig.AUTO_DIR+'/dataset',style=wx.OPEN | wx.CHANGE_DIR)
            #app.Yield()
            #del app

            if response.returnedString == "Cancel":
                self.logger.info('No testcrystal data, skipping step')
                self.skip = "Yes"
                return
            else:
                self.skip = "No"
                
                self.processing_dir = response.path+'/'
                self.spacegroup = "HSYMM"
                self.logger.info('Harvesting stats from '+self.processing_dir)

        html_output=[]


        ###FOR P1
        file='CORRECT.LP_p1'
        correctfile=open(self.processing_dir+file)
        correcttext = correctfile.readlines()
        #HTML HEADER
        html_output.append('<PRE><span style="font-size:9px;"><span style="font-family:courier new,courier,monospace;">\n')
        #TITLE
        html_output.append('P1\n')
        #GET UNIT CELL
        index = [i for i, item in enumerate(correcttext) if re.search('.*UNIT_CELL_CONSTANTS=.*', item)][-1]
        line=correcttext[index]
        html_output.append(line)
        html_output.append('')
        #GET STATS TABLE
        index = [i for i, item in enumerate(correcttext) if re.search('.*SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION.*', item)][-1]
        index2 = [i for i, item in enumerate(correcttext[index:]) if re.search(' *total.*', item)][0] + index + 1
        tablelist=correcttext[index:index2]
        for line in tablelist:
            html_output.append(line)
        #FOOTER
        html_output.append('</span> </span></PRE>\n')
        
        ###FOR HSYMM
        file='CORRECT.LP_hsymm'
        correctfile=open(self.processing_dir+file)
        correcttext = correctfile.readlines()
        #HTML HEADER
        html_output.append('<PRE><span style="font-size:9px;"><span style="font-family:courier new,courier,monospace;">\n')
        #TITLE
        html_output.append(self.spacegroup+'\n')
        #GET UNIT CELL
        index = [i for i, item in enumerate(correcttext) if re.search('.*UNIT_CELL_CONSTANTS=.*', item)][-1]
        line=correcttext[index]
        html_output.append(line)
        #GET ISA
        index = [i for i, item in enumerate(correcttext) if re.search('.*a        b          ISa.*', item)][-1] + 1
        line=correcttext[index]
        isa = line.split()[-1]
        html_output.append('ISa: '+str(isa)+'\n')
        html_output.append('FRIEDEL=FALSE\n')
        html_output.append('\n')
        #GET STATS TABLE
        index = [i for i, item in enumerate(correcttext) if re.search('.*SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION.*', item)][-1]
        index2 = [i for i, item in enumerate(correcttext[index:]) if re.search(' *total.*', item)][0] + index + 1
        tablelist=correcttext[index:index2]
        for line in tablelist:
            html_output.append(line)
        #FOOTER
        html_output.append('\n')
        
        ###FOR ANOM
        file='CORRECT.LP_hsymm_NOANOM'
        correctfile=open(self.processing_dir+file)
        correcttext = correctfile.readlines()
        #TITLE
        html_output.append('FRIEDEL=TRUE\n')
        html_output.append('\n')
        #GET STATS TABLE
        index = [i for i, item in enumerate(correcttext) if re.search('.*SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION.*', item)][-1]
        index2 = [i for i, item in enumerate(correcttext[index:]) if re.search(' *total.*', item)][0] + index + 1
        tablelist=correcttext[index:index2]
        for line in tablelist:
            html_output.append(line)
        #FOOTER
        html_output.append('</span> </span></PRE>\n')

        self.html_output = ''.join(html_output)

        tempfilename='/var/tmp/'+str(self.user)+'_testcrystal_stats.txt'
        self.delete_list.append(tempfilename)
        with open(tempfilename, 'w') as outputfile:
            outputfile.write(self.html_output)
        outputfile.closed

        response = wx.lib.dialogs.ScrolledMessageDialog(None, self.html_output, "TEST CRYSTAL", size=(1000,400))
        children = response.GetChildren()
        textCtrl = children[0]
        textCtrl.SetFont(wx.Font(9,wx.FONTFAMILY_TELETYPE,wx.NORMAL,wx.BOLD, False))
        response.ShowModal()
        response.Destroy()
        
        #app.Yield()
        #del app
        response = wx.lib.dialogs.messageDialog(title='CHECK STATS AND HIT OK TO DISMISS WINDOW', message='Do you want to write these stats to the calibration directory?', aStyle=wx.YES_NO)
        
        if response.returnedString == "No":
            self.logger.info('Will not write stats.')
        else:
            self.logger.info('Writing stats to /data/home/calibration/testcrystal_stats,txt')


            ###transfer output image to /data/home/calibration dir
            timestamp = time.strftime("%d-%m-%Y %H:%M:%S")
            local_file = tempfilename
            remote_file2 = '/data/home/calibration/testcrystal_stats.txt'
            remote_file3 = '/data/home/calibration/test_crystal/'+str(timestamp)+'testcrystal_stats.txt'
            sshc = ssh.SSHClient()
            sshc.set_missing_host_key_policy(ssh.AutoAddPolicy())
            sshc.connect('localhost', username='blctl', password=str(self.param_dict['password']))
            stdin, stdout, stderr = sshc.exec_command('cp '+local_file+' '+remote_file2)
            stdin, stdout, stderr = sshc.exec_command('cp '+local_file+' '+remote_file3)
            sshc.close()


            #define right hashmap for right beamline
            if blconfig.ID == "MX1":
                self.mymap = RedisHashMap('mx1_beamline_setup')            
            else:
                self.mymap = RedisHashMap('mx2_beamline_setup')

            self.mymap['TestCrystalDate'] = time.time()
            self.mymap['TestCrystalStats'] = self.html_output

            ###Get position of testcrystal if crystal has changed
            
            response = wx.lib.dialogs.messageDialog(title='TestCrystal', message='Did you end up using a different crystal than the one the last staff member recorded?', aStyle=wx.YES_NO)

            if response.returnedString == "No":
                self.logger.info('Will not change the test crystal info.')
            else:
                response = wx.lib.dialogs.textEntryDialog(title='NEW TESTCRYSTAL', message="Please enter where the new test crystal is in the format 'rC4'", style=wx.OK)
                if response.accepted:
                    self.new_crystal_posn = response.text
                    self.logger.info('Recording new crystal posn as '+self.new_crystal_posn)
                else:
                    self.new_crystal_posn = 'unknown'
                    self.logger.info('Recording new crystal posn as unknown')
                    
                try:
                    lastcrystal_file = open('/data/home/calibration/lastcrystal.txt', "a")
                    lastcrystal_file.write(self.new_crystal_posn+'\n')
                    lastcrystal_file.close
                except:
                    self.logger.error('was not able to record the position of the test crystal')
                        








    def CleanTempFiles(self):
        time.sleep(2)#it was deleting the temp files before they'd been copied to /data/home/calibration!
        no_duplicates = list(set(self.delete_list))
        for file in no_duplicates:
            try:
                os.remove(file)
            except:
                self.logger.info('Could not delete '+file)          


if __name__ == '__main__':
    app = wx.PySimpleApp()
    testcrystal = TestCrystal('NotDefined')
    testcrystal.SetupSnapshots()
    testcrystal.CollectDataset()
    testcrystal.WaitForProcessing()
    testcrystal.HarvestResults()
    del app
