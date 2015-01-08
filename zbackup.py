#!/usr/bin/python3
# $Id$
# $Date$

# NOTE: script need to call with root privileges or via "sudo"

# TODO: cannot receive incremental stream: most recent snapshot of backup/test does not match incremental source
# TODO : cannot create snapshot 'zroot-n/test@2014-12-26': dataset already exists

import argparse
import configparser

from zbackup_lib import *

# ############# constant values #################
config_file = 'zbackup.ini'
atempts_to_mount = 3


# ################ command line arguments ###########################
help_info = 'snapshots sending direction to \'usb\' or \'os\''
parser = argparse.ArgumentParser(description='Arguments from command line')
parser.add_argument('direction', action='store', type=str, help=help_info, choices=['usb', 'os'])

arg_group_v_q = parser.add_mutually_exclusive_group()
arg_group_v_q.add_argument('-v', '--verbosity', action='count',
                           # it alwayes set 2, if -v == 3, -vv == 4
                           default=2,
                           help='DEBUG on')
arg_group_v_q.add_argument("-q", "--quiet", action="store_true",
                           help='be quiet, only CRITICAL logs')
arg = parser.parse_args()

# print(arg.verbosity)
debug_flag = False
if arg.quiet:
    logging_level = 40
    # logging.ERROR
    # CRITICAL = 50
elif arg.verbosity >= 3:
    logging_level = 10
    debug_flag = True
    # logging.DEBUG
    # NOTSET = 0
else:
    logging_level = 20
    # logging.INFO
    # logging.WARNING = 30
# #################### logging block ##################
formatter = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging_level,
                    # filename='zbackup.log',
                    format=formatter,
                    handlers=[logging.FileHandler("zbackup.log"),
                              logging.StreamHandler()])

logger = logging.getLogger(__name__)

logger.info("----------- start working ------------")

# ############## read config file ################
config = configparser.ConfigParser()
config.read(config_file)

partuuid = config.get('USB device', 'partuuid', fallback=None)
pool = config.get('USB device', 'backup_pool', fallback='backup')
truecrypt = config.getboolean('USB device', 'truecrypt', fallback=True)
# config.BOOLEAN_STATES = {'yes': True, 'Yes': True, 'YES': True}

logger.debug('------ read config file {0} --------'.format(config_file))
logger.debug('dev_disk (partuuid) = {0}'.format(partuuid))
logger.debug('disk_pool = {0}'.format(pool))

# ## search zpool guid in config file and implement appropriate config section
zpool_get_guid = subprocess.getoutput('zpool get guid').split()
logger.debug('zpool_get_guid = {0}'.format(str(zpool_get_guid)))

for i in config.sections():
    if not i.startswith('host'):
        continue
    logger.debug('check config file section= {0}, guid= {1}'.format(i, config.get(i, 'guid')))
    if config.get(i, 'guid') in zpool_get_guid:
        # get pool name from 'zpool get guid' output
        root_pool_index = zpool_get_guid.index(config.get(i, 'guid')) - 2
        root_pool = zpool_get_guid[root_pool_index]
        host_config = i
        # root_pool = config.get(i, 'root_pool', fallback=None)
        break
else:
    logger.critical('there is CRITICAL error in config file\n'
                    'there are no any guid or host section in config file, in \'zpool get guid\' output\n'
                    'exit...')
    exit(202)
# noinspection PyUnboundLocalVariable
logger.debug('root_pool = {0}'.format(root_pool))

usb_disk = Pool(pool, partuuid)  # init USB disk
usb_disk.mount(atempts_to_mount)

# ############## set direction according command line options ###########
if arg.direction == 'usb':
    send_volume = ToUSB(root_pool, usb_disk.pool, debug_flag)
elif arg.direction == 'os':
    send_volume = ToOS(usb_disk.pool, root_pool, debug_flag)
else:
    logger.error('wrong direction exit ... ')
    exit(201)

# #################### main block #######################
# noinspection PyUnboundLocalVariable
for volume in config.get(host_config, 'volume').split():
    # noinspection PyUnboundLocalVariable
    logger.debug('INIT==> {0}'.format(send_volume))
    send_volume.generate_dicts(volume)
    if volume == '/tmp' and usb_disk.OS_type == 'Linux':
        send_volume.linux_workarount = True
    # else:
    # send_volume.linux_workarount = False
    logger.debug('UPDATE==> {0}'.format(send_volume))
    send_volume.snap()

usb_disk.umount()
logger.info("----------- END ------------")
