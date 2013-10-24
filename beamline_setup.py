#!/usr/bin/env python2.7



'''
version 0.1
by Nathan Cowieson 10/04/13
Set up parameters for the beamline setup and run
a small GUI to guide through the process.
'''
import wx, sys, logging, wx.lib.dialogs, ssh, subprocess, datetime, time
from wxPython.wx import *
from time import strftime
from redisobj import RedisHashMap
from SetUp import SetUp as SetUp
#sys.path.insert(0,'/xray/progs/mxpylib/beamline_setup')

#try:                                                   
#    sys.path.index('/xray/progs/mxpylib')              
#except (ValueError, TypeError):                        
#    sys.path.insert(0,'/xray/progs/mxpylib')           
                                                       
try:                                                   
    sys.path.index('/xray/progs/Python/libraries/')    
except (ValueError, TypeError):                        
    sys.path.insert(0,'/xray/progs/Python/libraries/') 

from beamline import variables as blconfig


class Window ( wxFrame ):

    def __init__ (self,dictionary):
        self.param_dict = dictionary
        self.logger = logging.getLogger('beamline_setup')
        self.logger.info('THE BEAMLINE_SETUP GUI WAS RUN by '+str(self.param_dict['staffName']))

        ###CHOOSE REDIS DICTIONARY###
        if blconfig.ID == "MX1":
            self.mymap = RedisHashMap('mx1_beamline_setup')            
        else:
            self.mymap = RedisHashMap('mx2_beamline_setup')
            
        wxFrame.__init__ ( self, None, -1, 'Beamline Setup', size=(300,730))

        self.red = (255,0,0)
        self.amber = (255,126,0)
        self.green = (0,155,0)

        # Create a panel

        self.panel = wxPanel ( self, wxID_ANY )
        self.panel.SetBackgroundColour('white')
        # Create a grid sizer

        self.vertical = wxGridSizer ( 2,2 )

        
        # Create an image and add to sizer
        self.imagepanel = wxPanel(self, wxID_ANY)
        self.bannerimage = wxStaticBitmap(self.imagepanel)
        self.bannerimage.SetBitmap(wxBitmap('/xray/progs/Python/applications/beamline_setup/banner.png'))
        self.imagepanel.SetBackgroundColour((0,0,0))

        # Add a space

        #self.vertical.Add ( ( 0, 0 ), 1 )
        #self.vertical.Add ( ( 0, 0 ), 1 )



        ### CREATE DIRS BUTTON AND CHECK BOX
        self.first = wxCheckBox ( self.panel, id=1, label="" )
        self.first.SetBackgroundColour((0,0,0))
        self.firstbtn = wxButton(self.panel, id=2, label='Create Dirs')
        self.first.Enable(False)

        #test if dirs have been created for this epn
        try:
            if str(blconfig.EPN) == self.mymap['CreateDirs_EPN']:
                self.first.SetValue ( True )
            else:
                self.first.SetValue ( False )
        except:
            self.first.SetValue ( False )

        self.vertical.Add ( self.firstbtn, 0, wxEXPAND, 5 )
        self.vertical.Add ( self.first, 0, wxALIGN_CENTER)
        self.vertical.Add ( ( 0, 0 ), 1 ) #space
        self.vertical.Add ( ( 0, 0 ), 1 ) #space

        self.Bind(EVT_BUTTON, self.OnFirst, id=2)#catch button press event








        ### ROTATION AXIS BUTTON AND CHECK BOX
        self.secondtxt_value = "unknown"
        self.secondtxt = wxStaticText(self.panel, label=self.secondtxt_value)
        self.secondtxt.SetForegroundColour(self.red)
        self.secondbtn = wxButton(self.panel, id=4, label='Rotation Axis')

        #get the last date rotation axis was run
        try:
            date = datetime.datetime.fromtimestamp(float(self.mymap['RotationAxisDate']))
            self.rotationaxisdate = date.strftime("%d/%m/%y")
            self.secondtxt.SetLabel(self.rotationaxisdate)
            
            delta = datetime.datetime.now() - date
            if delta.seconds > 86400: #3600 seconds in an hour, 86400 seconds in one day
                self.secondtxt.SetForegroundColour(self.red)
            else:
                self.secondtxt.SetForegroundColour(self.green)

        except:
            self.secondtxt.SetForegroundColour(self.red)

        self.vertical.Add ( self.secondbtn, 0, wxEXPAND, 5 )
        self.vertical.Add (self.secondtxt, 0, wxALIGN_CENTER)
        self.vertical.Add ( ( 0, 0 ), 1 ) #space
        self.vertical.Add ( ( 0, 0 ), 1 ) #space

        self.Bind(EVT_BUTTON, self.OnSecond, id=4) #catch button press event








        ### BEAM ALIGN BUTTON AND CHECK BOX
        self.thirdtxt_value = "unknown"
        self.thirdtxt = wxStaticText(self.panel, label=self.thirdtxt_value)
        self.thirdtxt.SetForegroundColour(self.red)
        self.thirdbtn = wxButton(self.panel, id=6, label='Align Beam')

        #get the last date beam was aligned
        try:
            date = datetime.datetime.fromtimestamp(float(self.mymap['AlignBeamDate']))
            self.alignbeamdate = date.strftime("%d/%m/%y")
            self.thirdtxt.SetLabel(self.alignbeamdate)

            delta = datetime.datetime.now() - date
            if delta.seconds > 86400: #3600 seconds in an hour, 86400 seconds in one day
                self.thirdtxt.SetForegroundColour(self.red)
            else:
                self.thirdtxt.SetForegroundColour(self.green)

        except:
            self.thirdtxt.SetForegroundColour(self.red)


        self.vertical.Add ( self.thirdbtn, 0, wxEXPAND )
        self.vertical.Add ( self.thirdtxt, 0, wxALIGN_CENTER )
        self.vertical.Add ( ( 0, 0 ), 1 ) #space
        self.vertical.Add ( ( 0, 0 ), 1 ) #space

        self.Bind(EVT_BUTTON, self.OnThird, id=6) #catch button press event








        ### SNAPSHOT BUTTON AND CHECK BOX
        self.fourth = wxCheckBox ( self.panel, id=1, label="" )
        self.fourth.SetBackgroundColour((0,0,0))
        self.fourthbtn = wxButton(self.panel, id=8, label='Snapshot')
        self.fourth.Enable(False)
        
        #test if snapshot has been run for this EPN
        try:
            if str(blconfig.EPN) == self.mymap['Snapshot_EPN']:
                self.fourth.SetValue ( True )
            else:
                self.fourth.SetValue ( False )
        except:
            self.fourth.SetValue ( False )

        self.vertical.Add ( self.fourthbtn, 0, wxEXPAND )
        self.vertical.Add ( self.fourth, 0, wxALIGN_CENTER )
        self.vertical.Add ( ( 0, 0 ), 1 ) #space
        self.vertical.Add ( ( 0, 0 ), 1 ) #space

        self.Bind(EVT_BUTTON, self.OnFourth, id=8) #catch button press event









        ### CHECK CRYOJET BUTTON AND CHECK BOX
        self.fifthtxt_value = "unknown"
        self.fifthtxt = wxStaticText(self.panel, label=self.fifthtxt_value)
        self.fifthtxt.SetForegroundColour(self.red)
        self.fifthbtn = wxButton(self.panel, id=10, label='Check Cryojet')

        #get the last date cryojet was checked
        try:
            date = datetime.datetime.fromtimestamp(float(self.mymap['CryojetDate']))
            self.checkcryodate = date.strftime("%d/%m/%y")
            self.fifthtxt.SetLabel(self.checkcryodate)

            delta = datetime.datetime.now() - date
            if delta.seconds > 86400: #3600 seconds in an hour, 86400 seconds in one day
                self.fifthtxt.SetForegroundColour(self.red)
            else:
                self.fifthtxt.SetForegroundColour(self.green)

        except:
            self.fifthtxt.SetForegroundColour(self.red)

      
        self.vertical.Add ( self.fifthbtn, 0, wxEXPAND )
        self.vertical.Add ( self.fifthtxt, 0, wxALIGN_CENTER )
        self.vertical.Add ( ( 0, 0 ), 1 ) #space
        self.vertical.Add ( ( 0, 0 ), 1 ) #space

        self.Bind(EVT_BUTTON, self.OnFifth, id=10) #catch button press event








        ### BEAMCENTRE BUTTON AND CHECK BOX
        self.sixthtxt_value = "unknown"
        self.sixthtxt = wxStaticText(self.panel, label=self.sixthtxt_value)
        self.sixthtxt.SetForegroundColour(self.red)
        self.sixthbtn = wxButton(self.panel, id=12, label='Run BeamCentre')

        #get the last beamcentre script was last run
        try:
            date = datetime.datetime.fromtimestamp(float(self.mymap['BeamcentreDate']))
            self.beamcentredate = date.strftime("%d/%m/%y")
            self.sixthtxt.SetLabel(self.beamcentredate)

            delta = datetime.datetime.now() - date
            if delta.seconds > 86400: #3600 seconds in an hour, 86400 seconds in one day
                self.sixthtxt.SetForegroundColour(self.red)
            else:
                self.sixthtxt.SetForegroundColour(self.green)

        except:
            self.sixthtxt.SetForegroundColour(self.red)

      
        self.vertical.Add ( self.sixthbtn, 0, wxEXPAND )
        self.vertical.Add ( self.sixthtxt, 0, wxALIGN_CENTER )
        self.vertical.Add ( ( 0, 0 ), 1 ) #space
        self.vertical.Add ( ( 0, 0 ), 1 ) #space

        self.Bind(EVT_BUTTON, self.OnSixth, id=12) #catch button press event








        ### TESTCRYSTAL BUTTON AND CHECK BOX
        self.seventhtxt_value = "unknown"
        self.seventhtxt = wxStaticText(self.panel, label=self.seventhtxt_value)
        self.seventhtxt.SetForegroundColour(self.red)
        self.seventhbtn = wxButton(self.panel, id=14, label='Run TestCrystal')

        #get the last test_crystal script was last run
        try:
            date = datetime.datetime.fromtimestamp(float(self.mymap['TestCrystalDate']))
            self.testcrystaldate = date.strftime("%d/%m/%y")
            self.seventhtxt.SetLabel(self.testcrystaldate)

            delta = datetime.datetime.now() - date
            if delta.seconds > 86400: #3600 seconds in an hour, 86400 seconds in one day
                self.seventhtxt.SetForegroundColour(self.red)
            else:
                self.seventhtxt.SetForegroundColour(self.green)

        except:
            self.seventhtxt.SetForegroundColour(self.red)

      
        self.vertical.Add ( self.seventhbtn, 0, wxEXPAND )
        self.vertical.Add ( self.seventhtxt, 0, wxALIGN_CENTER )
        self.vertical.Add ( ( 0, 0 ), 1 ) #space
        self.vertical.Add ( ( 0, 0 ), 1 ) #space

        self.Bind(EVT_BUTTON, self.OnSeventh, id=14) #catch button press event








        ### PROBE CASSETTE BUTTON AND CHECK BOX
        self.eighth = wxCheckBox ( self.panel, id=15 )
        self.eighth.SetBackgroundColour((0,0,0))        
        self.eighthbtn = wxButton(self.panel, id=16, label='Probe Samples')
        self.eighth.Enable(False)

        #test if cassette has been probed for this epn
        try:
            if str(blconfig.EPN) == self.mymap['ProbeCassette_EPN']:
                self.eighth.SetValue ( True )
            else:
                self.eighth.SetValue ( False )
        except:
            self.eighth.SetValue ( False )
      
        self.vertical.Add ( self.eighthbtn, 0, wxEXPAND )
        self.vertical.Add ( self.eighth, 0, wxALIGN_CENTER )
        self.vertical.Add ( ( 0, 0 ), 1 ) #space
        self.vertical.Add ( ( 0, 0 ), 1 ) #space

        self.Bind(EVT_BUTTON, self.OnEighth, id=16) #catch button press event









        ### EA AND INDUCTIONS BUTTON AND CHECK BOX
        self.nineth = wxCheckBox ( self.panel, id=17 )
        self.nineth.SetBackgroundColour((0,0,0))
        self.ninethbtn = wxButton(self.panel, id=18, label='EA/Inductions')
        self.nineth.Enable(False)

        #test if EAs have been prepared for this epn
        try:
            if str(blconfig.EPN) == self.mymap['PrepareEAs_EPN']:
                self.nineth.SetValue ( True )
            else:
                self.nineth.SetValue ( False )
        except:
            self.nineth.SetValue ( False )



        self.vertical.Add ( self.ninethbtn, 0, wxEXPAND )
        self.vertical.Add ( self.nineth, 0, wxALIGN_CENTER )
        self.vertical.Add ( ( 0, 0 ), 1 ) #space
        self.vertical.Add ( ( 0, 0 ), 1 ) #space

        self.Bind(EVT_BUTTON, self.OnNineth, id=18) #catch button press event






        ### FORMAT REPORT BUTTON AND CHECK BOX
        self.tenth = wxCheckBox ( self.panel, id=19 )
        self.tenth.SetBackgroundColour((0,0,0))        
        self.tenthbtn = wxButton(self.panel, id=20, label='Create Report')
        self.tenth.Enable(False)

        #test if dirs have been created for this epn
        try:
            if str(blconfig.EPN) == self.mymap['FormatReport_EPN']:
                self.tenth.SetValue ( True )
            else:
                self.tenth.SetValue ( False )
        except:
            self.tenth.SetValue ( False )
      
        self.vertical.Add ( self.tenthbtn, 0, wxEXPAND )
        self.vertical.Add ( self.tenth, 0, wxALIGN_CENTER )
        self.vertical.Add ( ( 0, 0 ), 1 ) #space
        self.vertical.Add ( ( 0, 0 ), 1 ) #space

        self.Bind(EVT_BUTTON, self.OnTenth, id=20) #catch button press event

        ### QUIT BUTTON
        self.quitbtn = wxButton(self.panel, id=22, label='Close')
        self.commentbtn = wxButton(self.panel, id=23, label='Comment')
        
        self.vertical.Add ( self.commentbtn, 0, wxALIGN_CENTER )
        self.vertical.Add ( self.quitbtn, 0, wxALIGN_CENTER )
        self.vertical.Add ( ( 0, 0 ), 1 ) #space
        self.vertical.Add ( ( 0, 0 ), 1 ) #space

        self.Bind(EVT_BUTTON, self.OnQuit, id=22) #catch button press event
        self.Bind(EVT_BUTTON, self.OnComment, id=23) #catch button press event

        # Center it with a horizontal sizer

        self.horizontal = wxBoxSizer ( wxVERTICAL )

        self.horizontal.Add ( ( 10, 0 ), 1 )
        self.horizontal.Add (self.imagepanel, 0, wxALL | wxEXPAND, 5)
        self.horizontal.Add ( ( 10, 0 ), 1 )
        self.horizontal.Add ( self.vertical, 0, wxALL | wxEXPAND, 5 )

        self.horizontal.Add ( ( 10, 0 ), 1 )

        # Add the sizer

        self.panel.SetSizerAndFit ( self.horizontal )

        self.Show ( True )

    # This method unchecks the other checkbox if it is checked
    def OnQuit (self, event ):
        print "User pressed 'Close', exitting application."
        self.Destroy()

    def OnComment (self, event ):
        from MakeComment import CommentBox as CommentBox
        dlg = CommentBox()
        
    def OnFirst ( self, event ): #CREATE DIRS
        from CreateDirs import createDirs as createDirs
        a = createDirs(self.param_dict)
        a.CreateDirs()
        self.first.SetValue(True)

    def OnSecond ( self, event ): #ROTATION AXIS
        from RotationAxis import Align as Align
        b = Align(self.param_dict)
        b.Take_Images([0,90,180,270])
        b.Analyse_Images()
        b.Correct_Axis()
        b.Take_Images([270,180,90,0])
        b.Analyse_Images()
        b.Save_Results()
        #b.CleanTempFiles()

        date = datetime.datetime.fromtimestamp(float(self.mymap['RotationAxisDate']))
        self.rotationaxisdate = date.strftime("%d/%m/%y")
        self.secondtxt.SetLabel(self.rotationaxisdate)
        self.secondtxt.SetForegroundColour(self.green)

    def OnThird ( self, event ): #BEAM ALIGNMENT
        from AlignBeam import Align as Align
        c = Align(self.param_dict)
        c.TakeImages()
        c.SaveResults()
        #c.CleanTempFiles()        

        date = datetime.datetime.fromtimestamp(float(self.mymap['AlignBeamDate']))
        self.alignbeamdate = date.strftime("%d/%m/%y")
        self.thirdtxt.SetLabel(self.alignbeamdate)
        self.thirdtxt.SetForegroundColour(self.green)

    def OnFirst ( self, event ): #CREATE DIRS
        from CreateDirs import createDirs as createDirs
        a = createDirs(self.param_dict)
        a.CreateDirs()
        self.first.SetValue(True)

    def OnFourth ( self, event ):
        from SnapShot import Snapshot as Snapshot
        d = Snapshot(self.param_dict)
        d.RunSnapshot()
        self.fourth.SetValue(True)        

    def OnFifth ( self, event ): #CRYOJET
        from CryoJet import CryoJet
        e = CryoJet(self.param_dict)
        e.AlignCryojet()
        e.ArchiveResults()

        date = datetime.datetime.fromtimestamp(float(self.mymap['CryojetDate']))
        self.checkcryodate = date.strftime("%d/%m/%y")
        self.fifthtxt.SetLabel(self.checkcryodate)
        self.fifthtxt.SetForegroundColour(self.green)


    def OnSixth ( self, event ):
        from BeamCentre import TiltTest
        f = TiltTest(self.param_dict)
        f.TakeImages()
        for image in f.imagelist:
            f.DefineParameters(image)
            f.GetLab6Peaks()
            f.MakeFit2dMacro()
        f.RefineBeamcentre()
        f.RefineDistance()
        f.RefinePitchYaw()
        #f.CleanTempFiles()                

        date = datetime.datetime.fromtimestamp(float(self.mymap['BeamcentreDate']))
        self.beamcentredate = date.strftime("%d/%m/%y")
        self.sixthtxt.SetLabel(self.beamcentredate)
        self.sixthtxt.SetForegroundColour(self.green)

    def OnSeventh ( self, event ):
        from TestCrystal import TestCrystal
        g = TestCrystal(self.param_dict)
        g.SetupSnapshots()
        g.CollectDataset()
        g.WaitForProcessing()
        g.HarvestResults()
        #g.CleanTempFiles()
        
        date = datetime.datetime.fromtimestamp(float(self.mymap['TestCrystalDate']))
        self.testcrystaldate = date.strftime("%d/%m/%y")
        self.seventhtxt.SetLabel(self.testcrystaldate)
        self.seventhtxt.SetForegroundColour(self.green)


    def OnEighth ( self, event ):
        self.mymap['ProbeCassette_EPN'] = blconfig.EPN
        self.eighth.SetValue ( True )

    def OnNineth ( self, event ):
        self.mymap['PrepareEAs_EPN'] = blconfig.EPN
        self.nineth.SetValue ( True )

    def OnTenth ( self, event ):
        from FormatReport import FormatReport
        formatreport = FormatReport(self.param_dict)
        if formatreport.ReportDialog('user'):
            output = formatreport.FormatHeader()
            output += formatreport.FormatComment('user')
            output += formatreport.FormatRotationAxis('user')
            output += formatreport.FormatCryoJet('user')
            output += formatreport.FormatAlignBeam('user')
            output += formatreport.FormatBeamCentre('user')
            output += formatreport.FormatTestCrystal('user')
            output += formatreport.FormatFooter()
            formatreport.SaveReport(output, 'user')
            formatreport.CleanTempFiles()
        if formatreport.ReportDialog('elog'):
            output = formatreport.FormatHeader()
            output += formatreport.FormatComment('elog')
            output += formatreport.FormatRotationAxis('elog')
            output += formatreport.FormatCryoJet('elog')
            output += formatreport.FormatAlignBeam('elog')
            output += formatreport.FormatBeamCentre('elog')
            output += formatreport.FormatTestCrystal('elog')
            output += formatreport.FormatFooter()
            formatreport.SaveReport(output, 'elog')
            formatreport.CleanTempFiles()
        self.tenth.SetValue ( True )


if __name__ == '__main__':
    app = wxPySimpleApp()
    m = SetUp()
    m.DefineParameters()
    m.PromptUserchange()
    m.GetPassword()
    m.GetLastCrystal()
    m.GetStaffMember()
    m.InductionForms()
    m.SmallMolecule()
    m.CurrentMessages()
    Window(m.ReturnDictionary())
    app.MainLoop()
