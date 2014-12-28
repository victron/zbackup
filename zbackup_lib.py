# functions for zbackup.py
# $Id$
# $Date$

import subprocess
import logging

logger = logging.getLogger(__name__)


def exit_on_error(exit_code):
    if exit_code != 0:
        logger.critical('exit... system return code...' + str(exit_code))
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


def create_new_snap(root_pool, pool_list, current_date, debug_flag=False):
    # create new snapshots
    for i in pool_list:
        logger.debug('create snap {0}'.format(root_pool + i + '@' + current_date))
        continue_or_exit('create snap {0} ?'.format(root_pool + i + '@' + current_date), debug_flag)
        exit_code = subprocess.call(['zfs', 'snapshot', root_pool + i + '@' + current_date])
        exit_on_error(exit_code)
        logger.info(root_pool + i + '@' + current_date + '....created  ' + str(exit_code))


def get_specific_snap_list(root_volume, volume):
    # get snapshots dict for root_volume/volume
    all_snap = subprocess.getoutput('zfs get -d 1 -t snapshot -p -H -o name,value creation ' + root_volume + volume)
    if 'dataset does not exist' in all_snap or all_snap == '':
        return None
    all_snap = all_snap.split('\n')
    for i in range(len(all_snap)):
        all_snap[i] = all_snap[i].split('\t')
    all_snap_dict = dict(all_snap)
    logger.debug('snaps on {0} in dict = {1}'.format(root_volume + volume, all_snap_dict))
    return all_snap_dict


def max_dict_val(all_snap_dict, less_then=None):
    # find max value in dict
    max_val = None
    max_key = None
    for key, val in all_snap_dict.items():
        if less_then is None:
            if max_val is None or val > max_val:
                max_key = key
                max_val = val
        else:
            if max_val is None or less_then > val > max_val:
                max_key = key
                max_val = val
    return max_key, max_val


def same_and_max_val_in_dicts(dict1, dict2):
    # find same and max val in both dicts
    # if one of args = None return None
    if dict1 is None or dict2 is None:
        logger.debug('dict {0} or {1} is None'.format(dict1, dict2))
        return None
    sorted_dict1 = sorted([(value, key) for key, value in dict1.items()], reverse=True)
    sorted_dict2 = sorted([(value, key) for key, value in dict2.items()], reverse=True)
    i_dict1 = 0
    i_dict2 = 0
    while i_dict1 < len(sorted_dict1) and i_dict2 < len(sorted_dict2):
        if sorted_dict1[i_dict1][0] == sorted_dict2[i_dict2][0]:
            return sorted_dict1[i_dict1][1], sorted_dict1[i_dict1][0]
        elif sorted_dict1[i_dict1][0] > sorted_dict2[i_dict2][0]:
            i_dict1 += 1
        elif sorted_dict1[i_dict1][0] < sorted_dict2[i_dict2][0]:
            i_dict2 += 1
    else:
        return None


def query_yes_no(question, default='yes'):
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}

    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: {0}".format(default))

    while True:
        print(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            print("Please respond with 'yes' or 'no' ('y' or 'n').\n")


def continue_or_exit(question, debug=False):
    if debug:
        if not query_yes_no(question):
            logger.info('user interupt, exit... 101')
            exit(101)
    else:
        pass


def send_snap_full(src_snap, dst_volume, debug_flag=False):
    logger.info('start sending   FULL snap {0}'.format(src_snap))
    logger.info('start receiving FULL snap on volume {0}'.format(dst_volume))
    send_snap_test_full(src_snap, dst_volume)
    continue_or_exit('send snap {0} to volume {1} ?'.format(src_snap, dst_volume), debug_flag)
    p1 = subprocess.Popen(['zfs', 'send', '-v', src_snap], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['zfs', 'receive', '-v', '-F', dst_volume], stdin=p1.stdout, stdout=subprocess.PIPE)
    output = p2.communicate()[0]
    exit_code = p2.returncode
    exit_on_error(exit_code)


def send_snap_incremental(src_snap1, src_snap2, dst_volume, debug_flag=False):
    logger.info('start sending INCREMENTAL snaps {0} and {1}'.format(src_snap1, src_snap2))
    logger.info('start receiving INCREMENTAL snap on volume {0}'.format(dst_volume))
    send_snap_test_incremental(src_snap1, src_snap2, dst_volume)
    continue_or_exit('send INCREMENTAL snaps {0} and {1} to volume {2} ?'.format(src_snap1, src_snap2, dst_volume),
                     debug_flag)
    p1 = subprocess.Popen(['zfs', 'send', '-v', '-i', src_snap1, src_snap2], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['zfs', 'receive', '-v', '-F', dst_volume], stdin=p1.stdout, stdout=subprocess.PIPE)
    exit_code = p2.returncode
    exit_on_error(exit_code)


def send_snap_test_incremental(src_snap1, src_snap2, dst_volume):
    p = subprocess.Popen(['zfs', 'send', '-v', '-n', '-i', src_snap1, src_snap2], stdout=subprocess.PIPE)
    output = p.communicate()[0]  # get only stdoutput, stderror in [1]
    logger.info('ZFS test {0}'.format(output.decode('utf-8')))
    exit_code = p.returncode
    exit_on_error(exit_code)
    p1 = subprocess.Popen(['zfs', 'send', '-v', '-i', src_snap1, src_snap2], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['zfs', 'receive', '-v', '-F', '-n', dst_volume], stdin=p1.stdout, stdout=subprocess.PIPE)
    output = p2.communicate()[0]
    logger.info('ZFS test {0}'.format(output.decode('utf-8')))
    exit_code = p2.returncode
    exit_on_error(exit_code)


def send_snap_test_full(src_snap1, dst_volume):
    p = subprocess.Popen(['zfs', 'send', '-v', '-n', src_snap1], stdout=subprocess.PIPE)
    output = p.communicate()[0]  # get only stdoutput, stderror in [1]
    logger.info('ZFS test {0}'.format(output.decode()))
    exit_code = p.returncode
    exit_on_error(exit_code)
    p1 = subprocess.Popen(['zfs', 'send', '-v', '-i', src_snap1], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['zfs', 'receive', '-v', '-F', '-n', dst_volume], stdin=p1.stdout, stdout=subprocess.PIPE)
    output = p2.communicate()[0]
    logger.info('ZFS test {0}'.format(output.decode()))
    exit_code = p2.returncode
    exit_on_error(exit_code)


def linux_workaround_umount(execute=False):
    if execute:
        exit_code = subprocess.call(['service', 'lightdm', 'stop'])
        logger.debug('stop lightd exit code = {0}'.format(exit_code))
        exit_on_error(exit_code)
        exit_code = subprocess.call(['umount', '-l', '/tmp'])
        logger.debug('umount /tmp exit code = {0}'.format(exit_code))
        exit_on_error(exit_code)
    else:
        pass


def linux_workaround_mount(execute=False):
    if execute:
        exit_code = subprocess.call(['zfs', 'mount', '-O', 'rpool/tmp'])
        logger.debug('zfs mount -O  rpool/tmp exit code = {0}'.format(exit_code))
        exit_on_error(exit_code)
        exit_code = subprocess.call(['service', 'lightdm', 'start'])
        logger.debug('start lightd exit code = {0}'.format(exit_code))
        exit_on_error(exit_code)
    else:
        pass