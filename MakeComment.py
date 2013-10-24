import wx, logging
from redisobj import RedisHashMap
from beamline import variables as blconfig

class CommentBox(wx.Frame):
    def __init__(self):
        self.logger = logging.getLogger('beamline_setup')
        
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

        
        #make a frame
        wx.Frame.__init__(self, None, wx.ID_ANY, title='Comment to elog')
        #make a panel in the frame
        self.panel = wx.Panel(self, wx.ID_ANY)
        self.panel.SetBackgroundColour(wx.Colour(200,200,180))

        #make a title
        title = wx.StaticText(self.panel, wx.ID_ANY, 'Comment to elog:')

        #make a text input box
        self.text_entry = wx.TextCtrl(self.panel, wx.ID_ANY, self.mymap['elog_comment'], wx.DefaultPosition, wx.Size(600,400), wx.TE_MULTILINE)

        #make a submit button
        SubmitBtn = wx.Button(self.panel, wx.ID_ANY, 'Submit')
        self.Bind(wx.EVT_BUTTON, self.onSubmit, SubmitBtn)
        
        #make a cancel button
        CancelBtn = wx.Button(self.panel, wx.ID_ANY, 'Cancel')
        self.Bind(wx.EVT_BUTTON, self.onCancel, CancelBtn)

        
        topSizer        = wx.BoxSizer(wx.VERTICAL)
        titleSizer      = wx.BoxSizer(wx.HORIZONTAL)
        textInputSizer   = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer        = wx.BoxSizer(wx.HORIZONTAL)


        titleSizer.Add(title, 0, wx.ALL, 5)
        textInputSizer.Add(self.text_entry, 1, wx.ALL|wx.EXPAND, 5)
        btnSizer.Add(SubmitBtn, 0, wx.ALL, 5)
        btnSizer.Add(CancelBtn, 0, wx.ALL, 5)

        topSizer.Add(titleSizer, 0, wx.CENTER)
        topSizer.Add(wx.StaticLine(self.panel), 0, wx.ALL|wx.EXPAND, 5)
        topSizer.Add(textInputSizer, 0, wx.ALL|wx.EXPAND, 5)
        topSizer.Add(btnSizer, 0, wx.ALL|wx.CENTER, 5)

        self.panel.SetSizer(topSizer)
        topSizer.Fit(self)

        self.Show(True)
        
    def onSubmit(self, event):
        self.mymap['elog_comment'] = self.text_entry.GetValue()
        print 'elog comment has been updated'
        print 'comment is now: '+str(self.mymap['elog_comment'])
        self.closeProgram()

    def onCancel(self, event):
        print 'elog comment has not been updated'
        self.closeProgram()
        
    def closeProgram(self):
        self.Close()

if __name__ == '__main__':
    app = wx.App(False)
    frame = CommentBox()
    app.MainLoop()
