#!/usr/bin/python3
# $Id$
# $Date$

# NOTE: script need to call with root privileges or via "sudo"

# TODO: cannot receive incremental stream: most recent snapshot of backup/test does not match incremental source

import argparse
import configparser

from zbackup_lib import *
from tables import print_table_as_is, reform_table_fix_columns_sizes
# ############# constant values #################
config_file = 'zbackup.ini'
atempts_to_mount = 3


# ################ command line arguments ###########################
help_info = 'snapshots sending direction to \'usb\' or \'os\''
parser = argparse.ArgumentParser(description='Arguments from command line')
parser.add_argument('direction', action='store', type=str, choices=['usb', 'os'],
                    help=help_info)

arg_group_v_q = parser.add_mutually_exclusive_group()
arg_group_v_q.add_argument('-v', '--verbosity', action='count',
                           # it always set 2, if -v == 3, -vv == 4
                           default=2,
                           help='DEBUG on')
arg_group_v_q.add_argument("-q", "--quiet", action='store_true',
                           help='be quiet, only CRITICAL logs')

parser.add_argument('-s', '--save-last-snapshots', type=int, default=0,
                    help='Delete old snapshots from all devices, it override values in all BLOCKs .INI file')
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
truecrypt = config.getboolean('USB device', 'truecrypt', fallback=False)

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

usb_disk = Pool(pool, partuuid)  # init USB disk
usb_disk.altroot = config.get('USB device', 'mount-point', fallback='/backup')
usb_disk.mount(atempts_to_mount)

# ############## set direction according command line options ###########
if arg.direction == 'usb':
    # noinspection PyUnboundLocalVariable
    current_volume = ToUSB(root_pool, usb_disk.pool, debug_flag)
    current_volume.save_n_old_snapshots_dst = config.get('USB device', 'save-last-snapshots', fallback=0)
    # noinspection PyUnboundLocalVariable
    current_volume.save_n_old_snapshots_src = config.get(host_config, 'save-last-snapshots', fallback=0)
elif arg.direction == 'os':
    # noinspection PyUnboundLocalVariable
    current_volume = ToOS(usb_disk.pool, root_pool, debug_flag)
    current_volume.save_n_old_snapshots_src = config.get('USB device', 'save-last-snapshots', fallback=0)
    # noinspection PyUnboundLocalVariable
    current_volume.save_n_old_snapshots_dst = config.get(host_config, 'save-last-snapshots', fallback=0)
else:
    logger.error('wrong direction exit ... ')
    exit(201)

# noinspection PyUnboundLocalVariable
current_volume.save_n_old_snapshots_src = int(current_volume.save_n_old_snapshots_src)
current_volume.save_n_old_snapshots_dst = int(current_volume.save_n_old_snapshots_dst)

if arg.save_last_snapshots != 0:
    # noinspection PyUnboundLocalVariable
    current_volume.save_n_old_snapshots_src = arg.save_last_snapshots
    current_volume.save_n_old_snapshots_dst = arg.save_last_snapshots


# #################### main block #######################
# noinspection PyUnboundLocalVariable
work_table = [('previous snapshot', 'prev. snap. date', 'snapshot to send', 'recv. destination', 'size')]
result_table = [('previous snap', 'send snap', 'est. size', 'trans. snap', 'received', 'time', 'speed')]
delete_snaps_table = [('del. snapshot', 'create date')]
# create snaps and tables, in work_table - snaps which to send and where
umount_tmp = False
for volume in config.get(host_config, 'volume').split():
    # noinspection PyUnboundLocalVariable
    logger.debug('INIT==> {0}'.format(current_volume))
    current_volume.generate_dicts(volume)
    if volume == '/tmp' and usb_disk.OS_type == 'Linux':
#        current_volume.linux_workarount = True
        umount_tmp = True

    logger.debug('UPDATE==> {0}'.format(current_volume))
    work_table.append(current_volume.send_snap(True))
    # current_volume.delete_old_snapshots()
    if current_volume.snaps_to_remove_src is not None:
        delete_snaps_table += current_volume.snaps_to_remove_src
    if current_volume.snaps_to_remove_dst is not None:
        delete_snaps_table += current_volume.snaps_to_remove_dst

logger.debug('<work_table> {0}'.format(work_table))
print_table_as_is(reform_table_fix_columns_sizes(work_table, [18, 18, 18, 12, 5]))
continue_or_exit('start send snapshots', True)
linux_workaround_umount(umount_tmp)
result_table += list(map(lambda lst: send_snap(lst[0], lst[2], lst[3], debug_flag, False), work_table[1:]))
logger.debug('<result_table> {0}'.format(result_table))
logger.info('result work table below:')
print_table_as_is(reform_table_fix_columns_sizes(result_table, [12, 12, 5, 12, 7, 5, 12]))
if len(delete_snaps_table) > 1:
    logger.info('list to delete snap according config below:')
    logger.debug('<delete_snaps_table>'.format(delete_snaps_table))
    print_table_as_is(reform_table_fix_columns_sizes(delete_snaps_table, 25))
    continue_or_exit('delete snaps?', True)
    tuple(map(lambda lst: destroy_snaps(lst[0]), delete_snaps_table[1:]))
else:
    logger.info('no snaps to delete according config')

usb_disk.umount()
linux_workaround_mount(umount_tmp)
logger.info("----------- END ------------")
