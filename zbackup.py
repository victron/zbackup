#!/usr/bin/python3
# $Id$
# $Date$

# NOTE: script need to call with root privileges or via "sudo"

# TODO : exceptions 
# TODO : check mounted disk or not, partly DONE
# DONE : find last snap on os and find same on disk, and rebuild send function
# TODO : Global variables, partly DONE
# TODO : check if there is snap on disk, if not import it fully
# TODO : config File
# TODO : moduler


import subprocess
import logging
import argparse

############## constant values #################
disk_pool = "backup"
Linux_zpool = "rpool"
FreeBSD_zpool = "zroot-n"
dev_disk = "09353f9f-c554-11e1-8897-5c260a0e9ee6"
keyword_snap = "@2014-"
pool_list = ['/test@', '/home@', '/home/vic@']

############ flags
send_incremental_snap = []
################# command line options ###########################
help_info = 'snapshots sending direction to usb or os'
parser = argparse.ArgumentParser(description='Arguments from command line')
parser.add_argument('direction', action='store', type=str, help=help_info, choices=['usb','os' ])

arg_group_v_q = parser.add_mutually_exclusive_group()
arg_group_v_q.add_argument('-v', '--verbosity', action='count',
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
#elif args.verbosity <= 2:
#    logging_level = 20
    # logging.INFO
    # logging.WARNING = 30
elif arg.verbosity >= 3:
    logging_level = 10
    # logging.DEBUG
    # NOTSET = 0
else:
    logging_level = 20

##################### logging block ##################
formatter = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging_level,
#                    filename='zbackup.log',
                    format=formatter,
                    handlers=[logging.FileHandler("zbackup.log"),
                              logging.StreamHandler()])

logger = logging.getLogger(__name__)

logger.info( "----------- start working ------------" )

## OS type  
OS_type = subprocess.getoutput(["uname"])
if OS_type == 'Linux':
  logger.info( "OS is " + OS_type )
  dev_disk = '/dev/disk/by-partuuid/'+dev_disk
  root_pool = Linux_zpool
elif OS_type == 'FreeBSD':
  logger.info( "OS is " + OS_type )
  dev_disk = '/dev/gptid/'+dev_disk
  root_pool = FreeBSD_zpool
else:
  logger.error('UNknow OS '+ OS_type)
  exit(202)

# check USB connection  
atempts = 3
for i in range(atempts):
    exit_code = subprocess.call(['ls', dev_disk])
    if exit_code == 0:
        break
    logger.error( "not found " + dev_disk)
    print("device "+ dev_disk+ " not found. \nConnect USB disk...")
    null_val = input('and push enter... '+str(atempts-i))
if exit_code != 0:
    print("device "+ dev_disk+ " not found. Connect disk...")
    exit(exit_code)

############### set direction according command line options ###########
if arg.direction == 'usb':
    dest_SYS = disk_pool
    src_SYS = root_pool
elif arg.direction == 'os':
    dest_SYS = root_pool
    src_SYS = disk_pool
else :
    logger.error('wrong direction exit ... ')
    exit (201)

logger.debug('<dest_SYS> '+ dest_SYS)
logger.debug('<src_SYS> '+ src_SYS)
logger.info('data sets list to work '+ str(pool_list))
logger.debug('keyword for search MY snapshots '+ keyword_snap)

stop_point = input("stop_pint push enter\n")

#================================================

current_date = subprocess.getoutput(['date +"%Y-%m-%d"'])
logger.debug('system date '+ current_date)

def get_snap_list():
  # get snapshots list
  all_snap = subprocess.getoutput(["zfs list -H -o name -s name -t snapshot"])
  all_snap = all_snap.split('\n')
  logger.debug('<all_snap> snap list, system return  '+ str(all_snap))
  return all_snap

def search_in_list(search_str, search_list):
# search substring in all list, and return a list with findings
  out_list = []
  for i in search_list:
    if i.find(search_str) != -1:
      out_list.append(i)
  return out_list

