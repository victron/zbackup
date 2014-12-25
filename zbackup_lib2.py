__author__ = 'vic'

import subprocess
import logging

logger = logging.getLogger(__name__)

def get_specific_snap_list(root_volume, volume):
    # get snapshots dict for root_volume/volume
    all_snap = subprocess.getoutput('zfs get -d 1 -t snapshot -p -H -o name,value creation ' + root_volume + volume)
    if all_snap == '':
        return None
    all_snap = all_snap.split('\n')
    for i in range(len(all_snap)):
        all_snap[i] = all_snap[i].split('\t')
    all_snap_dict = dict(all_snap)
    logger.debug('{0} dict = {1}'.format(root_volume + volume, all_snap_dict))
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
    return (max_key, max_val)

def same_and_max_val_in_dicts(dict1,dict2):
    # find same and max val in both dicts
    sorted_dict1 = sorted([(value, key) for key, value in dict1.items()],reverse=True)
    sorted_dict2 = sorted([(value, key) for key, value in dict2.items()],reverse=True)
    i_dict1 = 0
    i_dict2 = 0
    while i_dict1 < len(sorted_dict1) and i_dict2 < len(sorted_dict2):
        if sorted_dict1[i_dict1][0] == sorted_dict2[i_dict2][0]:
            return (sorted_dict1[i_dict1][1], sorted_dict1[i_dict1][0])
        elif sorted_dict1[i_dict1][0] > sorted_dict2[i_dict2][0]:
            i_dict1 += 1
        elif sorted_dict1[i_dict1][0] < sorted_dict2[i_dict2][0]:
            i_dict2 += 1
    else:
        return None


    