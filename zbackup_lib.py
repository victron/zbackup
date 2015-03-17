# functions for zbackup.py
# $Id$
# $Date$

import subprocess
import logging
from time import strftime, sleep, localtime

logger = logging.getLogger(__name__)


# noinspection PyAttributeOutsideInit
class Volume:
    def __init__(self, src_sys, dst_sys, debug):
        self.src_sys = src_sys
        self.dst_sys = dst_sys
        self.debug = debug
        self.current_date = strftime('%Y-%m-%d_%H:%M:%S')
        self.save_n_old_snapshots_src = 0
        self.save_n_old_snapshots_dst = 0

    def __str__(self):
        return '[{0}: {1}]'.format(self.__class__.__name__, self.gather_attrs())

    # @property
    def gather_attrs(self):
        attrs = []
        for key in self.__dict__:
            attrs.append('<{0}> = {1}'.format(key, getattr(self, key)))
        return ', '.join(attrs)

    def generate_dicts(self, volume):
        self.volume = volume
        self.volume_dst_dict = get_specific_snap_list(self.dst_sys, volume)
        self.volume_src_dict = get_specific_snap_list(self.src_sys, volume)
        self.previous_same_snap = same_and_max_val_in_dicts(self.volume_src_dict, self.volume_dst_dict)
        self.newest_src_snap = max_dict_val(self.volume_src_dict)
        self.linux_workarount = False
        self.snaps_to_leave_src, self.snaps_to_remove_src = create_last_n_snaps_list(self.volume_src_dict,
                                                                                     self.save_n_old_snapshots_src)
        self.snaps_to_leave_dst, self.snaps_to_remove_dst = create_last_n_snaps_list(self.volume_dst_dict,
                                                                                     self.save_n_old_snapshots_dst)


class ToOS(Volume):
    def send_snap(self, test_only: bool=False) -> tuple:
        if self.previous_same_snap == self.newest_src_snap:
            logger.debug('nothing send on OS {0} == {1}'.format(self.previous_same_snap, self.newest_src_snap))
            return self.previous_same_snap[0], strftime('%Y-%m-%d_%H:%M:%S',
                                                        localtime(int(self.previous_same_snap[1]))), None, None, None
        else:
            linux_workaround_umount(self.linux_workarount)
            if (self.previous_same_snap[0] is None) and isinstance(self.volume_dst_dict,dict) and self.volume_dst_dict:
                logger.info('need to delete snapshots {0}'.format(self.volume_dst_dict))
                continue_or_exit('confirm (or do it manually after', True)
                list(map(destroy_snaps, self.volume_dst_dict.keys()))
            result = send_snap(self.previous_same_snap[0], self.newest_src_snap[0], self.dst_sys + self.volume,
                               self.debug, test_only)
            linux_workaround_mount(self.linux_workarount)
            if self.previous_same_snap[1] is None:
                previous_same_snap_time = None
            else:
                previous_same_snap_time = strftime('%Y-%m-%d_%H:%M:%S', localtime(int(self.previous_same_snap[1])))
            return self.previous_same_snap[0], previous_same_snap_time, \
                   self.newest_src_snap[0], self.dst_sys + self.volume, result[2]


class ToUSB(Volume):
    def send_snap(self, test_only: bool=False) -> tuple:
        create_new_snap(self.src_sys, self.volume, self.current_date, self.debug)
        new_volume_data = ToUSB(self.src_sys, self.dst_sys, self.debug)
        new_volume_data.generate_dicts(self.volume)
        if (new_volume_data.previous_same_snap[0] is None) and (bool(new_volume_data.volume_dst_dict)):
            logger.warning('need to delete snapshots {0}'.format(new_volume_data.volume_dst_dict))
            continue_or_exit('confirm (or do it manually after', True)
            list(map(destroy_snaps, new_volume_data.volume_dst_dict.keys()))
        result = send_snap(new_volume_data.previous_same_snap[0], new_volume_data.newest_src_snap[0],
                           new_volume_data.dst_sys + new_volume_data.volume, new_volume_data.debug, test_only)
        # noinspection PyPep8
        return new_volume_data.previous_same_snap[0], \
               strftime('%Y-%m-%d_%H:%M:%S', localtime(int(new_volume_data.previous_same_snap[1]))), \
               new_volume_data.newest_src_snap[0], new_volume_data.dst_sys + new_volume_data.volume, result[2]


