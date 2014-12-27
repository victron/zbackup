# zbackup
=======
The aim of script to make quick transfer of ZFS snapshots from one host to another, using USB disk.
Also it could be used for simple backuping procedure.
#### In general case we has:
- host1
- host2
- USB drive
#### There are thee part of scripts:
1. zbackup.py - main and execution part of script
2. backup_lib.py - functions for zbackup.py
3. zbackup.ini - config file

## Config file (zbackup.ini) consists of:
* DEFAULT - block. 
According to logic of [configparser](https://docs.python.org/3.3/library/configparser.html) all options 
with it meaning represented here, will be available for program in another block. In this reason it the best location to put
 all general option. Here we put the names of [volumes](http://docs.oracle.com/cd/E18752_01/html/819-5461/ftyue.html), 
 witch we want to backup or transfer.
###### For example:
```
[DEFAULT]
volume = /test
         /tmp
         /home
```
* USB device - block
Put there specific options for your USB drive.
  - backup_pool - the name of your zfs [pool](https://docs.python.org/3.3/library/configparser.html). Script need to know on 
  what [dataset](http://docs.oracle.com/cd/E18752_01/html/819-5461/ftyue.html) it could transfer [snapshots](http://docs.oracle.com/cd/E18752_01/html/819-5461/ftyue.html). 
  Later it could be changed on [guid](https://docs.oracle.com/cd/E19120-01/open.solaris/817-2271/gfifk/index.html)
  - [partuuid](https://wiki.archlinux.org/index.php/persistent_block_device_naming) - the id of your partition on top of witch
  [truecrypt](http://en.wikipedia.org/wiki/TrueCrypt) is working.
  The easiest way to get label and partuuid mapping is to enter `ls -l /dev/disk/by-partuuid/` under linux
  ```
  ~ # ls -l /dev/disk/by-partuuid/
total 0
lrwxrwxrwx 1 root root 10 гру 27 19:07 03a37bc9-c554-11e1-8897-5c260a0e9ee6 -> ../../sdc3
lrwxrwxrwx 1 root root 10 гру 27 19:07 09353f9f-c554-11e1-8897-5c260a0e9ee6 -> ../../sdc4
lrwxrwxrwx 1 root root 10 гру 27 19:07 ebf6c572-c553-11e1-8897-5c260a0e9ee6 -> ../../sdc1
lrwxrwxrwx 1 root root 10 гру 27 19:07 fa11924d-c553-11e1-8897-5c260a0e9ee6 -> ../../sdc2
```

###### For example:
```
[USB device]
partuuid = 09353f9f-c554-11e1-8897-5c260a0e9ee6
backup_pool = backup
```

* host - block
Put there specific options for  any your hosts. Sript identify connected host by pool 
[guid](https://docs.oracle.com/cd/E19120-01/open.solaris/817-2271/gfifk/index.html)
It gets all zfs pools on system from `zpool get guid` output

## Arguments:
* [Positional arguments](https://docs.python.org/3.2/howto/argparse.html)
Only two options, witch specify snapshot sending direction
  - usb - send snapshots to USB drive
  Firstly it check for same snapshots on OS and USB drive.
  Then it creates newest snapshots on your system according to [config file](#Config file (zbackup.ini) consists of:)
  The names of new snapshots ends on output `date +"%Y-%m-%d`.
  If same snapshots not found in early step on OS and USB drive, created snapshot sensed fully on USB drive. 
  `zfs send -v <pool_src>/<volume>@<snapshot_newest> |zfs receive -v -F <pool_dst>/<volume> ` 
  If same snapshots were found on OS and USB drive, created snapshot sensed incrementally on USB drive.
  `zfs send -v -i <pool_src>/<volume>@<snapshot_previous> <pool_src>/<volume>@<snapshot_newest> | zfs receive -v -F <pool_dst>/<volume>`
  
  - os - send snapshots to host
  Firstly it check for same snapshots on OS and USB drive.
  If same snapshots present on OS and USB drive, and they both the newest, script simply ignore current volume. OS and drive both has actual data on volume,
  and continue work with another volumes.
  If same snapshots were found on OS and USB drive, but USB drive has as minimum one newest snapshot. This snapshot is 
  sent incrementally on OS.
  `zfs send -v -i <pool_src>/<volume>@<snapshot_previous> <pool_src>/<volume>@<snapshot_newest> | zfs receive -v -F <pool_dst>/<volume>`
  If same snapshots not found in early step on OS and USB drive, newest snapshot sensed fully on USB drive. 
  `zfs send -v <pool_src>/<volume>@<snapshot_newest> |zfs receive -v -F <pool_dst>/<volume> ` 
  
* [Optional arguments](https://docs.python.org/3.2/howto/argparse.html)
currently ony one option
  - '-v', '--verbosity - turn on debug and request user confirmation before every manipulation with disk

## [Truecrypt](http://en.wikipedia.org/wiki/TrueCrypt) integration
Currently there are no option to turn off truecrypt on USB disk.
Actually every times it check for device simply checking error code `ls /dev/disk/by-partuuid/<partuuid>` on Linux
 or `ls /dev/gptid/<partuuid>` on FreeBSD.
In failure case request user to connect USB disk.

After it, script attach truecrypt volume `truecrypt --filesystem=none --slot=1 /dev/gptid/<partuuid>`
And detach it at the end of work `truecrypt -d /dev/gptid/<partuuid>`

## Some useful notes about possible scenarios

```
#create key file
truecrypt --create-keyfile /etc/disk.key
#create container
truecrypt --volume-type=normal -c /dev/sda1

#map (attach) container
truecrypt --filesystem=none --slot=1 /dev/da0p4
truecrypt --filesystem=none --slot=1 /dev/gptid/09353f9f-c554-11e1-8897-5c260a0e9ee6
# find where is it attached
truecrypt -l


# format filesystem inside container
mkfs.ext4 /dev/mapper/truecrypt1
zpool create -O mountpoint=none backup

#import Zpool
zpool import backup

zfs send -i zroot-n/test@2014-06-29 zroot-n/test@2014-07-03 | zfs recv -F backup/test
zfs send -v -i zroot-n/home@2014-06-29 zroot-n/home@2014-07-03 | zfs recv -v -F backup/home
zfs send -v -i zroot-n/home/vic@2014-06-29 zroot-n/home/vic@2014-07-03 | zfs recv -v -F backup/home/vic

zpool export backup
truecrypt -l
truecrypt -d /dev/da0p4


################## on linux ######################
truecrypt --filesystem=none --slot=1 /dev/sdb4
zpool import backup
zfs send -v -i backup/test@2014-06-29 backup/test@2014-07-03 | zfs recv -v -F  rpool/test
zfs send -v -i backup/home@2014-06-29 backup/home@2014-07-03 | zfs recv -v -F  rpool/home
zfs send -v -i backup/home/vic@2014-06-29 backup/home/vic@2014-07-03 | zfs recv -v -F  rpool/home/vic

zpool export backup
truecrypt -l
##############################################
/usr/local/etc/rc.d/fusefs onestart
truecrypt --filesystem=none --slot=1 /dev/da0p4

 zfs snapshot -r zroot-n/home@`date "+%Y-%m-%d"`
 zfs snapshot -r zroot-n/test@`date "+%Y-%m-%d"`
 
 
 zfs send -v -i zroot-n/test@2014-07-03 zroot-n/test@2014-07-08 | zfs recv -v -F backup/test
 zfs send -v -R -i zroot-n/home@2014-07-03 zroot-n/home@2014-07-08 | zfs recv -v -F backup/home
 zpool export backup
 truecrypt -l
 
 #############################################################
 zfs list -H -t snapshot -o name -s name
 ```
