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


# ############# constant values #################
config_file = 'zbackup.ini'


# ########### flags
send_incremental_snap = []
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

print(arg.verbosity)
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
keyword_snap = config.get('DEFAULT', 'keyword', fallback=None)
pool_list = config.get('DEFAULT', 'pools', fallback='/test@ /home@ /home/vic@').strip().split()
dev_disk = config.get('USB device', 'partuuid', fallback=None)
disk_pool = config.get('USB device', 'backup_pool', fallback='backup')

logger.debug('------ read config file {0} --------'.format(config_file))
logger.debug('keyword_snap= {0}'.format(keyword_snap))
logger.debug('pool_list= {0}'.format(str(pool_list)))
logger.debug('dev_disk (partuuid) = {0}'.format(dev_disk))
logger.debug('disk_pool = {0}'.format(disk_pool))

# ## search zpool guid in config file and implement appropriate config section
# Linux_zpool = "rpool"
# FreeBSD_zpool = "zroot-n"
zpool_get_guid = subprocess.getoutput('zpool get guid').split()
logger.debug('zpool_get_guid = {0}'.format(str(zpool_get_guid)))

for i in config.sections():
    if not i.startswith('host'):
        continue
    logger.debug('check config file section= {0}, guid= {1}'.format(i, config.get(i, 'guid')))
    if config.get(i, 'guid') in zpool_get_guid:
        root_pool_index = zpool_get_guid.index(config.get(i, 'guid')) - 2
        root_pool = zpool_get_guid[root_pool_index]
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

stop_point = input("stop_pint push enter\n")
# check USB connection  
atempts = 3
for i in range(atempts):
    exit_code = subprocess.call(['ls', dev_disk])
    if exit_code == 0:
        break
    logger.error("not found " + dev_disk)
    print("device " + dev_disk + " not found. \nConnect USB disk...")
    null_val = input('and push enter... ' + str(atempts - i))
# noinspection PyUnboundLocalVariable
if exit_code != 0:
    print("device " + dev_disk + " not found. Connect disk...")
    exit(exit_code)

# ############## set direction according command line options ###########
if arg.direction == 'usb':
    dest_SYS = disk_pool
    src_SYS = root_pool
elif arg.direction == 'os':
    dest_SYS = root_pool
    src_SYS = disk_pool
else:
    logger.error('wrong direction exit ... ')
    exit(201)

# noinspection PyUnboundLocalVariable
logger.debug('<dest_SYS> ' + dest_SYS)
# noinspection PyUnboundLocalVariable
logger.debug('<src_SYS> ' + src_SYS)
logger.info('data sets list to work ' + str(pool_list))
logger.debug('keyword for search MY snapshots ' + keyword_snap)

stop_point = input("stop_pint push enter\n")

# ================================================

current_date = subprocess.getoutput(['date +"%Y-%m-%d"'])
logger.debug('system date ' + current_date)

# #################### main block #######################

mount_disk(OS_type, dev_disk)

all_snap = get_snap_list()
logger.info('<all_snap> value ' + str(all_snap))
logger.info('===== prepare lists ======')
all_snap_src = search_in_list(src_SYS, all_snap)
logger.debug('<all_snap_src> value ' + str(all_snap_src))
all_snap_dst = search_in_list(dest_SYS, all_snap)
logger.debug('<all_snap_dst> value ' + str(all_snap_dst))
previos_snap_list_src = create_last_snap_list(keyword_snap, pool_list, all_snap_src, 0)
logger.info('<previos_snap_list_src> ' + str(previos_snap_list_src))
previos_snap_list_dst = create_last_snap_list(keyword_snap, pool_list, all_snap_dst, 0)
logger.info('<previos_snap_list_dst> ' + str(previos_snap_list_dst))

# ############ checking pools on src
# noinspection PyRedeclaration
send_incremental_snap = create_pool_list_flag(pool_list, all_snap_src)
logger.info(' <send_incremental_snap>' + str(send_incremental_snap))
stop_point = input("stop_pint push enter delete after check\n")


# check snapshots on disk and PC
if len(previos_snap_list_src) != len(previos_snap_list_dst):
    logger.error('number of snapshots different on disk and PC')
    exit(201)

if dest_SYS == 'backup':
    logger.info('===== direction: ' + OS_type + '--->' + 'usb disk')

    # check snapshots on disk and PFC
    for i in range(len(previos_snap_list_src)):
        if previos_snap_list_src[i].replace(src_SYS, '') != previos_snap_list_dst[i].replace(dest_SYS, ''):
            logger.error('previous snaps on disk and PC different')
            exit(201)

    create_new_snap(root_pool, pool_list, current_date)
    all_snap = get_snap_list()
    logger.debug('<all_snap> value ' + str(all_snap))
    all_snap = search_in_list(root_pool, all_snap)
    logger.debug('<all_snap> value ' + str(all_snap))
    new_snap_list = create_last_snap_list(keyword_snap, pool_list, all_snap, 0)
    logger.info('<new_snap_list> ' + str(new_snap_list))

elif dest_SYS == root_pool:
    logger.info('===== direction: ' + 'usb disk' + '--->' + OS_type)

    # check snapshots on disk and PC
    for i in range(len(previos_snap_list_src)):
        if previos_snap_list_src[i].replace(src_SYS, '') == previos_snap_list_dst[i].replace(dest_SYS, ''):
            logger.info('previous snaps on disk and PC identical - nothing to do')
            umount_disk(dev_disk)
            exit(0)

    new_snap_list = previos_snap_list_src
    logger.debug('<new_snap_list> ' + str(new_snap_list))
    # searching  previos_snap_list_dst on USB
    previos_snap_list_src = []
    for searching_snap in previos_snap_list_dst:
        previos_snap_list_src.append(searching_snap.replace(dest_SYS, src_SYS))

    for searching_snap in previos_snap_list_src:
        if searching_snap in all_snap_src:
            # everything OK
            pass

        else:
            logger.error('last snaps on OS not found on USB, exit')
            umount_disk(dev_disk)
            exit(201)

    logger.debug('<previos_snap_list_src> ' + str(previos_snap_list_src))
    stop_point = input("stop_pint push enter\n")

logger.info('===== send snap  ======')
send_snap(dest_SYS, pool_list, new_snap_list, previos_snap_list_src, send_incremental_snap)

umount_disk(dev_disk)
logger.info("----------- END ------------")