class Pool:
    def __init__(self, pool, partuuid=None):
        self.altroot = '/backup'
        self.pool = pool
        self.OS_type = subprocess.getoutput('uname')
        logger.info('OS => {0}'.format(self.OS_type))
        if partuuid is not None:
            if self.OS_type == 'Linux':
                self.partuuid = '/dev/disk/by-partuuid/' + partuuid
            elif self.OS_type == 'FreeBSD':
                self.partuuid = '/dev/gptid/' + partuuid
            else:
                logger.error('UNknow OS =>'.format(self.OS_type))
                exit(202)

    def check_imported(self):
        all_zpools = subprocess.getoutput(["zpool list -H -o name,health"])
        all_zpools = all_zpools.split()
        logger.debug('<all_Zpools>= {0}'.format(all_zpools))
        if self.pool in all_zpools:
            logger.info('Zpool backup already  imported into system')
            if all_zpools[all_zpools.index(self.pool) + 1] != 'ONLINE':
                logger.error('pool {0} not ONLINE, trying to export with \'-f\' flag...'.format(self.pool))
                # TODO: currently not implemented
                exit(101)
                exit_code = subprocess.call(['zpool', 'export', '-f', self.pool])
                return False if exit_code == 0 else exit_on_error(exit_code)
            return True
        else:
            return False

    def check_partuuid(self):
        exit_code = subprocess.call(['ls', self.partuuid])
        if exit_code == 0:
            return True
        else:
            return False

    def mount(self, attempt, truecrypt=False):
        i = 0
        while i < attempt:
            if self.check_imported():
                logger.info('ZPOOL {0} already  imported into system'.format(self.pool))
                return True
            elif self.check_partuuid():
                logger.info('importing pool.... backup ')
                exit_code = subprocess.call(['zpool', 'import', '-f', '-o', 'altroot=' + self.altroot, self.pool])
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
        # TODO : truecrypt, currently not supported under FreeBsd 10.1
        if truecrypt:
            try:
                exit_code = subprocess.call(['truecrypt', '--filesystem=none', '--slot=1', self.partuuid])
                exit_on_error(exit_code)
            except:
                logger.critical('unknow exeption... ... exit')
                exit(25)

    # noinspection PyUnusedLocal
    def umount(self, truecrypt=False):
        logger.info('exporting pool.... {0}'.format(self.pool))
        exit_code = subprocess.call(['zpool', 'export', self.pool])
        return True if exit_code == 0 else exit_on_error(exit_code)
        # TODO: truecrypt, not in use untill correction on FreeBSD 10


# if truecrypt:
# logger.info('Umounting as truecrypt disk ' + self.partuuid)
# exit_code = subprocess.call(['truecrypt', '-d', self.partuuid])
# exit_on_error(exit_code)


def exit_on_error(exit_code, error_info='<no error info>'):
    if exit_code != 0:
        logger.critical('ERROR => {0}'.format(error_info))
        logger.critical('exit... system return code...' + str(exit_code))
        exit(exit_code)


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


def create_last_n_snaps_list(input_dict, number):
    # create list of N snaps to leave on disk and list of snaps to remove
    if (input_dict is not None) and (len(input_dict) > number > 0):
        sorted_dict = sorted([(value, key) for key, value in input_dict.items()], reverse=True)
        snaps_to_leave = [(key, strftime('%Y-%m-%d_%H:%M:%S', localtime(int(value)))) for (value, key) in
                          sorted_dict[:len(input_dict) - number]]
        snaps_to_remove = [(key, strftime('%Y-%m-%d_%H:%M:%S', localtime(int(value)))) for (value, key) in
                           sorted_dict[number:]]
        logger.debug('<snaps_to_leave> = {0}\n <snaps_to_remove> = {1}'.format(snaps_to_leave, snaps_to_remove))
        return snaps_to_leave, snaps_to_remove
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


