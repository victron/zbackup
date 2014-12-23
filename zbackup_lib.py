# functions for zbackup.py
# $Id$
# $Date$

import subprocess
import logging

logger = logging.getLogger(__name__)


def get_snap_list():
    # get snapshots list
    all_snap = subprocess.getoutput(["zfs list -H -o name -s name -t snapshot"])
    all_snap = all_snap.split('\n')
    logger.debug('<all_snap> snap list, system return  ' + str(all_snap))
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


def create_pool_list_flag(pool_list, snap_list):
    # create list of pools which not present in snap_list
    pool_list_flag = []
    for i in pool_list:
        pool_list_flag.append(check_in_list(i, snap_list))
    return pool_list_flag


def send_snap(recv_root_pool, pool_list, new_pool_list, old_pool_list, send_incremental_snap):
    stop_point = input("stop_pint push enter\n")
    for i in range(0, len(pool_list)):
        if send_incremental_snap[i]:
            logger.info('start sending   snap : ' + old_pool_list[i] + ' increment ' + new_pool_list[i])
            logger.info('start receiving snap : ' + recv_root_pool + pool_list[i][:-1])
            p1 = subprocess.Popen(['zfs', 'send', '-v', '-i', old_pool_list[i], new_pool_list[i]],
                                  stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['zfs', 'receive', '-v', '-F', recv_root_pool + pool_list[i][:-1]], stdin=p1.stdout,
                                  stdout=subprocess.PIPE)
            output = p2.communicate()[0]
            exit_code = p2.returncode
            exit_on_error(exit_code)
            logger.info('transferred' + str(recv_root_pool + pool_list[i][:-1]) + 'return code=' + str(exit_code))
        else:
            logger.info('start sending   snap : full ' + new_pool_list[i])
            logger.info('start receiving snap : ' + recv_root_pool + pool_list[i][:-1])
            stop_point = input("stop_pint push enter delete after check\n")
            p1 = subprocess.Popen(['zfs', 'send', '-v', new_pool_list[i]], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['zfs', 'receive', '-v', '-F', recv_root_pool + pool_list[i][:-1]], stdin=p1.stdout,
                                  stdout=subprocess.PIPE)
            output = p2.communicate()[0]
            exit_code = p2.returncode
            exit_on_error(exit_code)
            logger.info('transferred' + str(recv_root_pool + pool_list[i][:-1]) + 'return code=' + str(exit_code))


def exit_on_error(exit_code):
    if exit_code != 0:
        logger.error('exit... system return code...' + str(exit_code))
        exit(exit_code)


def umount_disk(dev_disk):
    logger.info('exporting pool.... backup ')
    exit_code = subprocess.call(['zpool', 'export', 'backup'])
    exit_on_error(exit_code)
    logger.info('Umounting as truecrypt disk ' + dev_disk)
    exit_code = subprocess.call(['truecrypt', '-d', dev_disk])
    exit_on_error(exit_code)


def check_mounted():
    # check usb mounted or not
    all_zpools = subprocess.getoutput(["zpool list -H -o name"])
    all_zpools = all_zpools.split('\n')
    logger.debug('<all_Zpools> in system  %s', all_zpools)
    if 'backup' in all_zpools:
        logger.info('Zpool backup already  imported into system')
        return 1
    else:
        return 0


def mount_disk(os_type, dev_disk):
    if check_mounted() == 0:
        if os_type == 'FreeBSD':
            logger.debug('start  fusefs')
            exit_code = subprocess.call(['/usr/local/etc/rc.d/fusefs', 'onestart'])
            exit_on_error(exit_code)

        logger.info('mounting as truecrypt disk ' + dev_disk)
        try:
            exit_code = subprocess.call(['truecrypt', '--filesystem=none', '--slot=1', dev_disk])
            exit_on_error(exit_code)
        except:
            logger.critical('unknow exeption... ... exit')
            exit(25)

        logger.info('importing pool.... backup ')
        exit_code = subprocess.call(['zpool', 'import', 'backup'])
        exit_on_error(exit_code)

    elif check_mounted() == 1:
        logger.debug('Do not need to mount')
    else:
        exit_on_error(202)


def create_new_snap(root_pool, pool_list, current_date):
    # create new snapshots
    stop_point = input("stop_pint push enter\n")
    for i in pool_list:
        logger.info('call to create snapshot ' + root_pool + i + current_date)
        exit_code = subprocess.call(['zfs', 'snapshot', root_pool + i + current_date])
        exit_on_error(exit_code)
        logger.info(root_pool + i + current_date + '....created  ' + str(exit_code))


def create_last_snap_list(keyword_snap, pool_list, snap_list, last_or_previous):
    # create list of last snapshots, needed to process
    latest_snap = []
    for i in pool_list:
        # last_or_previous == 0 -> it means last snap
        # last_or_previous == 1 -> it means previous before last snap
        latest_snap.append(find_later_snap(keyword_snap, search_in_list(i, snap_list), last_or_previous))
    return latest_snap


def find_later_snap(keyword_snap, list_snap, last_or_previous):
    # return the latest snapshot
    list_snap = search_in_list(keyword_snap, list_snap)
    list_snap.sort(reverse=True)
    return list_snap[last_or_previous]

