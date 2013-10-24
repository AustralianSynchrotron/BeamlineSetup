'''
#IMPORT LIBRARIES AND SET UP PATHS
'''

import wx, sys, logging, wx.lib.dialogs, ssh, os
from SetUp import SetUp as SetUp
from redisobj import RedisHashMap


try: 
    sys.path.index('/xray/progs/mxpylib')
except (ValueError, TypeError):
    sys.path.insert(0,'/xray/progs/mxpylib')

try: 
    sys.path.index('/xray/progs/Python/libraries/')
except (ValueError, TypeError):
    sys.path.insert(0,'/xray/progs/Python/libraries/')
from beamline import variables as blconfig

class createDirs():

    def __init__(self,param_dict):
        self.param_dict = param_dict
        self.logger = logging.getLogger('beamline_setup')
        self.logger.info('Running step to create calibration directories')

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

    def CreateDirs(self):
        ###Set up SSH connection to file server
        sshc = ssh.SSHClient()
        sshc.set_missing_host_key_policy(ssh.AutoAddPolicy())
        sshc.connect(str(self.param_dict['fileserverIP']), username=str(self.param_dict['username']), password=str(self.param_dict['password']))

        #PROMPT USER INPUT, DO YOU WANT TO CREATE CALIBRATION DIRS

        if os.path.isdir(self.param_dict['calibrationDir']):
            self.logger.info(str(self.param_dict['calibrationDir'])+' already exists')
            #app = wx.PySimpleApp()
            response = wx.lib.dialogs.messageDialog(title='Calibration Directories', message='A calibration dir already exists in '+str(self.param_dict['calibrationDir'])+', do you want to overwrite?', aStyle=wx.YES_NO)
            #app.Yield()
            #del app
            
            if response.returnedString == 'Yes':
                self.param_dict['createDirs'] = 'Yes'
                epoc = str(int(os.stat(str(self.param_dict['calibrationDir'])).st_ctime))
                dir_archive = '/data/frames/'+str(self.param_dict['EPN'])+'/calibration_'+epoc
                command = 'mv '+str(self.param_dict['calibrationDir'])+' '+dir_archive
                stdin, stdout, stderr = sshc.exec_command(command)
                self.logger.info('moved the old calibration dir to '+dir_archive)
            else:
                self.param_dict['createDirs'] = 'Yes'
        else:
            #app = wx.PySimpleApp()
            response = wx.lib.dialogs.messageDialog(title='Calibration Directories', message='Do you want to create a new calibration directory in '+str(self.param_dict['calibrationDir'])+'?', aStyle=wx.YES_NO)
            #app.Yield()
            #del app
            if response.returnedString == 'Yes':
                self.param_dict['createDirs'] = 'Yes'
            else:
                self.param_dict['createDirs'] = 'No'

        #CREATE THE DIRECTORIES

        if self.param_dict['createDirs'] == 'Yes':
            calibration_dirs = ['', 'beam_centre', 'beam_image', 'cryo_alignment', 'rotation_axis', 'test_crystal']
            

            try:
                for dir in calibration_dirs:
                    command = 'mkdir '+str(self.param_dict['calibrationDir'])+dir
                    stdin, stdout, stderr = sshc.exec_command(command)
                    channel = stdout.channel
                    status = channel.recv_exit_status()
                    if status == 0:
                        self.logger.info('made dir '+str(self.param_dict['calibrationDir'])+dir)
                    else:
                        self.logger.error('make dir '+str(self.param_dict['calibrationDir'])+dir+' failed with exit code '+str(status))

                #define right hashmap for right beamline
                if blconfig.ID == "MX1":
                    self.mymap = RedisHashMap('mx1_beamline_setup')            
                else:
                    self.mymap = RedisHashMap('mx2_beamline_setup')

                self.mymap['CreateDirs_EPN'] = str(blconfig.EPN)

            except:
                self.logger.error('Could not make the calibration directories')
            
        else:
            self.logger.error('Did not make the calibration directories')

if __name__ == '__main__':
    app = wx.PySimpleApp()
    m = createDirs('NotDefined')
    m.CreateDirs()
    del app
