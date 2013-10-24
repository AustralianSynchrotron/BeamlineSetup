'''
#IMPORT LIBRARIES AND SET UP PATHS
'''

import wx, sys, logging, wx.lib.dialogs, ssh, epics, urllib, ast, datetime, getpass
from time import strftime
from os.path import isfile as isfile
from os.path import isdir as isdir
from subprocess import call, Popen, PIPE, STDOUT, check_output
from SetUp import SetUp as SetUp
import time
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


class CryoJet():
    """Sets up for a new CryoJet alignment job
    
    This class is for aligning the Cryojets

    """
    
    '''
    Constructor
    '''
    def __init__(self,param_dict):
        self.user = getpass.getuser()

        self.param_dict = param_dict
        self.logger = logging.getLogger('beamline_setup')
        self.logger.info('Running step to align cryojet')

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

    def AlignCryojet(self):
        self.logger.info('Prompting for cryojet variables')
        ###define cryo related variables for both beamlines
        if blconfig.ID == "MX1":
            self.cryo_inout_pv = "SR03BM01DIO01:CRYOJET1_INOUT_CMD"
            self.shield_flow = 5.7
            self.sample_flow = 6.3
            self.target_temp = 100
            self.target_distance = 26
            self.camera_url = "http://10.109.2.132:8080/IMAGE.JPG"
        
        else:
            self.cryo_inout_pv = "SR03ID01DIO01:CRYOJET1_INOUT_CMD"
            self.shield_flow = 4.7
            self.sample_flow = 6.3
            self.target_temp = 100
            self.target_distance = 26
            self.camera_url = "http://10.108.2.132/IMAGE.JPG"


        class TextEntryDialog(wx.Dialog):
            def __init__(self, parent, title, caption):
                style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
                super(TextEntryDialog, self).__init__(parent, -1, title, style=style)
                sampletext = wx.StaticText(self, -1, 'Sample flow:')
                sampleflow = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE)
                sampleflow.SetInitialSize((200, 30))

                shieldtext = wx.StaticText(self, -1, 'Shield flow:')
                shieldflow = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE)
                shieldflow.SetInitialSize((200, 30))

                cryotemptext = wx.StaticText(self, -1, 'Temperature:')
                cryotemp = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE)
                cryotemp.SetInitialSize((200, 30))

                cryodisttext = wx.StaticText(self, -1, "Cryojet has been aligned to sample by eye:")
                choicelist=["Yes","No"]
                cryodist = wx.ComboBox(self, -1, value=choicelist[0], pos=wx.Point(10, 30),size=wx.Size(200, 30), choices=choicelist)
                #cryodist = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE)
                #cryodist.SetInitialSize((200, 30))

                buttons = self.CreateButtonSizer(wx.OK|wx.CANCEL)
                sizer = wx.BoxSizer(wx.VERTICAL)
                sizer.Add(sampletext, 0, wx.ALL, 5)
                sizer.Add(sampleflow, 1, wx.EXPAND|wx.ALL, 5)
                sizer.Add(shieldtext, 0, wx.ALL, 5)
                sizer.Add(shieldflow, 1, wx.EXPAND|wx.ALL, 5)
                sizer.Add(cryotemptext, 0, wx.ALL, 5)
                sizer.Add(cryotemp, 1, wx.EXPAND|wx.ALL, 5)
                sizer.Add(cryodisttext, 0, wx.ALL, 5)
                sizer.Add(cryodist, 1, wx.EXPAND|wx.ALL, 5)


                sizer.Add(buttons, 0, wx.EXPAND|wx.ALL, 5)
                self.SetSizerAndFit(sizer)
                self.sampleflow = sampleflow
                self.shieldflow = shieldflow
                self.cryotemp = cryotemp
                self.cryodist = cryodist

            def SetSampleFlow(self, value):
                self.sampleflow.SetValue(value)
            def GetSampleFlow(self):
                return self.sampleflow.GetValue()
            def SetShieldFlow(self, value):
                self.shieldflow.SetValue(value)
            def GetShieldFlow(self):
                return self.shieldflow.GetValue()
            def SetCryoTemp(self, value):
                self.cryotemp.SetValue(value)
            def GetCryoTemp(self):
                return self.cryotemp.GetValue()
            def SetCryoDist(self, value):
                self.cryodist.SetValue(value)
            def GetCryoDist(self):
                return self.cryodist.GetValue()


        #app = wx.PySimpleApp()
        dialog = TextEntryDialog(None, 'Check Cryojet', 'Check that the CryoJet is functioning normally')
        dialog.Center()
        dialog.SetSampleFlow(str(self.sample_flow))
        dialog.SetShieldFlow(str(self.shield_flow))
        dialog.SetCryoTemp(str(self.target_temp))
        if dialog.ShowModal() == wx.ID_OK:
            self.cryodist = dialog.GetCryoDist()
            self.cryotemp = dialog.GetCryoTemp()
            self.sampleflow = dialog.GetSampleFlow()
            self.shieldflow = dialog.GetShieldFlow()
        dialog.Destroy()
        #del app

    def ArchiveResults(self):
        self.logger.info('Archiving the input CryoJet parameters')
        timestamp = strftime("%y-%m-%d-%H-%M")

        if blconfig.ID == "MX1":
            self.mymap = RedisHashMap('mx1_beamline_setup')            
        else:
            self.mymap = RedisHashMap('mx2_beamline_setup')

        self.mymap['CryojetDate'] = time.time()
        self.mymap['CryojetDist'] = self.cryodist.rstrip()
        self.mymap['CryojetTemp'] = self.cryotemp.rstrip()
        self.mymap['CryojetSampleFlow'] = self.sampleflow.rstrip()
        self.mymap['CryojetShieldFlow'] = self.shieldflow.rstrip()

    def Take_Images(self):

        #set cryojet in posn
        #turn down sample light
        #set mark posn depending on smx or mx
        imagename = '/var/tmp/'+str(self.user)+'_temp.jpg'
        imagefile = urllib.urlopen(self.camera_url)
        image = imagefile.read()
        outfile =open(imagename, 'w')
        outfile.write(image)
        outfile.close()
        im_command = 'convert -flip -crop 640x180+0+170 /var/tmp/'+str(self.user)+'_temp.jpg /var/tmp/'+str(self.user)+'_cryojet.jpg'
        call(im_command, shell=True)
        self.logger.info('written '+str(imagename))

if __name__ == '__main__':
    app = wx.PySimpleApp()
    m = CryoJet('NotDefined')
    m.AlignCryojet()
    m.ArchiveResults()
    del app


