'''
#IMPORT LIBRARIES AND SET UP PATHS
'''
import wx, sys, logging, wx.lib.dialogs, ssh, epics, urllib, ast, time, glob, re, os, subprocess, numpy, pylab, math, multiprocessing, getpass
from scipy import optimize
from numpy import mat
from os.path import isfile as isfile
from os.path import isdir as isdir
from subprocess import call, Popen, PIPE, STDOUT, check_output
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

import beamline
sys.path.insert(0, '/xray/progs/dcss_test')
from dcss_runs import DCSSRuns

class TiltTest():
    """Sets up for a new tilttest job
    
    The tilttest functions are used by tilttest.py. Given a lanthanum 
    hexaborate powder diffraction sample the script calculates detector
    distance, pitch and yaw.    
    
    """
    
    '''
    Constructor
    '''
    def __init__(self,param_dict):
        self.user = getpass.getuser()
        if beamline.variables.ID == "MX1":
            self.mymap = RedisHashMap('mx1_beamline_setup')
            self.minimum_distance = 72
        else:
            self.minimum_distance = 90
            self.mymap = RedisHashMap('mx2_beamline_setup')

        self.datapoints = {}        
        self.delete_list = []
        self.param_dict = param_dict
        self.skip = 'No'
        ###start a log file
        self.logger = logging.getLogger('beamline_setup')
        self.logger.info('Running TiltTest script')

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

    def TakeImages(self):
        if self.skip == 'Yes':
            return

        ###Work out the next index number for lab6 images in cal dir
        try:
            os.chdir(self.param_dict['calibrationDir']+'beam_centre')
            filelist=glob.glob('lab6*'+'.img')
            if len(filelist) < 1:
                self.index = 0
            else:
                self.index = int(re.split(r'[_.]', filelist[-1])[-2])
        except:
            self.logger.error('the beam_centre dir does not exist')
            self.index = 0

        ###Use bluice DCSS access to automate lab6 images
        #app = wx.PySimpleApp()
        response = wx.lib.dialogs.messageDialog(title='Beamcentre', message='Please mount and centre a LaB6 pin. Search the hutch and open the mono shutter. Bluice will automatically collect LaB6 images. Cancel will skip collection and give opportunity to select previously collected images.')
        #app.Yield()
        #del app

        


        if response.returnedString == "Cancel":
            self.logger.info('Skipping LaB6 image collection')
            self.skip = "Yes"
        else:
            #app = wx.PySimpleApp()
            response_two = wx.lib.dialogs.messageDialog(title='Beamcentre', message='Will move detector to minimum distance ('+str(self.minimum_distance)+' mm), please confirm this is safe!',aStyle=wx.YES_NO)
            #app.Yield()
            #del app

            if response_two.returnedString == "Yes":
                self.logger.info('Running LaB6 image collection')
                self.skip = "No"
            else:
                self.logger.info('Skipping LaB6 image collection')
                self.skip = "Yes"
                self.logger.info('Running LaB6 image collection')
                self.skip = "No"


        if beamline.variables.ID == "MX1":
            self.distances=[self.minimum_distance,100,200,300,400]
            self.dcssArgs = {'status': None,
            'exposure_time': 5,
            'attenuation': 95,
            'run': 0,
            'start_frame': self.index,
            'start_angle': 0,
            'debug': False,
            'end_angle': None,
            'collect': False,
            'energy1': beamline.energy.eV,
            'next_frame': 0,
            'delta': 30,
            'directory': self.param_dict['calibrationDir']+'beam_centre',
            'file_root': 'lab6',
            'beam_stop': None,
            'distance': 400}

        if beamline.variables.ID == "MX2":
            self.distances=[self.minimum_distance,100,200,300,400,500]
            self.dcssArgs = {'status': None,
            'exposure_time': 5,
            'attenuation': 95,
            'run': 0,
            'start_frame': self.index,
            'start_angle': 0,
            'debug': False,
            'end_angle': None,
            'collect': False,
            'energy1': beamline.energy.eV,
            'next_frame': 0,
            'delta': 30,
            'directory': self.param_dict['calibrationDir']+'beam_centre',
            'file_root': 'lab6',
            'beam_stop': None,
            'distance': 400}

        if self.skip == "No":
            runs = DCSSRuns()
            self.imagelist = []
            for dist in self.distances:
                self.dcssArgs['distance'] = dist
                self.dcssArgs['start_frame'] += 1
                imagename = self.param_dict['calibrationDir']+'beam_centre/'+str(self.dcssArgs['file_root'])+'_'+str(self.dcssArgs['run'])+'_'+str(str(self.dcssArgs['start_frame']).zfill(3))+'.img'

                if dist == 100:
                    self.param_dict['tilttest_file'] = imagename
                
                self.imagelist.append(imagename)
                self.logger.info('Taking image '+imagename+' at distance '+str(dist))
                runs.set_run('run%s' % self.dcssArgs['run'], **self.dcssArgs)
                runs.start_run(self.dcssArgs['run'])

            self.param_dict['lab6_images'] = self.imagelist
        else:
            #app = wx.PySimpleApp()
            wildcard = "Image files (*.img)|*.img|" \
                       "All files (*.*)|*.*"
            response = wx.lib.dialogs.openFileDialog(title='Choose Lab6 images', directory=self.param_dict['calibrationDir']+'beam_centre/', wildcard=wildcard, style=wx.OPEN | wx.MULTIPLE | wx.CHANGE_DIR)
            #app.Yield()
            #del app
            
            if response.returnedString == "Cancel":
                self.logger.info('No lab6 images, skipping beamcentre step')
                self.skip = "Yes"
            else:
                self.imagelist = response.paths
                self.param_dict['lab6_images'] = self.imagelist
                self.skip = "No"

    def DefineParameters(self,image):
        if self.skip == "Yes":
            return

        self._path_and_imagename = image

        ###test if image exists
        if not isfile(self._path_and_imagename):        
            self.logger.error('Image '+str(self._path_and_imagename)+' does not exist')
            self.skip = "Yes"
            return

        ###harvest header info
        imagefile = open(self._path_and_imagename, "r")
        fileheader = imagefile.read(1024)
        imagefile.close()

        self.header_dict = {}

        for line in (''.join(fileheader)).split('\n')[1:-1]:
            try:
                self.header_dict[((line.replace('=',' ').replace(';','')).split())[0]]=((line.replace('=',' ').replace(';','')).split())[1]
            except:
                pass
        ###prepare output file
        try:
            self.outputfile = open('/var/tmp/'+str(self.user)+'_tilttest_output.txt', "w")
            self.delete_list.append('/var/tmp/'+str(self.user)+'_tilttest_output.txt')
            output_string = '"twotheta angle (deg)","X beamcentre (px)","Y beamcentre (px)","Detector distance (mm)"\n'
            self.outputfile.write(output_string)
            self.outputfile.close()
        except:
            self.logger.error('cannot write to output file /var/tmp/'+str(self.user)+'_tilttest_output.txt')
            self.skip = "Yes"
            return
        
        ###test output
        try:
            self.pixelsize_mm = float(self.header_dict['PIXEL_SIZE'])
            self.wavelength_A = float(self.header_dict['WAVELENGTH'])
            self.distance_mm = float(self.header_dict['DISTANCE'])
            self.detectorsize_pixels = float(self.header_dict['SIZE1'])
            self.detectorsize_mm = self.detectorsize_pixels * self.pixelsize_mm
            self.beamx_mm = float(self.header_dict['BEAM_CENTER_X'])
            self.beamx_pixels = self.beamx_mm / self.pixelsize_mm
            self.beamy_mm = float(self.header_dict['BEAM_CENTER_Y'])
            self.beamy_pixels = self.beamy_mm / self.pixelsize_mm
            self.logger.info('Got header info from image at '+str(self.distance_mm)+' mm')
            return 'PASS'
        
        except:
            self.logger.error('Cannot harvest header records from image')
            self.skip = "Yes"
            return 'FAIL'

    def GetLab6Peaks(self):
        if self.skip == "Yes":
            return
        ###define some parameters
        temperature = 295.65
        expansion_coefficient = 6.4e-6
        a = 4.156919032 # FOR 660a at 295.65 K (22.5 degrees C)
        #a = 4.1569118   # FOR 660b at 295.65 K (22.5 degrees C)

        a = a + (temperature - 295.65) * expansion_coefficient #correct a for thermal expansion
        indices = [[1,0,0],[1,1,0],[1,1,1],[2,0,0],[2,1,0],[2,1,1],[2,2,0],[3,0,0],[3,1,0],[3,1,1],[2,2,2],[3,2,0],[3,2,1],[4,0,0],[4,1,0],[4,1,1],[3,3,1],[4,2,0],[4,2,1],[3,3,2],[4,2,2],[5,0,0],[5,1,0],[5,1,1]]

        ###define lab6 dspacings in mm!
        self.dspacings = []
        for index in indices:
            d = math.sqrt(1 / (( (index[0]**2) + (index[1]**2) + (index[2]**2) ) / ( a**2 )))
            self.dspacings.append(d)

        ###define lab6 2theta in radians!
        self.twotheta = []
        for dspacing in self.dspacings:
            theta = math.asin(( self.wavelength_A ) / ( 2*dspacing ))
            self.twotheta.append(2 * theta)
        
        ###define lab6 peaks in mm!
        self.peaks = []
        for angle in self.twotheta:
            peak = (self.distance_mm * math.tan(angle))
            self.peaks.append(peak)

        ###calculate which peaks are on the image
        centre_to_edge = []
        centre_to_edge.append(self.beamx_mm)                             #centre_to_left  
        centre_to_edge.append(self.detectorsize_mm - self.beamx_mm)      #centre_to_right 
        centre_to_edge.append(self.beamy_mm)                             #center_to_top   
        centre_to_edge.append(self.detectorsize_mm - self.beamy_mm)      #center_to_bottom
        self.max_peak = max(centre_to_edge)
        self.rings = []
        for peak in self.peaks:
            if peak <= self.max_peak:
                self.rings.append(peak)

        self.logger.info('Defined position of '+str(len(self.rings))+' LaB6 peaks on the image')

        self.delete_list.append('/var/tmp/'+str(self.user)+'_calibrant.Ds')
        with open('/var/tmp/'+str(self.user)+'_calibrant.Ds', 'w') as calfile:
            for d in self.dspacings:
                calfile.write(str(d)+'\n')


        
    def MakeFit2dMacro(self):
        if self.skip == "Yes":
            return


        self.radius_px = float(sorted(self.rings)[0]) / float(self.pixelsize_mm)
        self.firstpoint_x = float(self.beamy_pixels)
        self.firstpoint_y = float(self.beamx_pixels) + float(self.radius_px) 
        self.secondpoint_x = float(self.beamy_pixels)
        self.secondpoint_y = float(self.beamx_pixels) - float(self.radius_px) 
        self.thirdpoint_x = float(self.beamy_pixels) + float(self.radius_px) 
        self.thirdpoint_y = float(self.beamx_pixels)
        self.fourthpoint_x = float(self.beamy_pixels) - float(self.radius_px) 
        self.fourthpoint_y = float(self.beamx_pixels)

        self.delete_list.append('/var/tmp/'+str(self.user)+'_fit2d.mac')
        with open('/var/tmp/'+str(self.user)+'_fit2d.mac', 'w') as macfile:
                  macfile.write('%!*\ START OF MACRO FILE\n')
                  macfile.write('I ACCEPT\n')
                  macfile.write('POWDER DIFFRACTION (2-D)\n')
                  macfile.write('INPUT\n')
                  macfile.write(str(self._path_and_imagename)+'\n')
                  macfile.write('O.K.\n')
                  macfile.write('CALIBRANT\n')
                  macfile.write('USER DEFINED\n')
                  macfile.write('/var/tmp/'+str(self.user)+'_calibrant.Ds\n')
                  macfile.write('REFINE WAVELENGTH\n')
                  macfile.write('NO\n')
                  macfile.write('DISTANCE\n')
                  macfile.write(str(self.distance_mm)+'\n')
                  macfile.write('WAVELENGTH\n')
                  macfile.write(str(self.wavelength_A)+'\n')
                  macfile.write('X-PIXEL SIZE\n')
                  macfile.write(str(self.pixelsize_mm * 1000)+'\n')
                  macfile.write('Y-PIXEL SIZE\n')
                  macfile.write(str(self.pixelsize_mm * 1000)+'\n')
                  macfile.write('O.K.\n')
                  macfile.write('4\n')
                  macfile.write(str(self.firstpoint_x)+'\n')
                  macfile.write(str(self.firstpoint_y)+'\n')
                  macfile.write(str(self.secondpoint_x)+'\n')
                  macfile.write(str(self.secondpoint_y)+'\n')
                  macfile.write(str(self.thirdpoint_x)+'\n')
                  macfile.write(str(self.thirdpoint_y)+'\n')
                  macfile.write(str(self.fourthpoint_x)+'\n')
                  macfile.write(str(self.fourthpoint_y)+'\n')
                  macfile.write('O.K.\n')
                  macfile.write('EXIT\n')
                  macfile.write('EXIT FIT2D\n')
                  macfile.write('YES\n')
                  macfile.write('%!*\ END OF MACRO FILE\n')




        fit2d_command = 'fit2d -dim'+str(int(self.detectorsize_pixels))+'x'+str(int(self.detectorsize_pixels))+' -mac/var/tmp/'+str(self.user)+'_fit2d.mac'

        p = Popen(fit2d_command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        fit2d_output = p.stdout.readlines()

        try:
            ###GET DISTANCE
            index = [i for i, item in enumerate(fit2d_output) if re.search('.*Refined sample to detector distance =.*', item)][-1]
            self.refined_distance = fit2d_output[index].split()[7]

            ###GET PITCH AND YAW
            index = [i for i, item in enumerate(fit2d_output) if re.search('.*INFO: ROT X =.*', item)][-1]
            self.refined_yaw = fit2d_output[index].split()[4]
            self.refined_pitch = fit2d_output[index].split()[8]

            ###GET WAVELENGTH
            index = [i for i, item in enumerate(fit2d_output) if re.search('.*INFO: Refined wavelength =.*', item)][-1]
            self.refined_wavelength = fit2d_output[index].split()[4]

            ###GET BEAMCENTRE X AND Y PIXELS
            index = [i for i, item in enumerate(fit2d_output) if re.search('.*INFO: Refined Beam centre =.*(pixels).*', item)][-1]
            self.refined_beamcentrex_px = fit2d_output[index].split()[6]
            self.refined_beamcentrey_px = fit2d_output[index].split()[5]

            ###GET BEAMCENTRE X AND Y MM
            index = [i for i, item in enumerate(fit2d_output) if re.search('.*INFO: Refined Beam centre =.*(mm).*', item)][-1]
            self.refined_beamcentrex_mm = fit2d_output[index].split()[6]
            self.refined_beamcentrey_mm = fit2d_output[index].split()[5]

            print "###IMAGE "+str(self._path_and_imagename)
            print "DISTANCE:   "+str(self.refined_distance)+" ("+str(self.distance_mm)+")"
            print "WAVELENGTH: "+str(self.refined_wavelength)+" ("+str(self.wavelength_A)+")"
            print "PITCH:      "+str(self.refined_pitch)+" deg"
            print "YAW:        "+str(self.refined_yaw)+" deg"
            print "BEAM X PX:  "+str(self.refined_beamcentrex_px)+" ("+str(self.beamx_pixels)+")"
            print "BEAM Y PX:  "+str(self.refined_beamcentrey_px)+" ("+str(self.beamy_pixels)+")"      
            print "BEAM X MM:  "+str(self.refined_beamcentrex_mm)+" ("+str(self.beamx_mm)+")"
            print "BEAM Y MM:  "+str(self.refined_beamcentrey_mm)+" ("+str(self.beamy_mm)+")"      
            print " "

            self.datapoints[float(self.distance_mm)] = [float(self.refined_distance),float(self.refined_wavelength),float(self.refined_pitch),float(self.refined_yaw),float(self.refined_beamcentrex_px),float(self.refined_beamcentrey_px),float(self.refined_beamcentrex_mm),float(self.refined_beamcentrey_mm)]
        except:
            self.logger.error('fit2d did not run for '+str(self._path_and_imagename))

    def RefineBeamcentre(self):
        if len(self.datapoints.keys()) < 3:
            self.logger.error('There were insufficient points to run fitting')
            return
        
        ###FITTING X DATA
        self.logger.info('Fitting beam centre X data')
        #self.datapoints =  {200.042: [199.629, 0.7118, 0.08, -0.11, 1023.576, 1000.852, 104.814, 102.487], 100.127: [99.407, 0.71212, 0.086, -0.085, 1022.71, 996.901, 104.725, 102.083], 400.085: [398.985, 0.7139, 0.089, -0.168, 1025.239, 1007.103, 104.984, 103.127], 300.068: [299.811, 0.71197, 0.083, -0.119, 1024.24, 1004.715, 104.882, 102.883], 72.043: [71.507, 0.71192, 0.084, -0.104, 1022.335, 996.086, 104.687, 101.999]}

        x = self.datapoints.keys()
        y = []
        for value in x:
            y.append(self.datapoints[value][6])

        x = numpy.array(x)
        y = numpy.array(y)
        
        
        def f(x, m, c):
            return (m * x + c)
        
        def resid(p, y, x):
            m, c = p
            return y - f(x, m, c)
        
        m0, c0 = 1,1024
        
        [m, c], flag = optimize.leastsq(resid, [m0, c0], args=(y, x))
        
        ###CREATE A PYLAB PLOT OBJECT
        self.myfigure = pylab.figure()  
        self.myplot = self.myfigure.add_subplot(111)
        self.myplot.set_title('Deviation of beam centre X (blue) and Y (green) as a function of distance')
        self.myplot.set_xlabel('Distance (mm)')
        self.myplot.set_ylabel('Beam centre (pixels)')

        #plot the datapoints
        self.myplot.plot(x, y, 'ro')
        
        # plot the smooth model fit
        xc = numpy.linspace(x.min(), x.max(), 2)
        self.myplot.plot(xc, f(xc, m, c ))
        
        
        self.xbeam_m = m
        self.xbeam_c = c

        ###FITTING Y DATA
        self.logger.info('Fitting beam centre Y data')

        x = self.datapoints.keys()
        y = []
        for value in x:
            y.append(self.datapoints[value][7])

        x = numpy.array(x)
        y = numpy.array(y)
                
        def f(x, m, c):
            return (m * x + c)
        
        def resid(p, y, x):
            m, c = p
            return y - f(x, m, c)
        
        m0, c0 = 1,1024
        
        [m, c], flag = optimize.leastsq(resid, [m0, c0], args=(y, x))
        
        #add datapoints to pylab plot
        self.myplot.plot(x, y, 'ro')
        
        # plot the smooth model fit
        xc = numpy.linspace(x.min(), x.max(), 2)
        self.myplot.plot(xc, f(xc, m, c ))

        #save the plot to file
        output_image='/var/tmp/'+str(self.user)+'_beamcentre_fit.png'
        self.delete_list.append(output_image)
        self.myfigure.savefig(output_image, format="png")

        self.ybeam_m = m
        self.ybeam_c = c

        ###USE THE RESULTS
         
        if beamline.variables.ID == 'MX2':
            xslope_pv = 'SR03ID01HU02IOC09:ADSC_XBEAM_SLOPE'
            xicpt_pv = 'SR03ID01HU02IOC09:ADSC_XBEAM_INTERCEPT'
            yslope_pv = 'SR03ID01HU02IOC09:ADSC_YBEAM_SLOPE'
            yicpt_pv = 'SR03ID01HU02IOC09:ADSC_YBEAM_INTERCEPT'
            old_mx = epics.caget(xslope_pv)
            old_cx = epics.caget(xicpt_pv)
            old_my = epics.caget(yslope_pv)
            old_cy = epics.caget(yicpt_pv)
        elif beamline.variables.ID == 'MX1':
            xslope_pv = 'SR03BM01HU02IOC09:ADSC_XBEAM_SLOPE'
            xicpt_pv = 'SR03BM01HU02IOC09:ADSC_XBEAM_INTERCEPT'
            yslope_pv = 'SR03BM01HU02IOC09:ADSC_YBEAM_SLOPE'
            yicpt_pv = 'SR03BM01HU02IOC09:ADSC_YBEAM_INTERCEPT'
            old_mx = epics.caget(xslope_pv)
            old_cx = epics.caget(xicpt_pv)
            old_my = epics.caget(yslope_pv)
            old_cy = epics.caget(yicpt_pv)
        else:
            self.logger.error('Cannot determine beamline')
            return
        self.logger.info('Change X formula from m = '+str(old_mx)+' to '+str(self.xbeam_m)+' and c = '+str(old_cx)+' to '+str(self.xbeam_c))
        self.logger.info('Change Y formula from m = '+str(old_my)+' to '+str(self.ybeam_m)+' and c = '+str(old_cy)+' to '+str(self.ybeam_c))

        self.myfigure.show()

        #app = wx.PySimpleApp()
        response = wx.lib.dialogs.messageDialog(title='Beamcentre', message='Do you want to update the header records?',aStyle=wx.YES_NO)
        #app.Yield()
        #del app

        if response.returnedString == "No":
            self.logger.info('will not update header records or save images')
            pylab.close('all')
            return
        else:
            self.logger.info('saving images and updating headers')
            pylab.close('all')

        epics.caput(xslope_pv, self.xbeam_m)
        epics.caput(xicpt_pv, self.xbeam_c)
        epics.caput(yslope_pv, self.ybeam_m)
        epics.caput(yicpt_pv, self.ybeam_c)
        self.logger.info('Updated beamcentre PVs in EPICS')

        
        
        ###transfer output image to users calibration dir
        timestamp = time.strftime("%y-%m-%d-%H-%M")
        ###transfer output image to /data/home/calibration dir
        local_file = '/var/tmp/'+str(self.user)+'_beamcentre_fit.png'
        remote_file2 = '/data/home/calibration/beamcenterlog.png'
        remote_file3 = '/data/home/calibration/beamcenter/'+str(timestamp)+'_beamcenterlog.png'
        sshc = ssh.SSHClient()
        sshc.set_missing_host_key_policy(ssh.AutoAddPolicy())
        sshc.connect('localhost', username='blctl', password=str(self.param_dict['password']))
        stdin, stdout, stderr = sshc.exec_command('cp '+local_file+' '+remote_file2)
        self.logger.info('Wrote output to '+str(remote_file2))
        stdin, stdout, stderr = sshc.exec_command('cp '+local_file+' '+remote_file3)
        self.logger.info('Wrote output to '+str(remote_file3))
        sshc.close()


        self.mymap['BeamcentreDate'] = time.time()

    def RefineDistance(self):
        if len(self.datapoints.keys()) < 3:
            return

        ###FITTING X DATA
        self.logger.info('Refining detector distance')
        #self.datapoints =  {200.042: [199.629, 0.7118, 0.08, -0.11, 1023.576, 1000.852, 104.814, 102.487], 100.127: [99.407, 0.71212, 0.086, -0.085, 1022.71, 996.901, 104.725, 102.083], 400.085: [398.985, 0.7139, 0.089, -0.168, 1025.239, 1007.103, 104.984, 103.127], 300.068: [299.811, 0.71197, 0.083, -0.119, 1024.24, 1004.715, 104.882, 102.883], 72.043: [71.507, 0.71192, 0.084, -0.104, 1022.335, 996.086, 104.687, 101.999]}

        working_dist = min(self.datapoints.keys())
        refined_dist = self.datapoints[working_dist][0]
        delta_dist = refined_dist - working_dist

        self.mymap['ExpectedDist'] = str(working_dist)
        self.mymap['RefinedDist'] = str(refined_dist)

        self.logger.info('image at '+str(working_dist)+' mm was refined to '+str(refined_dist)+' mm. A discrepency of '+str(delta_dist)+' mm')
        
        ###USE THE RESULTS
         
        if beamline.variables.ID == 'MX2':
            ccd_z_offset_pv = 'SR03ID01CCD01:Z_MTR_OFFSET_SP'
            ccd_y2_offset_pv = 'SR03ID01CCD01:Y2_MTR_OFFSET_SP'
            self.jack_separation = 302
            old_z_offset = epics.caget(ccd_z_offset_pv)
            self.old_y2_offset = epics.caget(ccd_y2_offset_pv)
        elif beamline.variables.ID == 'MX1':
            ccd_z_offset_pv = 'SR03BM01CCD01:Z_MTR_OFFSET_SP'
            ccd_y2_offset_pv = 'SR03BM01CCD01:Y2_MTR_OFFSET_SP'
            self.jack_separation = 308
            old_z_offset = epics.caget(ccd_z_offset_pv)
            self.old_y2_offset = epics.caget(ccd_y2_offset_pv)
        else:
            self.logger.error('Cannot determine beamline')
            return

        new_offset = float(old_z_offset) - delta_dist
        
        self.logger.info('Distance is off by '+str(delta_dist)+' this can be fixed by changing the CCD Z offset from '+str(old_z_offset)+' to '+str(new_offset))
        if abs(delta_dist) < 0.1:
            self.logger.info('the error in the detector distance is less than the threshold of 0.1 mm, no need to update.')
        else:
            response = wx.lib.dialogs.messageDialog(title='Beamcentre', message='Do you want to change the CCD Z offset from '+str(old_z_offset)+' to '+str(new_offset)+'?\nNote: will not change headers on images already collected. Running repeatedly on the same images will continue to move distance offset.',aStyle=wx.YES_NO)

            if response.returnedString == "No":
                self.logger.info('will not change CCD Z offset')
            else:
                self.logger.info('updating CCD Z offset')
                epics.caput(ccd_z_offset_pv, new_offset)
                self.logger.info('Updated CCD Z offset in EPICS')

    def RefinePitchYaw(self):
        if len(self.datapoints.keys()) < 3:
            return

        ###FITTING X DATA
        #self.datapoints =  {200.042: [199.629, 0.7118, 0.08, -0.11, 1023.576, 1000.852, 104.814, 102.487], 100.127: [99.407, 0.71212, 0.086, -0.085, 1022.71, 996.901, 104.725, 102.083], 400.085: [398.985, 0.7139, 0.089, -0.168, 1025.239, 1007.103, 104.984, 103.127], 300.068: [299.811, 0.71197, 0.083, -0.119, 1024.24, 1004.715, 104.882, 102.883], 72.043: [71.507, 0.71192, 0.084, -0.104, 1022.335, 996.086, 104.687, 101.999]}

        pitch = self.datapoints[min(self.datapoints.keys())][2]
        yaw = self.datapoints[min(self.datapoints.keys())][3]
        new_y2_offset = self.old_y2_offset - ( self.jack_separation * numpy.tan( numpy.radians(pitch) ))
        
        self.logger.info('Detector is pitched by '+str(pitch)+' and yawed by '+str(yaw)+' degrees.')
        self.logger.info('Pitch can be corrected by changing the CCD Y2 OFFSET from '+str(self.old_y2_offset)+' to '+str(new_y2_offset))
        self.logger.info('Yaw can only be corrected by trimming the A frame using the jacking bolts on the feet')

    def CleanTempFiles(self):
        time.sleep(2)#it was deleting the temp files before they'd been copied to /data/home/calibration!
        #all files in delete list are in the /var/tmp dir
        no_duplicates = list(set(self.delete_list))
        for file in no_duplicates:
            try:
                os.remove(file)
            except:
                self.logger.info('Could not delete '+file)
                
if __name__ == '__main__':
    app = wx.PySimpleApp()
    tilttest = TiltTest('NotDefined')
    tilttest.TakeImages()
    for image in tilttest.imagelist:
        tilttest.DefineParameters(image)
        tilttest.GetLab6Peaks()
        tilttest.MakeFit2dMacro()
    tilttest.RefineBeamcentre()
    tilttest.RefineDistance()
    tilttest.RefinePitchYaw()
    tilttest.CleanTempFiles()
    del app
