#!/usr/bin/python3
# $Id$
# $Date$

# NOTE: script need to call with root privileges or via "sudo"

# TODO : exceptions 
# TODO : check mounted disk or not, partly DONE
# TODO : check if there is snap on disk, if not import it fully


import argparse
import configparser

from zbackup_lib import *
from zbackup_lib2 import *


# ############# constant values #################
config_file = 'zbackup.ini'
atempts_to_mount = 3


# ################ command line arguments ###########################
help_info = 'snapshots sending direction to usb or os'
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
if arg.quiet:
    logging_level = 40
    # logging.ERROR
    # CRITICAL = 50
# elif args.verbosity <= 2:
# logging_level = 20
# logging.INFO
# logging.WARNING = 30
elif arg.verbosity >= 3:
    logging_level = 10
    # logging.DEBUG
    # NOTSET = 0
else:
    logging_level = 20

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
        root_pool_index = zpool_get_guid.index(config.get(i, 'guid')) - 2
        root_pool = zpool_get_guid[root_pool_index]
        host_config = i
        # root_pool = config.get(i, 'root_pool', fallback=None)
        break
else:
    logger.critical('there are no any guid from config file, in \'zpool get guid\' output\nexit...')
    exit(202)
# noinspection PyUnboundLocalVariable
logger.debug('root_pool = {0}'.format(root_pool))

# OS type
OS_type = subprocess.getoutput(["uname"])
if OS_type == 'Linux':
    logger.info("OS is " + OS_type)
    dev_disk = '/dev/disk/by-partuuid/' + dev_disk
    # TODO check and delete below string
# root_pool = Linux_zpool
elif OS_type == 'FreeBSD':
    logger.info("OS is " + OS_type)
    dev_disk = '/dev/gptid/' + dev_disk
# root_pool = FreeBSD_zpool
else:
    logger.error('UNknow OS ' + OS_type)
    exit(202)

# check USB connection  

for i in range(atempts_to_mount):
    exit_code = subprocess.call(['ls', dev_disk])
    if exit_code == 0:
        break
    logger.error("not found " + dev_disk)
    print("device " + dev_disk + " not found. \nConnect USB disk...")
    null_val = input('and push enter... ' + str(atempts_to_mount - i))
# noinspection PyUnboundLocalVariable
if exit_code != 0:
    print("device " + dev_disk + " not found. Connect disk...")
    exit(exit_code)

# ############## set direction according command line options ###########
if arg.direction == 'usb':
    dst_SYS = disk_pool
    src_SYS = root_pool
elif arg.direction == 'os':
    dst_SYS = root_pool
    src_SYS = disk_pool
else:
    logger.error('wrong direction exit ... ')
    exit(201)

# noinspection PyUnboundLocalVariable
logger.debug('<dst_SYS> ' + dst_SYS)
# noinspection PyUnboundLocalVariable
logger.debug('<src_SYS> ' + src_SYS)


# ================================================

current_date = subprocess.getoutput(['date +"%Y-%m-%d"'])
logger.debug('system date ' + current_date)

# #################### main block #######################

mount_disk(OS_type, dev_disk)

for volume in config.get(host_config, 'volume').split():
    logger.debug('<volume> = {0}'.format(volume))
    volume_dst_dict = get_specific_snap_list(dst_SYS, volume)
    volume_src_dict = get_specific_snap_list(src_SYS, volume)
    logger.debug('<volume_src_dict> {0}'.format(volume_src_dict))
    logger.debug('<volume_dst_dict> {0}'.format(volume_dst_dict))
    previous_same_snap = same_and_max_val_in_dicts(volume_src_dict, volume_dst_dict)
    logger.info('<previous_same_snap> {0}'.format(previous_same_snap))

    if previous_same_snap is None:
        logger.debug('there are no SAME snaps on volume {0}'.format(volume))
        logger.debug('create snap {0}'.format(src_SYS + volume + '@' + current_date))
        stop_point = input("stop_pint push enter\n")
        continue_or_exit(query_yes_no('create snap {0} ?'.format(src_SYS + volume + '@' + current_date)))
        exit_code = subprocess.call(['zfs', 'snapshot', src_SYS + volume + '@' + current_date])
        exit_on_error(exit_code)
        logger.info('start sending   FULL snap {0}'.format(src_SYS + volume + '@' + current_date))
        logger.info('start receiving FULL snap {0}'.format(dst_SYS + volume + '@' + current_date))
        stop_point = input("stop_pint push enter delete after check\n")
        p1 = subprocess.Popen(['zfs', 'send', '-v', src_SYS + volume + '@' + current_date], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['zfs', 'receive', '-v', '-F', dst_SYS + volume + '@' + current_date],
                              stdin=p1.stdout,
                              stdout=subprocess.PIPE)
        output = p2.communicate()[0]
        exit_code = p2.returncode
        exit_on_error(exit_code)
    else:
        logger.debug('found SAME snaps on volume {0}  working in INCREMENTAL mode'.format(volume))
        logger.debug('create snap {0}'.format(src_SYS + volume + '@' + current_date))
        stop_point = input("stop_pint push enter\n")
        exit_code = subprocess.call(['zfs', 'snapshot', src_SYS + volume + '@' + current_date])
        exit_on_error(exit_code)
        logger.info('start sending INCREMENTAL snaps {0} and {1}'.format(previous_same_snap[0],
                                                                         src_SYS + volume + '@' + current_date))
        logger.info('start receiving INCREMENTAL snap {0}'.format(dst_SYS + volume + '@' + current_date))
        p1 = subprocess.Popen(
            ['zfs', 'send', '-v', '-i', previous_same_snap[0], src_SYS + volume + '@' + current_date],
            stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['zfs', 'receive', '-v', '-F', dst_SYS + volume + '@' + current_date],
                              stdin=p1.stdout,
                              stdout=subprocess.PIPE)
        output = p2.communicate()[0]
        exit_code = p2.returncode
        exit_on_error(exit_code)

umount_disk(dev_disk)
logger.info("----------- END ------------")
