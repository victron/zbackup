# functions for zbackup.py
# $Id$
# $Date$

import subprocess
import logging
from time import strftime, sleep

logger = logging.getLogger(__name__)


# noinspection PyAttributeOutsideInit
class Volume:
    def __init__(self, src_sys, dst_sys, debug):
        self.src_sys = src_sys
        self.dst_sys = dst_sys
        self.debug = debug
        self.current_date = strftime('%Y-%m-%d_%H:%M:%S')

    def generate_dicts(self, volume):
        # TODO : how it correct according __init__?
        self.volume = volume
        self.volume_dst_dict = get_specific_snap_list(self.dst_sys, volume)
        self.volume_src_dict = get_specific_snap_list(self.src_sys, volume)
        self.previous_same_snap = same_and_max_val_in_dicts(self.volume_src_dict, self.volume_dst_dict)
        self.newest_src_snap = max_dict_val(self.volume_src_dict)
        self.linux_workarount = False

    # @property
    def gather_attrs(self):
        attrs = []
        for key in self.__dict__:
            attrs.append('<{0}> = {1}'.format(key, getattr(self, key)))
        return ', '.join(attrs)

    def __str__(self):
        return '[{0}: {1}]'.format(self.__class__.__name__, self.gather_attrs())



class ToOS(Volume):
    def snap(self):
        if self.previous_same_snap == self.newest_src_snap:
            logger.debug('nothing send on OS {0} == {1}'.format(self.previous_same_snap, self.newest_src_snap))
        else:
            linux_workaround_mount(self.linux_workarount)
            send_snap(self.previous_same_snap[0], self.newest_src_snap[0], self.dst_sys + self.volume, self.debug)
            linux_workaround_umount(self.linux_workarount)


class ToUSB(Volume):
    def snap(self):
        create_new_snap(self.src_sys, self.volume, self.current_date, self.debug)
        new_volume_data = ToUSB(self.src_sys, self.dst_sys, self.debug)
        new_volume_data.generate_dicts(self.volume)
        # ToOS.snap(new_volume_data)
        send_snap(new_volume_data.previous_same_snap[0], new_volume_data.newest_src_snap[0],
                  new_volume_data.dst_sys + new_volume_data.volume, new_volume_data.debug)

class Pool:
    def __init__(self, pool, partuuid=None):
        self.pool = pool
        self.OS_type = subprocess.getoutput('uname')
        logger.info('OS => '.format(self.OS_type))
        if partuuid is not None:
            if self.OS_type == 'Linux':
                self.partuuid = '/dev/disk/by-partuuid/' + partuuid
            elif OS_type == 'FreeBSD':
                self.partuuid = '/dev/gptid/' + partuuid
            else:
                logger.error('UNknow OS =>'.format(self.OS_type))
                exit(202)


    def check_imported(self):
        all_zpools = subprocess.getoutput(["zpool list -H -o name"])
        all_zpools = all_zpools.split('\n')
        logger.debug('<all_Zpools>= {0}'.format(all_zpools))
        if self.pool in all_zpools:
            logger.info('Zpool backup already  imported into system')
            return True
        else:
            return False

    def check_partuuid(self):
        exit_code = subprocess.call(['ls', self.partuuid])
        if exit_code == 0:
            return True
        else:
            return False

    def mount(self,attempt, truecrypt=False):
        i = 0
        while i < attempt:
            if self.check_imported():
                logger.info('ZPOOL {0} already  imported into system'.format(self.pool))
                return True
            elif self.check_partuuid():
                # TODO : truecrypt, currently not supported under FreeBsd 10.1
                logger.info('importing pool.... backup ')
                exit_code = subprocess.call(['zpool', 'import', self.pool])
                exit_on_error(exit_code)
            elif not self.check_partuuid():
                i += 1
                logger.error('not found {0}'.format(self.partuuid))
                continue_or_exit('device {0} not found.\n'
                                 'Connect USB disk...\n'
                                 'atempt {1} continue or exit...'.format(self.partuuid, attempt - i), True)
        else:
            logger.critical('device {0} not found. Connect disk... Exit...'.format(self.partuuid))
            exit(10)

    def umount(self):
        logger.info('exporting pool.... backup ')
        exit_code = subprocess.call(['zpool', 'export', 'backup'])
        True if exit_code == 0 else exit_on_error(exit_code)

def exit_on_error(exit_code):
    if exit_code != 0:
        logger.critical('exit... system return code...' + str(exit_code))
        exit(exit_code)


