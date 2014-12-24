__author__ = 'vic'

import subprocess
import logging

logger = logging.getLogger(__name__)

def get_specific_snap_list(root_volume, volume):
    # get snapshots list
    all_snap = subprocess.getoutput('zfs list -H -o name -s name -t snapshot ' + root_volume + volume).split('\n')
    for i in range(len(all_snap)):
        all_snap[i] = all_snap[i].slit('\t')
    all_snap_dict = dict(all_snap)
    logger.debug('{0} dict = {1}'.format(root_volume + volume, all_snap_dict))
    return all_snap_dict


def max_dict_val(all_snap_dict, less_then=None):
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

def same_and_max_val_in_dicts(dict1,dict2):
    