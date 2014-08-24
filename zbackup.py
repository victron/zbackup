#!/usr/bin/python3
# $Id$
# $Commit$
# $Date$


# NOTE: script need to call with root privileges or via "sudo"

# TODO : add "exit code" check after every system call 
# TODO : exceptions 


import subprocess
import logging
import argparse

############## constant values #################
disk_pool = "backup"

################# command line options ###########################
help_info = 'snapshots sending direction to usb or os'
parser = argparse.ArgumentParser(description='Arguments from command line')
parser.add_argument('direction', action='store', type=str, help=help_info, choices=['usb','os' ])
arg = parser.parse_args()



##################### logging block ##################
formatter = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.DEBUG,
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
  dev_disk = '/dev/disk/by-partuuid/09353f9f-c554-11e1-8897-5c260a0e9ee6'
  root_pool = "rpool"
elif OS_type == 'FreeBSD':
  logger.info( "OS is " + OS_type )
  dev_disk = '/dev/gptid/09353f9f-c554-11e1-8897-5c260a0e9ee6'
  root_pool = "zroot-n"
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
pool_list = ['/test@', '/home@', '/home/vic@']
logger.info('data sets list to work '+ str(pool_list))
keyword_snap = "@2014-"
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


def find_later_snap(list_snap,last_or_previous):
# return the latest snapshot
  list_snap = search_in_list(keyword_snap,list_snap)
  list_snap.sort(reverse=True)
  return list_snap[last_or_previous]

def create_last_snap_list(pool_list,snap_list,last_or_previous):
# create list of last snapshots, needed to process
  latest_snap = []
  for i in pool_list:
    latest_snap.append(find_later_snap(search_in_list(i, snap_list),last_or_previous))
  return latest_snap

def create_new_snap(root_pool, pool_list):
# create new snapshots
  stop_point = input("stop_pint push enter\n")
  for i in pool_list:
    logger.info('call to create snapshot '+ root_pool+i+current_date)
    subprocess.call(['zfs','snapshot', root_pool+i+current_date])
    logger.info('call to create snapshot code='+ "TODO")

def send_snap(recv_root_pool, pool_list, new_pool_list, old_pool_list):
  stop_point = input("stop_pint push enter\n")
  for i in range(0, len(pool_list)):
    logger.info('start sending   snap : '+ old_pool_list[i] + ' inctrement ' + new_pool_list[i])
    logger.info('start recieving snap : '+ recv_root_pool+pool_list[i][:-1])
    p1 = subprocess.Popen(['zfs','send','-v','-i', old_pool_list[i], new_pool_list[i]], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['zfs','receive','-v','-F', recv_root_pool+pool_list[i][:-1]], stdin=p1.stdout, stdout=subprocess.PIPE)
    output = p2.communicate()[0]
    logger.info('transfer snapshots code='+ 'TODO')
    

##################### main block #######################



## mount disk
if OS_type == 'FreeBSD':
	logger.debug('start  fusefs')
	subprocess.call(['/usr/local/etc/rc.d/fusefs', 'onestart'])

logger.info('mounting as truecrypt disk '+ dev_disk)
subprocess.call(['truecrypt', '--filesystem=none', '--slot=1', dev_disk])
logger.info('importing pool.... backup ')
subprocess.call(['zpool', 'import', 'backup'])

#### send from linux or BSD

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
            exit(0)
    
    new_snap_list = previos_snap_list_src
    logger.debug('<new_snap_list> ' + str(new_snap_list))
    previos_snap_list_src = create_last_snap_list(pool_list, all_snap_src,1)
    logger.debug('<previos_snap_list_src> ' + str(previos_snap_list_src))
    
    for i in range(len(previos_snap_list_src)):
        if previos_snap_list_src[i].replace(src_SYS,'') != previos_snap_list_dst[i].replace(dest_SYS,''):
            logger.error('previous-1 snaps on disk and PC different')
            exit(201)

logger.info('===== send snap  ======')
send_snap(dest_SYS,pool_list,new_snap_list,previos_snap_list_src)

## umount disk
logger.info('exporting pool.... backup ')
subprocess.call(['zpool', 'export', 'backup'])
logger.info('Umounting as truecrypt disk '+ dev_disk)
subprocess.call(['truecrypt', '-d', dev_disk])

logger.info( "----------- END ------------" )
