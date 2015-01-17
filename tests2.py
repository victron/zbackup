__author__ = 'vic'

import unittest
from zbackup_lib2 import same_and_max_val_in_dicts


class KnownValues(unittest.TestCase):
    dict1 = {'zroot-n/test@2014-07-03': '1404374299',
             'zroot-n/test@2014-09-11': '1410436754',
             'zroot-n/test@2014-09-04': '1409827569',
             'zroot-n/test@2014-09-30': '1412108822',
             'zroot-n/test@2014-09-15': '1410790628',
             'zroot-n/test@upgraded-10.1': '1409597466',
             'zroot-n/test@2014-07-22': '1406031796',
             'zroot-n/test@2014-09-18': '1411061504',
             'zroot-n/test@2014-08-18': '1408382338',
             'zroot-n/test@2014-08-19': '1408448183',
             'zroot-n/test@2014-06-29': '1404046619'}

    dict2 = {'zroot-n/test@2014-07-03': '1404374299',
             'zroot-n/test@2014-09-11': '1410436754',
             'zroot-n/test@2014-09-04': '1409827569',
             'zroot-n/test@2014-09-30': '1412108822',
             'zroot-n/test@2014-09-15': '1410790628',
             'zroot-n/test@upgraded-10.1': '1409597466',
             'zroot-n/test@2014-07-22': '1406031796',
             'zroot-n/test@2014-09-18': '1411061504',
             'zroot-n/test@2014-08-18': '1408382338',
             'zroot-n/test@2014-08-19': '1408448183',
             'zroot-n/test@2014-06-29': '1404046619'}

    dict3 = {'zroot-n/test@2014-07-03': '1404374299',
             'zroot-n/test@2014-09-11': '1410436754',
             'zroot-n/test@2014-09-04': '1409827569',
             # 'zroot-n/test@2014-09-30': '1412108822',
             'zroot-n/test@2014-09-15': '1410790628',
             'zroot-n/test@upgraded-10.1': '1409597466',
             'zroot-n/test@2014-07-22': '1406031796',
             'zroot-n/test@2014-09-18': '1411061504',
             'zroot-n/test@2014-08-18': '1408382338',
             'zroot-n/test@2014-08-19': '1408448183',
             'zroot-n/test@2014-06-29': '1404046619'}

    dict4 = {'zroot-n/test@2014-07-03': '14043742990',
             'zroot-n/test@2014-09-11': '14104367540',
             'zroot-n/test@2014-09-04': '14098275690',
             # 'zroot-n/test@2014-09-30': '14121088220',
             'zroot-n/test@2014-09-15': '14107906280',
             'zroot-n/test@upgraded-10.1': '14095974660',
             'zroot-n/test@2014-07-22': '14060317960',
             'zroot-n/test@2014-09-18': '14110615040',
             'zroot-n/test@2014-08-18': '14083823380',
             'zroot-n/test@2014-08-19': '14084481830',
             'zroot-n/test@2014-06-29': '14040466190'}

    known_values = ((None, None, None),
                    (None, dict2, None),
                    (dict2, None, None),
                    (dict1, dict2, ('zroot-n/test@2014-09-30', '1412108822')),
                    (dict1, dict3, ('zroot-n/test@2014-09-18', '1411061504')),
                    (dict1, dict4, None))

    def test__same_and_max_val_in_dicts(self):
        for val1, val2, table_result in self.known_values:
            result = same_and_max_val_in_dicts(val1, val2)
            self.assertEqual(result, table_result)


if __name__ == '__main__':
    unittest.main()
