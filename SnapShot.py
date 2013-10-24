'''
#IMPORT LIBRARIES AND SET UP PATHS
'''

import wx, sys, logging, wx.lib.dialogs, ssh, epics, urllib, ast, time
from time import strftime
from os.path import isfile as isfile
from os.path import isdir as isdir
from subprocess import call, Popen, PIPE, STDOUT, check_output
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


class Snapshot():
    """Take a snap shot of the EPICS PVs

    This script simply calls Nathan Cowiesons bash snapshot script
    
    """
    
    '''
    Constructor
    '''
    def __init__(self,param_dict):
        self.param_dict = param_dict
        ###start a log file
        self.logger = logging.getLogger('beamline_setup')
        self.logger.info('Taking snapshot of EPICS PVs')

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

    def RunSnapshot(self):
        ###Log into the admin box and run the snapshot script

        sshc = ssh.SSHClient()
        sshc.set_missing_host_key_policy(ssh.AutoAddPolicy())
        sshc.connect('10.'+str(blconfig.beamlineN)+'.2.21', username='blctl', password=str(self.param_dict['password']))
        command = 'screen -d -m /xray/progs/bin/snapshot.sh '+str(blconfig.ID)
        sshc.exec_command(command)
        sshc.close()

        if blconfig.ID == "MX1":
            self.mymap = RedisHashMap('mx1_beamline_setup')            
        else:
            self.mymap = RedisHashMap('mx2_beamline_setup')

        self.mymap['Snapshot_EPN'] = str(blconfig.EPN)
        self.mymap['SnapshotDate'] = time.time()
        self.logger.info('Snapshot script is finished')
if __name__ == '__main__':
    app = wx.PySimpleApp()
    snapshot = Snapshot('NotDefined')
    snapshot.RunSnapshot()
    del app