def umount_disk(dev_disk, truecrypt=True):
    logger.info('exporting pool.... backup ')
    exit_code = subprocess.call(['zpool', 'export', 'backup'])
    exit_on_error(exit_code)
    if truecrypt:
        logger.info('Umounting as truecrypt disk ' + dev_disk)
        exit_code = subprocess.call(['truecrypt', '-d', dev_disk])
        exit_on_error(exit_code)





def check_mounted(dev_disk):
    # check usb mounted or not
    atempts_to_mount = 3
    for atempt in range(atempts_to_mount):
        all_zpools = subprocess.getoutput(["zpool list -H -o name"])
        # TODO: need to rebuild, in case not exported before shutdown
        all_zpools = all_zpools.split('\n')
        logger.debug('<all_Zpools> in system  %s', all_zpools)
        if 'backup' in all_zpools:
            logger.info('Zpool backup already  imported into system')
            return True
        else:
            exit_code = subprocess.call(['ls', dev_disk])
            if exit_code == 0:
                logger.info('USB found ... manual mounting')
                return False
            else:
                logger.error("not found " + dev_disk)
                continue_or_exit('device {0} not found.\n'
                                 'Connect USB disk...\n'
                                 'atempt {1} continue or exit...'.format(dev_disk, atempts_to_mount - atempt), True)
    else:
        print("device " + dev_disk + " not found. Connect disk...")
        # noinspection PyUnboundLocalVariable
        exit(exit_code)


def mount_disk(os_type, dev_disk, truecrypt=True):
    if not check_mounted(dev_disk):
        if truecrypt:
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

    elif check_mounted(dev_disk):
        logger.debug('Do not need to mount')
    else:
        exit_on_error(202)


def create_new_snap(root_pool, volume, current_date, debug_flag=False):
    # create new snapshots
    continue_or_exit('create snap {0} ?'.format(root_pool + volume + '@' + current_date), debug_flag)
    exit_code = subprocess.call(['zfs', 'snapshot', root_pool + volume + '@' + current_date])
    exit_on_error(exit_code)
    logger.info(root_pool + volume + '@' + current_date + '....created  ' + str(exit_code))


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


def max_dict_val(all_snap_dict: 'dictionary of snapshot', less_then=None) -> tuple:
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


def same_and_max_val_in_dicts(dict1, dict2) -> tuple:
    # find same and max val in both dicts
    # if one of args = None return None
    if dict1 is None or dict2 is None:
        logger.debug('dict {0} or {1} is None'.format(dict1, dict2))
        return None, None
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
        return None, None


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


def send_snap(src_snap1, src_snap2, dst_volume, debug_flag=False):
    # in case src_snap1 == None send full snapshot
    if src_snap1 is None:
        logger.debug('<src_snap2>'.format(src_snap2))
        p = subprocess.Popen(['zfs', 'send', '-v', '-n', src_snap2], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = p.communicate()[1]  # get only  stderror in [1]
        logger.info('ZFS test==> {0}'.format(output.decode()))
        exit_code = p.returncode
        exit_on_error(exit_code)
        continue_or_exit('send snap {0} to volume {1} ?'.format(src_snap2, dst_volume), debug_flag)
        p1 = subprocess.Popen(['zfs', 'send', '-v', src_snap2], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['zfs', 'receive', '-v', '-F', dst_volume], stdin=p1.stdout, stdout=subprocess.PIPE)
        output = p2.communicate()[0]
        exit_code = p2.returncode
        exit_on_error(exit_code)
    else:
        p = subprocess.Popen(['zfs', 'send', '-v', '-n', '-i', src_snap1, src_snap2], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        output = p.communicate()[1]  # get only  stderror in [1]
        logger.info('ZFS test==> {0}'.format(output.decode('utf-8')))
        exit_code = p.returncode
        exit_on_error(exit_code)
        continue_or_exit('send INCREMENTAL snaps {0} and {1} to volume {2} ?'.format(src_snap1, src_snap2, dst_volume),
                         debug_flag)
        p1 = subprocess.Popen(['zfs', 'send', '-v', '-i', src_snap1, src_snap2], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['zfs', 'receive', '-v', '-F', dst_volume], stdin=p1.stdout, stdout=subprocess.PIPE)
        output = p2.communicate()[0]  # need for below string, in oposite it return None
        exit_code = p2.returncode
        exit_on_error(exit_code)


def linux_workaround_umount(execute=False):
    if execute:
        exit_code = subprocess.call(['service', 'lightdm', 'stop'])
        logger.debug('stop lightd exit code = {0}'.format(exit_code))
        exit_on_error(exit_code)
        sleep(3)
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
        sleep(3)
        exit_code = subprocess.call(['service', 'lightdm', 'start'])
        logger.debug('start lightd exit code = {0}'.format(exit_code))
        exit_on_error(exit_code)
    else:
        pass