def check_in_list(search_str, search_list):
    # return True if search_str present in search_list
    flag = False
    for i in search_list:
        if i.find(search_str) != -1:
            flag = True
    return flag

def create_pool_list_flag(pool_list,snap_list):
    # create list of pools which not present in snap_list
    pool_list_flag = []
    for i in pool_list:
        pool_list_flag.append(check_in_list(i, snap_list))
    return pool_list_flag


def find_later_snap(list_snap,last_or_previous):
# return the latest snapshot
  list_snap = search_in_list(keyword_snap,list_snap)
  list_snap.sort(reverse=True)
  return list_snap[last_or_previous]

def create_last_snap_list(pool_list,snap_list,last_or_previous):
# create list of last snapshots, needed to process
  latest_snap = []
  for i in pool_list:
      # last_or_previous == 0 -> it means last snap
      # last_or_previous == 1 -> it means previous before last snap
    latest_snap.append(find_later_snap(search_in_list(i, snap_list),last_or_previous))
  return latest_snap

def create_new_snap(root_pool, pool_list):
# create new snapshots
  stop_point = input("stop_pint push enter\n")
  for i in pool_list:
    logger.info('call to create snapshot '+ root_pool+i+current_date)
    exit_code = subprocess.call(['zfs','snapshot', root_pool+i+current_date])
    exit_on_error(exit_code)
    logger.info(root_pool+i+current_date + '....created  '+ str(exit_code))

def send_snap(recv_root_pool, pool_list, new_pool_list, old_pool_list, send_incremental_snap):
  stop_point = input("stop_pint push enter\n")
  for i in range(0, len(pool_list)):
      if send_incremental_snap[i] == True:
        logger.info('start sending   snap : '+ old_pool_list[i] + ' inctrement ' + new_pool_list[i])
        logger.info('start recieving snap : '+ recv_root_pool+pool_list[i][:-1])
        p1 = subprocess.Popen(['zfs','send','-v','-i', old_pool_list[i], new_pool_list[i]], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['zfs','receive','-v','-F', recv_root_pool+pool_list[i][:-1]], stdin=p1.stdout, stdout=subprocess.PIPE)
        output = p2.communicate()[0]
        exit_code = p2.returncode
        exit_on_error(exit_code)
        logger.info('transferred'+ str(recv_root_pool+pool_list[i][:-1]) + 'return code='+ str(exit_code))
      else:
        logger.info('start sending   snap : full ' + new_pool_list[i])
        logger.info('start recieving snap : '+ recv_root_pool+pool_list[i][:-1])
        stop_point = input("stop_pint push enter delete after check\n")
        p1 = subprocess.Popen(['zfs','send','-v', new_pool_list[i]], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['zfs','receive','-v','-F', recv_root_pool+pool_list[i][:-1]], stdin=p1.stdout, stdout=subprocess.PIPE)
        output = p2.communicate()[0]
        exit_code = p2.returncode
        exit_on_error(exit_code)
        logger.info('transferred'+ str(recv_root_pool+pool_list[i][:-1]) + 'return code='+ str(exit_code))

def exit_on_error (exit_code):
    if exit_code != 0:
        logger.error('exit... system return code...'+ str(exit_code))
        exit (exit_code)

def umount_disk():
    logger.info('exporting pool.... backup ')
    exit_code = subprocess.call(['zpool', 'export', 'backup'])
    exit_on_error(exit_code)
    logger.info('Umounting as truecrypt disk '+ dev_disk)
    exit_code = subprocess.call(['truecrypt', '-d', dev_disk])
    exit_on_error(exit_code)

def check_mounted():
  # check usb mounted or not
  all_Zpools = subprocess.getoutput(["zpool list -H -o name"])
  all_Zpools = all_Zpools.split('\n')
  logger.debug('<all_Zpools> in system  '+ str(all_Zpools))
  if 'backup' in all_Zpools:
      logger.info('Zpool backup already  imported into system')
      return 1
  else:
      return 0