def send_snap(src_snap1, src_snap2, dst_volume, debug_flag=False, test_only=False):
    # in case src_snap1 == None send full snapshot
    if  src_snap2 is None:
        logger.debug('nothing to send')
        return src_snap1, None, None, None, None, None, None
    if src_snap1 is None:
        logger.debug('<src_snap2> = {0}'.format(src_snap2))
        p = subprocess.Popen(['zfs', 'send', '-v', '-n', src_snap2], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = p.communicate()[1]  # get only  stderror in [1]
        output = output.decode('utf-8')
        logger.info('ZFS test==> {0}'.format(output))
        exit_code = p.returncode
        exit_on_error(exit_code)
        if test_only:
            return tuple(map(lambda num: output.split()[num], [2, 4, 8]))
        """
        continue_or_exit('On LINUX it\'s not posible to use flag -F, if already some snapshots exists,\n'
                         'we need to delete all snapshots, before sending full stream\n'
                         ' {0} to {1}'.format(src_snap2, dst_volume), debug_flag)
        p = subprocess.Popen(['zfs', 'destroy', '-v',  dst_volume + '@%'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = p.communicate()[0]
        output = output.decode('utf-8')
        logger.info('ZFS ==> {0}'.format(output))
        exit_code = p.returncode
        exit_on_error(exit_code)
        """
        continue_or_exit('send snap {0} to volume {1} ?'.format(src_snap2, dst_volume), debug_flag)
        p1 = subprocess.Popen(['zfs', 'send', '-v', '-p', src_snap2], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p2 = subprocess.Popen(['zfs', 'receive', '-v', '-F', dst_volume], stdin=p1.stdout, stdout=subprocess.PIPE)
        output = p2.communicate()[0].decode()
        stderr_send = p1.communicate()[1].decode()
        exit_code = p2.returncode
        logger.debug('<zfs send> {}'.format(stderr_send))
        logger.debug('<zfs receive> {}'.format(output))
        exit_on_error(exit_code)
        # noinspection PyPep8
        return list(map(lambda num: stderr_send.split()[num], [2, 4, 8])) \
               + list(map(lambda num: output.split()[num], [6, 8, 11, 13]))

    else:
        p = subprocess.Popen(['zfs', 'send', '-v', '-n', '-i', src_snap1, src_snap2], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        output = p.communicate()[1]  # get only  stderror in [1]
        output = output.decode('utf-8')
        logger.info('ZFS test==> {0}'.format(output))
        exit_code = p.returncode
        exit_on_error(exit_code)
        if test_only:
            return tuple(map(lambda num: output.split()[num], [2, 4, 8]))
        continue_or_exit('send INCREMENTAL snaps {0} and {1} to volume {2} ?'.format(src_snap1, src_snap2, dst_volume),
                         debug_flag)
        p1 = subprocess.Popen(['zfs', 'send', '-v', '-p', '-i', src_snap1, src_snap2],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p2 = subprocess.Popen(['zfs', 'receive', '-v', '-F', dst_volume], stdin=p1.stdout, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        output = p2.communicate()
        stderr_send = p1.communicate()[1].decode()
        output_error = output[1].decode()
        output = output[0].decode()  # need for below string, in oposite it return None
        exit_code = p2.returncode
        logger.debug('<zfs send> {}'.format(stderr_send))
        logger.debug('<zfs receive> {}'.format(output))
        exit_on_error(exit_code, output + output_error)
        """
['@2015-01-13_14:03:29',
 'zroot-n/test@2015-01-15_20:41:48',
 '120K',
 'receiving',
 'incremental',
 'stream',
 'of',
 'zroot-n/test@2015-01-15_20:41:48',
 'into',
 'backup/test@2015-01-15_20:41:48',
 'received',
 '192KB',
 'stream',
 'in',
 '1',
 'seconds',
 '(192KB/sec)']
 return [previous snap, send snap, est. size, trans. snap, received, time, speed ]
"""
        # noinspection PyPep8
        #result = list(map(lambda num: stderr_send.split()[num], [2, 4, 8])) \
        #       + list(map(lambda num: output.split()[num], [6, 8, 11, 13]))
        #result = [stderr_send.split()[num] for num in [2, 4, 8]] + [output.split()[num] for num in [6, 8, 11, 13]]
        #return result
        return list(map(lambda num: stderr_send.split()[num], [2, 4, 8])) \
                + list(map(lambda num: output.split()[num], [6, 8, 11, 13]))


def linux_workaround_umount(execute=False):
    if execute and (subprocess.getoutput('service lightdm status') != 'lightdm stop/waiting'):
        exit_code = subprocess.call(['service', 'lightdm', 'stop'])
        logger.debug('stop lightd exit code = {0}'.format(exit_code))
        exit_on_error(exit_code)
        sleep(3)
#        exit_code = subprocess.call(['umount', '-l', '/tmp'])
#        logger.debug('umount /tmp exit code = {0}'.format(exit_code))
#        exit_on_error(exit_code)
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


def destroy_snaps(snap):
    logger.debug('snap to destroy {0}'.format(snap))
    exit_code = subprocess.call(['zfs', 'destroy', snap])
    exit_on_error(exit_code)
    logger.debug('deleted snapshot {0} exit..{1}'.format(snap, exit_code))




