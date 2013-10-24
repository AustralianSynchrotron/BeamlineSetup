#!/usr/bin/env python2.7
'''
This set up section defines the various parameters needed by the script
'''
import wx, sys, logging, wx.lib.dialogs, ssh, subprocess           
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

class SetUp():
    def DefineParameters(self):
        args = ['notify-send', '--urgency=normal', '-i', '/xray/progs/Python/applications/beamline_setup/icon.png', 'Welcome to Beamline SetUp!\nPlease define some variables']
        subprocess.Popen(args)

        ###START A LOG FILE
        self.logger = logging.getLogger('beamline_setup')
        self.logger.setLevel(logging.DEBUG)
        filehandler = logging.FileHandler('/data/home/calibration/beamline_setup.log')
        streamhandler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s: %(levelname)s: %(module)s: %(message)s',"[%Y-%m-%d %H:%M:%S]")
        streamhandler.setFormatter(formatter)
        filehandler.setFormatter(formatter)
        self.logger.addHandler(filehandler)
        self.logger.addHandler(streamhandler)
        self.logger.info('Setup a new log file')

        self.param_dict = {}
        self.param_dict['EPN'] = blconfig.EPN
        self.param_dict['calibrationDir'] = '/data/frames/'+str(blconfig.EPN)+'/calibration/'
        self.param_dict['fileserverIP'] = '10.'+str(blconfig.beamlineN)+'.24.10'
        self.param_dict['username'] = str(blconfig.owner)
        self.param_dict['TestVariable'] = 'PASS'

        ###Reset staff comment in redis if new EPN otherwise propegate
        if blconfig.ID == "MX1":
            self.mymap = RedisHashMap('mx1_beamline_setup')            
        else:
            self.mymap = RedisHashMap('mx2_beamline_setup')

        try:
            if self.mymap['elog_comment_EPN'] == str(blconfig.EPN):
                self.logger.info('there is already an elog comment for this EPN, will propegate this')
            else:
                self.logger.info('the current elog comment is for a different EPN, will start a new one')
                self.mymap['elog_comment'] = ""
                self.mymap['elog_comment_EPN'] = str(blconfig.EPN)

        except:
                self.logger.info('the fields elog_comment and elog_comment_EPN did not exist in redis, will create them')
                self.mymap['elog_comment'] = ""
                self.mymap['elog_comment_EPN'] = str(blconfig.EPN)



    def PromptUserchange(self):

        '''
        #RUN THE USER CHANGER
        '''
        #app = wx.PySimpleApp()
        response = wx.lib.dialogs.messageDialog(title='User Changer', message='Has the user changer run?\n (No will cause setup script to abort.)', aStyle=wx.YES_NO)
        #app.Yield()
        #del app

        if response.returnedString == "No":
            self.logger.info('Aborting beamline setup due to user input')
            sys.exit()

    def SmallMolecule(self):

        '''
        #ARE THEY SMALL MOLECULE
        '''
        #app = wx.PySimpleApp()
        response = wx.lib.dialogs.messageDialog(title='SMX', message='Are the users small molecule? If so you may want to change energy to 17440 KeV.',aStyle=wx.YES_NO)
        #app.Yield()
        #del app

        if response.returnedString == "Yes":
            self.logger.info('Writing .SMX file to users homespace')
            command='touch /data/home/'+str(blconfig.EPN)+'/.SMX'
            p = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        else:
            self.logger.info('Users are not SMX')

    def GetPassword(self):

        '''
        #GET THE BEAMLINE PASSWORD
        '''
        attempts=0
        success=0
        while attempts < 3 and success == 0:
            #app = wx.PySimpleApp()
            response = wx.lib.dialogs.textEntryDialog(title='ENTER PASSWORD', message='Please enter the beamline password for '+str(blconfig.ID), style=wx.TE_PASSWORD | wx.OK)
            #app.Yield()
            #del app
            if response.accepted:

                try:
                    sshc = ssh.SSHClient()
                    sshc.set_missing_host_key_policy(ssh.AutoAddPolicy())
                    sshc.connect(self.param_dict['fileserverIP'], username=str(blconfig.owner), password=response.text)
                    stdin, stdout, stderr = sshc.exec_command("hostname")
                    self.logger.info('Successfully logged into the file server')
                    self.param_dict['password'] = response.text
                    success=1
                except:
                    attempts = attempts + 1
                    self.logger.error('Wrong password, try again')
            else:
                self.logger.error('Cannot proceed without a password, try again')

        if success == 0:
            #app = wx.PySimpleApp()
            wx.lib.dialogs.messageDialog(title='BEAMLINE SETUP ERROR', message='The password is wrong or the fileserver is down. Cannot continue with setup.')
            #app.Yield()
            #del app
            self.logger.error('Cannot log into the file server')
            sys.exit()

    def GetLastCrystal(self):
            '''
            #Get position of the last crystal mounted
            '''
            try:
                last_line = file('/data/home/calibration/lastcrystal.txt', "r").readlines()[-1].rstrip()
                self.param_dict['LastCrystal'] = last_line
            except:
                self.param_dict['LastCrystal'] = "unknown"
                self.logger.error('cannot read lastcrystal.txt file, you may be running as wrong user')

    def GetStaffMember(self):    
        '''
        #Get the staff member
        '''
        #app = wx.PySimpleApp()
        response = wx.lib.dialogs.multipleChoiceDialog(None, title='WHO ARE YOU?', message='Please select your name from the list.', lst=['Tom Caradoc-Davies', 'David Aragao', 'Santosh Panjikar', 'Jason Price', 'Rachel Williamson', 'Alan Riboldi-Tunnicliffe', 'Nathan Cowieson', 'Christine Gee'])
        #app.Yield()
        if response.accepted:
            staff_name = response.selection[0]
        else:
            staff_name = 'MX staff'
        self.param_dict['staffName'] = staff_name
        #del app

    def InductionForms(self):    
        '''
        #Get the number of induction forms to print
        '''
        #app = wx.PySimpleApp()
        response = wx.lib.dialogs.multipleChoiceDialog(None, title='Induction forms', message='How many induction forms would you like to print?', lst=['0','1','2','3','4','5'])
        #app.Yield()
        if response.accepted:
            number_forms = response.selection[0]
        else:
            number_forms = 0
        #del app
        print_command = '/xray/progs/bin/print_induction.sh '+str(number_forms)
        p = subprocess.Popen(print_command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        self.logger.info('printing '+number_forms+' inductions forms')

    def ChooseModules(self):
        '''
        #Allow user to choose which modules to run.
        '''
        #app = wx.PySimpleApp()
        lst = ["Create directories", "Rotation axis", "Align beam", "Snapshot", "Cryojet", "Beam centre", "Test crystal", "Probe cassette", "EA and inductions", "Format report"]
        dlg = wx.MultiChoiceDialog( None, "Select modules to run:", "Beamline Setup", lst)

        dlg.SetSelections(range(0,len(lst)))#Set all modules to run by default
 
        if (dlg.ShowModal() == wx.ID_OK):
            selections = dlg.GetSelections()
            strings = [lst[x] for x in selections]
        else:
            self.logger.info('Aborting beamline setup due to user input')
            sys.exit()
        

        dlg.Destroy()
        #del app

        self.param_dict['moduleSelection'] = strings


    def RunModules(self):
        '''
        #Run the modules listed in self.param_dict['moduleSelection']
        #"Create directories", "Rotation axis", "Align beam", "Snapshot", "Cryojet", "Beam centre", "Test crystal", "Probe cassette", "EA and inductions", "Format report"
        '''
        ###RUN CREATE DIRS MODULE
        module = "Create directories"
        if module in self.param_dict['moduleSelection']:
            step = self.param_dict['moduleSelection'].index(module) + 1
            total = len(self.param_dict['moduleSelection'])
            args = ['notify-send', '--urgency=normal', '-i', '/xray/progs/Python/applications/beamline_setup/icon.png', 'Step '+str(step)+' of '+str(total)+'.\n'+str(module)]
            subprocess.Popen(args)
            from CreateDirs import createDirs
            m = createDirs(self.param_dict)
            m.CreateDirs()


        ###RUN ROTATION AXIS MODULE
        module = "Rotation axis"
        if module in self.param_dict['moduleSelection']:
            step = self.param_dict['moduleSelection'].index(module) + 1
            total = len(self.param_dict['moduleSelection'])
            args = ['notify-send', '--urgency=normal', '-i', '/xray/progs/Python/applications/beamline_setup/icon.png', 'Step '+str(step)+' of '+str(total)+'.\n'+str(module)]
            subprocess.Popen(args)
            from RotationAxis import Align
            m = Align(self.param_dict)
            m.Take_Images()
            m.Prepare_Search_Images()
            m.Correct_Axis()
            m.Save_Results()

        ###RUN BEAM ALIGNMENT MODULE
        module = "Align beam"
        if module in self.param_dict['moduleSelection']:
            step = self.param_dict['moduleSelection'].index(module) + 1
            total = len(self.param_dict['moduleSelection'])
            args = ['notify-send', '--urgency=normal', '-i', '/xray/progs/Python/applications/beamline_setup/icon.png', 'Step '+str(step)+' of '+str(total)+'.\n'+str(module)]
            subprocess.Popen(args)
            from AlignBeam import Align
            m = Align(self.param_dict)
            m.TakeImages()
            m.SaveResults()

        ###RUN SNAPSHOT MODULE
        module = "Snapshot"
        if module in self.param_dict['moduleSelection']:
            step = self.param_dict['moduleSelection'].index(module) + 1
            total = len(self.param_dict['moduleSelection'])
            args = ['notify-send', '--urgency=normal', '-i', '/xray/progs/Python/applications/beamline_setup/icon.png', 'Step '+str(step)+' of '+str(total)+'.\n'+str(module)]
            subprocess.Popen(args)
            from SnapShot import Snapshot
            m = Snapshot(self.param_dict)
            m.RunSnapshot()

        ###RUN CRYOJET MODULE
        module = "Cryojet"
        if module in self.param_dict['moduleSelection']:
            step = self.param_dict['moduleSelection'].index(module) + 1
            total = len(self.param_dict['moduleSelection'])
            args = ['notify-send', '--urgency=normal', '-i', '/xray/progs/Python/applications/beamline_setup/icon.png', 'Step '+str(step)+' of '+str(total)+'.\n'+str(module)]
            subprocess.Popen(args)
            from CryoJet import CryoJet
            m = CryoJet(self.param_dict)
            m.AlignCryojet()
            m.ArchiveResults()

    def CurrentMessages(self):
        try:
            messagesfile=open('/data/home/calibration/beamline_messages.txt')
            messages=messagesfile.readlines()
        except:
            self.logger.error('Could not open /data/home/calibration/beamline_messages.txt')
            messages = []

        for message in messages:
            if message.rstrip() != '':
                response = wx.lib.dialogs.messageDialog(title='Messages', message=str(message.rstrip()), aStyle=wx.OK|wx.ICON_EXCLAMATION)

    def ReturnDictionary(self):
        return self.param_dict

if __name__ == '__main__':
    app = wx.PySimpleApp()
    m = SetUp()
    m.DefineParameters()
    m.PromptUserchange()
    m.GetPassword()
    m.GetLastCrystal()
    m.GetStaffMember()
    m.ChooseModules()
    m.RunModules()
    m.ReturnDictionary()
    del app



