#!/usr/bin/python3
# $Id$
# $Date$

# NOTE: script need to call with root privileges or via "sudo"

# TODO: cannot receive incremental stream: most recent snapshot of backup/test does not match incremental source
# TODO : cannot create snapshot 'zroot-n/test@2014-12-26': dataset already exists

import argparse
import configparser
import time

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

dev_disk = config.get('USB device', 'partuuid', fallback=None)
disk_pool = config.get('USB device', 'backup_pool', fallback='backup')

logger.debug('------ read config file {0} --------'.format(config_file))
logger.debug('dev_disk (partuuid) = {0}'.format(dev_disk))
logger.debug('disk_pool = {0}'.format(disk_pool))

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

# OS type
OS_type = subprocess.getoutput(["uname"])
if OS_type == 'Linux':
    logger.info("OS is " + OS_type)
    dev_disk = '/dev/disk/by-partuuid/' + dev_disk
elif OS_type == 'FreeBSD':
    logger.info("OS is " + OS_type)
    dev_disk = '/dev/gptid/' + dev_disk
else:
    logger.error('UNknow OS ' + OS_type)
    exit(202)

# check USB connection  

for atempt in range(atempts_to_mount):
    exit_code = subprocess.call(['ls', dev_disk])
    if exit_code == 0:
        break
    logger.error("not found " + dev_disk)
    continue_or_exit('device {0} not found.\n'
                     'Connect USB disk...\n'
                     'atempt {1} continue or exit...'.format(dev_disk, atempts_to_mount - atempt), debug_flag)
# noinspection PyUnboundLocalVariable
if exit_code != 0:
    print("device " + dev_disk + " not found. Connect disk...")
    exit(exit_code)

# ############## set direction according command line options ###########
if arg.direction == 'usb':
    dst_SYS = disk_pool
    src_SYS = root_pool
    create_snap_flag = True
elif arg.direction == 'os':
    dst_SYS = root_pool
    src_SYS = disk_pool
    create_snap_flag = False
else:
    logger.error('wrong direction exit ... ')
    exit(201)

# noinspection PyUnboundLocalVariable
logger.debug('<dst_SYS> ' + dst_SYS)
# noinspection PyUnboundLocalVariable
logger.debug('<src_SYS> ' + src_SYS)


# ================================================

# current_date = subprocess.getoutput(['date +"%Y-%m-%d"'])
current_date = time.strftime('%Y-%m-%d_%H:%M:%S')
logger.debug('system date ' + current_date)

# #################### main block #######################

mount_disk(OS_type, dev_disk)

# noinspection PyUnboundLocalVariable
for volume in config.get(host_config, 'volume').split():
    volume_dst_dict = get_specific_snap_list(dst_SYS, volume)
    volume_src_dict = get_specific_snap_list(src_SYS, volume)
    previous_same_snap = same_and_max_val_in_dicts(volume_src_dict, volume_dst_dict)
    newest_src_snap = max_dict_val(volume_src_dict)

    logger.debug('<volume> = {0}'.format(volume))
    logger.debug('<volume_src_dict> {0}'.format(volume_src_dict))
    logger.debug('<volume_dst_dict> {0}'.format(volume_dst_dict))
    logger.info('<previous_same_snap> {0}'.format(previous_same_snap))
    logger.info('<newest_src_snap> {0}'.format(newest_src_snap))

    if OS_type == 'Linux' and volume == '/tmp':
        linux_workaround_yes = True
    else:
        linux_workaround_yes = False

    if create_snap_flag:
        create_new_snap(src_SYS, [volume], current_date, debug_flag)
        if previous_same_snap is None:
            logger.debug('there are no SAME snaps on volume {0}\n sending to USB'.format(volume))
            send_snap_full(src_SYS + volume + '@' + current_date, dst_SYS + volume, debug_flag)
        else:
            logger.debug('found SAME snaps on volume {0}\n'
                         'working in INCREMENTAL mode sending to USB'.format(volume))
            send_snap_incremental(previous_same_snap[0], src_SYS + volume + '@' + current_date, dst_SYS + volume,
                                  debug_flag)
    elif not create_snap_flag:
        if previous_same_snap == newest_src_snap:
            logger.debug('nothing send on OS {0} == {1}'.format(previous_same_snap, newest_src_snap))
        elif previous_same_snap is None:
            logger.debug('there are no SAME snaps on volume {0}\n'
                         'sending to OS'.format(volume))
            linux_workaround_umount(linux_workaround_yes)
            send_snap_full(newest_src_snap[0], dst_SYS + volume, debug_flag)
            linux_workaround_mount(linux_workaround_yes)
        else:
            logger.debug('found SAME snaps on volume {0}  working in INCREMENTAL mode'.format(volume))
            linux_workaround_umount(linux_workaround_yes)
            send_snap_incremental(previous_same_snap[0], newest_src_snap[0], dst_SYS + volume, debug_flag)
            linux_workaround_mount(linux_workaround_yes)

umount_disk(dev_disk)
logger.info("----------- END ------------")