def mount_disk():
    if check_mounted() == 0:
        if OS_type == 'FreeBSD':
            logger.debug('start  fusefs')
            exit_code = subprocess.call(['/usr/local/etc/rc.d/fusefs', 'onestart'])
            exit_on_error(exit_code)

        logger.info('mounting as truecrypt disk '+ dev_disk)
        try:
            exit_code = subprocess.call(['truecrypt', '--filesystem=none', '--slot=1', dev_disk])
            exit_on_error(exit_code)
        except:
            logger.error('unknow exeption... ... exit')
            exit (25)

        logger.info('importing pool.... backup ')
        exit_code = subprocess.call(['zpool', 'import', 'backup'])
        exit_on_error(exit_code)

    elif check_mounted() == 1:
        logger.debug('Do not need to mount')
    else:
        exit_on_error(202)

##################### main block #######################

mount_disk()

all_snap = get_snap_list()
logger.info('<all_snap> value ' + str(all_snap))
logger.info('===== prepare lists ======')
all_snap_src = search_in_list(src_SYS, all_snap)
logger.debug('<all_snap_src> value ' + str(all_snap_src))
all_snap_dst = search_in_list(dest_SYS, all_snap)
logger.debug('<all_snap_dst> value ' + str(all_snap_dst))
previos_snap_list_src = create_last_snap_list(pool_list, all_snap_src,0)
logger.info('<previos_snap_list_src> ' + str(previos_snap_list_src))
previos_snap_list_dst = create_last_snap_list(pool_list, all_snap_dst,0)
logger.info('<previos_snap_list_dst> ' + str(previos_snap_list_dst))

############# checking pools on src
send_incremental_snap = create_pool_list_flag(pool_list, all_snap_src)
logger.info(' <send_incremental_snap>'+ str(send_incremental_snap))
stop_point = input("stop_pint push enter delete after check\n")


# check snapshots on disk and PC
if len(previos_snap_list_src) != len(previos_snap_list_dst):
    logger.error('number of snapshots different on disk and PC')
    exit(201)

if dest_SYS == 'backup':
    logger.info('===== direction: '+ OS_type + '--->' + 'usb disk')

    # check snapshots on disk and PC
    for i in range(len(previos_snap_list_src)):
        if previos_snap_list_src[i].replace(src_SYS,'') != previos_snap_list_dst[i].replace(dest_SYS,''):
            logger.error('previous snaps on disk and PC different')
            exit(201)

    create_new_snap(root_pool, pool_list)
    all_snap = get_snap_list()
    logger.debug('<all_snap> value ' + str(all_snap))
    all_snap = search_in_list(root_pool, all_snap)
    logger.debug('<all_snap> value ' + str(all_snap))
    new_snap_list = create_last_snap_list(pool_list, all_snap,0)
    logger.info('<new_snap_list> ' + str(new_snap_list))

elif dest_SYS == root_pool:
    logger.info('===== direction: '+ 'usb disk' + '--->' + OS_type)

    # check snapshots on disk and PC
    for i in range(len(previos_snap_list_src)):
        if previos_snap_list_src[i].replace(src_SYS,'') == previos_snap_list_dst[i].replace(dest_SYS,''):
            logger.info('previous snaps on disk and PC identical - nothing to do')
            umount_disk()
            exit(0)

    new_snap_list = previos_snap_list_src
    logger.debug('<new_snap_list> ' + str(new_snap_list))
    # searching  previos_snap_list_dst on USB
    previos_snap_list_src = []
    for searching_snap in previos_snap_list_dst:
        previos_snap_list_src.append(searching_snap.replace(dest_SYS,src_SYS))

    for searching_snap in previos_snap_list_src:
        if searching_snap in all_snap_src:
            # everything OK
            pass

        else:
            logger.error('last snaps on OS not found on USB, exit')
            umount_disk()
            exit(201)

    logger.debug('<previos_snap_list_src> ' + str(previos_snap_list_src))
    stop_point = input("stop_pint push enter\n")

logger.info('===== send snap  ======')
send_snap(dest_SYS,pool_list,new_snap_list,previos_snap_list_src, send_incremental_snap)

umount_disk()
logger.info( "----------- END ------------" )
