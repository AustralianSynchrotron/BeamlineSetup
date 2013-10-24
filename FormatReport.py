'''
#IMPORT LIBRARIES AND SET UP PATHS
'''
import wx, sys, logging, wx.lib.dialogs, ssh, epics, ast, time, glob, re, os, math, requests, glob, datetime, getpass, json
from scipy import optimize
from numpy import mat
from os.path import isfile as isfile
from os.path import isdir as isdir
#from subprocess import call, Popen, PIPE, STDOUT, check_output
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
sys.path.insert(0, '/xray/progs/dcss_test')
from dcss_runs import DCSSRuns

class FormatReport():
    """Writes a report based on calibration data to either elog or the users calibration directory
    
    The FormatReport script uses calibration results from
    /data/home/calibration and redis to format a report
    in the users calibration directory or in elog.
    
    """
    '''
    Constructor
    '''
    
    def __init__(self,param_dict):
        self.imageposturl = 'http://sol.synchrotron.org.au/elog/api/upload'
        self.elogposturl = 'http://sol.synchrotron.org.au/elog/api/newEntry'
        self.user = getpass.getuser()
        self.delete_list = []
        self.param_dict = param_dict
        self.skip = 'No'
        ###start a log file
        self.logger = logging.getLogger('beamline_setup')
        self.logger.info('Making the calibration report')
        self.htmlstyle = '\n<tr class="alt">\n'
        self.html_output = ''



        
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


        if blconfig.ID == "MX1":
            self.beamwidth = "120"
            self.beamheight = "120"
            self.energyhigh = "18"
            self.energylow = "8"
            self.mymap = RedisHashMap('mx1_beamline_setup')
        else:
            self.beamwidth = "20"
            self.beamheight = "10"
            self.energyhigh = "18"
            self.energylow = "8"
            self.mymap = RedisHashMap('mx2_beamline_setup')

        if 'staffName' in self.param_dict.keys():
            self.staffname = self.param_dict['staffName']
        else:
            self.staffname = 'MX staff'



    def FormatHeader(self):
        self.header = '\n\
        <html>\n\
        <head>\n\
        <style type="text/css">\n\
        body {\n\
                height: 297mm;\n\
                width: 210mm;\n\
                margin-left: auto;\n\
                margin-right: auto;\n\
            }\n\
        \n\
        #calibration\n\
        {\n\
        font-family:"Trebuchet MS", Arial, Helvetica, sans-serif;\n\
        width:100%;\n\
        border-collapse:collapse;\n\
        }\n\
        #calibration td, #calibration th \n\
        {\n\
        font-size:1em;\n\
        border:0px solid #98bf21;\n\
        padding:3px 7px 2px 7px;\n\
        }\n\
        #calibration th \n\
        {\n\
        font-size:1.1em;\n\
        text-align:left;\n\
        padding-top:5px;\n\
        padding-bottom:4px;\n\
        background-color:#A7C942;\n\
        color:#ffffff;\n\
        }\n\
        #calibration tr.alt td \n\
        {\n\
        color:#000000;\n\
        background-color:#EAF2D3;\n\
        }\n\
        </style>\n\
        </head>\n\
        \n\
        <body>\n\
        <table id="calibration">\n\
        <tr>\n\
        <th>'+str(blconfig.ID)+' Calibration Report for experiment '+str(blconfig.EPN)+'</th></tr>\n\
        <tr><th>Set up by '+str(self.staffname)+' on the '+str(time.strftime("%d/%m/%y"))+'</th></tr>\n\
        \n\
        '
        return self.header

    def FormatComment(self, action):
        ###SET VARIABLES
        datestamp = datetime.datetime.fromtimestamp(float(self.mymap['TestCrystalDate']))
        created = datestamp.strftime("%d/%m/%y")

        if action == 'user':
            self.logger.info('Will not add beamline setup staff comments to users calibration report')
            self.comment = ""
            
        elif action == 'elog':
            try:
                comment = '<br />'.join(self.mymap['elog_comment'].split('\n'))
            except:
                comment = 'comment absent of could not be formatted for html'
                
            self.logger.info('Write Comments to the setup report in elog')

            ###FORMAT HTML
            if self.htmlstyle == '\n<tr>\n':
                self.htmlstyle = '\n<tr class="alt">\n'
            else:
                self.htmlstyle = '\n<tr>\n'

            self.comment =    self.htmlstyle+'\
            <td><p>STAFF COMMENTS '+str(created)+'</td>\n\
            </tr>\
            '+self.htmlstyle+'\
            <td><p align="center">'+comment+'</p></td>\n\
            </tr>\
            '+self.htmlstyle+'\
            </tr>\n\
            '
        else:
            self.logger.error('Action for FormatComment function MUST be user or elog')
            self.comment = ""

        return self.comment


    def FormatRotationAxis(self, action):
        filename = 'rotation_axis_montage.jpg'
        master_file = '/data/home/calibration/'+filename
        datestamp = datetime.datetime.fromtimestamp(float(self.mymap['RotationAxisDate']))
        created = datestamp.strftime("%d/%m/%y")
        
        ###TEST /DATA/HOME/CALIBRATION FILE EXISTS
        if os.path.isfile(master_file):
            self.logger.info('Format rotation axis report')
        else:
            self.logger.error('No calibration data for rotation axis')
            self.rotation_axis = ''
            return
        
        ###Deal with the images
        if action == 'user':
            ###COPY FROM /DATA/HOME/CALIBRATION TO USER DIR
            self.logger.info('Copy '+str(filename)+' to users calibration directory')
            user_file = self.param_dict['calibrationDir']+'rotation_axis/'+filename

            sshc = ssh.SSHClient()
            sshc.set_missing_host_key_policy(ssh.AutoAddPolicy())
            sshc.connect(self.param_dict['fileserverIP'], username=self.param_dict['username'], password=str(self.param_dict['password']))
            stdin, stdout, stderr = sshc.exec_command('cp '+master_file+' '+user_file)
            self.logger.info('written '+user_file)
            sshc.close()

        elif action == 'elog':
            self.logger.info('Upload rotation axis image to elog')
            files = {'rotation_axis': open(master_file, 'rb')}
            r = requests.post(self.imageposturl, files = files)
            results = json.loads(r.text)
            try:
                if results['rotation_axis']['error']:
                    self.logger.error('There was an error uploading file '+str(master_file))
                else:
                    user_file = results['rotation_axis']['url']
                    self.logger.info('Image uploaded to elog at '+str(user_file))
            except:
                self.logger.error('There was an error uploading file '+str(master_file))
        else:
            self.logger.error('Action for FormatRotationAxis function MUST be user or elog')
            user_file = 'error'

        ###FORMAT HTML
        if self.htmlstyle == '\n<tr>\n':
            self.htmlstyle = '\n<tr class="alt">\n'
        else:
            self.htmlstyle = '\n<tr>\n'


        self.rotation_axis =  self.htmlstyle+'\
        <td><p>ROTATION AXIS '+str(created)+'</td>\
        '+self.htmlstyle+'\
        <td><p align="center"><img src="'+str(user_file)+'" alt="Rotation axis alignment" width="620" height="669" /></p></td>\n\
        </tr>\
        '+self.htmlstyle+'\
        <td><p>The rotation axis was aligned at 0,90,180 and 270 degrees omega using an acupuncture needle. Images at each angle are shown with cross-hairs marking the direct beam position.</p></td>\n\
        </tr>\n\
        '
        return self.rotation_axis
        
    def FormatAlignBeam(self, action):

        ###SET VARIABLES
        filename = 'beamalignment_montage.jpg'
        master_file = '/data/home/calibration/'+filename
        datestamp = datetime.datetime.fromtimestamp(float(self.mymap['AlignBeamDate']))
        created = datestamp.strftime("%d/%m/%y")

        ###TEST /DATA/HOME/CALIBRATION FILE EXISTS
        if os.path.isfile(master_file):
            self.logger.info('Format beam alignment report')
        else:
            self.logger.error('No calibration data for beam alignment')
            self.beam_image = ''
            return

        ###Deal with the images
        if action == 'user':
            ###COPY FROM /DATA/HOME/CALIBRATION TO USER DIR
            self.logger.info('Copy '+str(filename)+' to users calibration directory')
            user_file = self.param_dict['calibrationDir']+'beam_image/'+filename

            sshc = ssh.SSHClient()
            sshc.set_missing_host_key_policy(ssh.AutoAddPolicy())
            sshc.connect(self.param_dict['fileserverIP'], username=self.param_dict['username'], password=str(self.param_dict['password']))
            stdin, stdout, stderr = sshc.exec_command('cp '+master_file+' '+user_file)
            self.logger.info('written '+user_file)
            sshc.close()

        elif action == 'elog':
            self.logger.info('Upload beam image to elog')
            files = {'beam_image': open(master_file, 'rb')}
            r = requests.post(self.imageposturl, files = files)
            results = json.loads(r.text)
            try:
                if results['beam_image']['error']:
                    self.logger.error('There was an error uploading file '+str(master_file))
                else:
                    user_file = results['beam_image']['url']
                    self.logger.info('Image uploaded to elog at '+str(user_file))
            except:
                self.logger.error('There was an error uploading file '+str(master_file))
        else:
            self.logger.error('Action for FormatAlignBeam function MUST be user or elog')
            user_file = 'error'

        ###FORMAT HTML
        if self.htmlstyle == '\n<tr>\n':
            self.htmlstyle = '\n<tr class="alt">\n'
        else:
            self.htmlstyle = '\n<tr>\n'

        self.beam_image =    self.htmlstyle+'\
        <td><p>BEAM IMAGE '+str(created)+'</td>\n\
        </tr>\
        '+self.htmlstyle+'\
        <td><p align="center"><img src="'+str(user_file)+'" alt="Beam Image" width="620" height="234" /></p></td>\n\
        </tr>\
        '+self.htmlstyle+'\
        <td><p> The x-ray beam is imaged on a fluorescing yttrium aluminium garnet (YAG) crystal both at the sample position (left hand image) and at the shutter (right hand image). The shutter image is used for steering the beam. The dimensions of the beam at the sample are approximately '+str(self.beamwidth)+'x'+str(self.beamheight)+' microns (FWHM).</p></td>\n\
        </tr>\n\
        '
        return self.beam_image
        
    def FormatBeamCentre(self, action):
        ###SET VARIABLES
        filename = 'beamcenterlog.png'
        master_file = '/data/home/calibration/'+filename
        datestamp = datetime.datetime.fromtimestamp(float(self.mymap['BeamcentreDate']))
        created = datestamp.strftime("%d/%m/%y")

        try:
            distancetext = 'From a LaB6 image taken at a detector distance of '+self.mymap['ExpectedDist']+' mm the true distance was refined to be '+self.mymap['RefinedDist']+' mm.'
        except:
            distancetext = ''

        ###TEST /DATA/HOME/CALIBRATION FILE EXISTS
        if os.path.isfile(master_file):
            self.logger.info('Format beam centre report')
        else:
            self.logger.error('No calibration data for beam centre')
            self.rotation_axis = ''
            return

        ###Deal with the images
        if action == 'user':
            ###COPY FROM /DATA/HOME/CALIBRATION TO USER DIR
            self.logger.info('Copy '+str(filename)+' to users calibration directory')
            user_file = self.param_dict['calibrationDir']+'beam_centre/'+filename

            sshc = ssh.SSHClient()
            sshc.set_missing_host_key_policy(ssh.AutoAddPolicy())
            sshc.connect(self.param_dict['fileserverIP'], username=self.param_dict['username'], password=str(self.param_dict['password']))
            stdin, stdout, stderr = sshc.exec_command('cp '+master_file+' '+user_file)
            self.logger.info('written '+user_file)
            sshc.close()

        elif action == 'elog':
            self.logger.info('Upload beam centre image to elog')
            files = {'beam_centre': open(master_file, 'rb')}
            r = requests.post(self.imageposturl, files = files)
            results = json.loads(r.text)
            try:
                if results['beam_centre']['error']:
                    self.logger.error('There was an error uploading file '+str(master_file))
                else:
                    user_file = results['beam_centre']['url']
                    self.logger.info('Image uploaded to elog at '+str(user_file))
            except:
                self.logger.error('There was an error uploading file '+str(master_file))
        else:
            self.logger.error('Action for FormatBeamCentre function MUST be user or elog')
            user_file = 'error'


        ###FORMAT HTML
        if self.htmlstyle == '\n<tr>\n':
            self.htmlstyle = '\n<tr class="alt">\n'
        else:
            self.htmlstyle = '\n<tr>\n'

        self.beamcentre =    self.htmlstyle+'\
        <td><p>BEAM CENTRE ON DETECTOR '+str(created)+'</td>\n\
        </tr>\
        '+self.htmlstyle+'\
        <td><p align="center"><img src="'+str(user_file)+'" alt="Beam Centre" width="480" height="360" /></p></td>\n\
        </tr>\
        '+self.htmlstyle+'\
        <td><p> Powder diffraction from Lanthanum hexaborate (LaB6) was measured at several detector distances. The beam centre on the detector was determined from the diffraction rings and a straight line formula derived to describe the horizontal and vertical beam position as a function of distance. This formula is used to calculate the direct beam position in the image headers and this position is accurate to 100 microns. '+distancetext+'</p></td>\n\
        </tr>\n\
        '

        return self.beamcentre

    def FormatTestCrystal(self, action):
        ###SET VARIABLES

        if action == 'user':
            self.logger.info('Write TestCrystal stats to setup report in the users calibration directory')
        elif action == 'elog':
            self.logger.info('Write TestCrystal stats to setup report in elog')
        else:
            self.logger.error('Action for TestCrystal function MUST be user or elog')

            
        datestamp = datetime.datetime.fromtimestamp(float(self.mymap['TestCrystalDate']))
        created = datestamp.strftime("%d/%m/%y")

        #self.mymap['TestCrystalStats']

        ###FORMAT HTML
        if self.htmlstyle == '\n<tr>\n':
            self.htmlstyle = '\n<tr class="alt">\n'
        else:
            self.htmlstyle = '\n<tr>\n'

        self.testcrystal =    self.htmlstyle+'\
        <td><p>TEST CRYSTAL '+str(created)+'</td>\n\
        </tr>\
        '+self.htmlstyle+'\
        <td><p align="center">'+self.mymap['TestCrystalStats']+'</p></td>\n\
        </tr>\
        '+self.htmlstyle+'\
        <td><p>A diffraction dataset was collected from a crystal of a protein standard. The merging statistics in the low resolution bins are checked to ensure that the beamline is producing data of a high quality.</p></td>\n\
        </tr>\n\
        '

        return self.testcrystal

    def FormatCryoJet(self, action):
        ###SET VARIABLES

        if action == 'user':
            self.logger.info('Write Cryojet status to setup report in the users calibration directory')
        elif action == 'elog':
            self.logger.info('Write Cryojet status to setup report in elog')
        else:
            self.logger.error('Action for FormatCryojet function MUST be user or elog')

            
        datestamp = datetime.datetime.fromtimestamp(float(self.mymap['TestCrystalDate']))
        created = datestamp.strftime("%d/%m/%y")


        ###FORMAT HTML
        if self.htmlstyle == '\n<tr>\n':
            self.htmlstyle = '\n<tr class="alt">\n'
        else:
            self.htmlstyle = '\n<tr>\n'

        self.cryojet =    self.htmlstyle+'\
        <td><p>CRYOJET STATUS '+str(created)+'</td>\n\
        </tr>\
        '+self.htmlstyle+'\
        <td><p>A normal sample pin was centred on the cross-hair and the cryojet was aligned with respect to this by '+str(self.staffname)+' on '+str(time.strftime("%d/%m/%y",time.localtime(float(self.mymap['CryojetDate']))))+'. The distance from the end of the cryojet nozzle to the goniometer magnet is set to be 26 mm with the cryojet in the IN position such as during data collection and 32 mm with the cryojet in the OUT position such as during sample exchange by either the robot or the user. The temperature of the cryojet at the time of set up was '+str(self.mymap['CryojetTemp'])+' K, the sample flow rate was '+str(self.mymap['CryojetSampleFlow'])+' l/min, and the shield flow rate was '+str(self.mymap['CryojetShieldFlow'])+' l/min.</p></td>\n\
        </tr>\n\
        '

        return self.cryojet

    def FormatFooter(self):
        self.footer = '\n\
        </table>\n\
        </body>\n\
        </html>\n\
        '
        return self.footer

        
    def SaveReport(self, html_output, action):
        self.html_output = html_output

        if action == 'user':
            local_file = '/var/tmp/'+str(self.user)+'_calibration_report.html'
            self.delete_list.append(local_file)

            with open(local_file, 'w') as htmlfile:
                htmlfile.write(self.html_output)
            
            ###transfer html to users calibration dir

            remote_file = self.param_dict['calibrationDir']+'calibration_report.html'
            t = ssh.Transport((self.param_dict['fileserverIP'],22))
            t.connect(username=str(self.param_dict['username']), password=str(self.param_dict['password']))
            sftp = ssh.SFTPClient.from_transport(t)
            sftp.put(local_file, remote_file)
            t.close()

            self.mymap['FormatReport_EPN'] = str(blconfig.EPN)
            self.logger.info('Saved report to '+str(remote_file))
        elif action == 'elog':
            url = 'http://sol.synchrotron.org.au/elog/api/newEntry'
            payload = {
            'apikey':'970fd633',
            'group':blconfig.ID,
            'severity':'Information',
            'keyword[]': 'Automated',
            'title':blconfig.ID+': Beamline Setup',
            'author':self.staffname,
            'text': self.html_output
            }
            r = requests.post(url, payload)
            response = json.loads(r.text)
            if response['error']:
                self.logger.error('Upload to elog failed with the error code '+str(response['error']))
            else:
                self.logger.info('Successfully uploaded report to elog')            
        else:
            self.logger.error('Action for SaveReport function MUST be user or elog')
            
    def CleanTempFiles(self):
        no_duplicates = list(set(self.delete_list))
        for file in no_duplicates:
            try:
                os.remove(file)
            except:
                self.logger.info('Could not delete '+file)


    def ReportDialog(self, action):
        if action == 'user':
            message = 'Would you like to write a calibration report in the users calibration directory?'
            log_message = 'write report into calibration directory'
        elif action == 'elog':
            message = 'Would you like to upload this calibration report to elog?'
            log_message = 'upload report to elog'
        else:
            self.logger.error('Action for ReportDialog function MUST be user or elog')
            return False
        
        response = wx.lib.dialogs.messageDialog(title='FormatReport', message=message,aStyle=wx.YES_NO)

        if response.returnedString == "Yes":
            self.logger.info('User selected to '+str(log_message))
            return True
        else:
            self.logger.info('User input NOT to '+str(log_message))
            return False

if __name__ == '__main__':
    app = wx.PySimpleApp()
    formatreport = FormatReport('NotDefined')
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
    del app
