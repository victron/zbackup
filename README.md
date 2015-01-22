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

## <a id="config_file"></a>Config file (zbackup.ini) consists of:
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
  - truecrypt - Does you secure your USB disk via truecrypt or not.
  - mount-point - place where to mount all USB volumes (early USB disk pools were imported with flag '-N'- don't mount)
  
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
* [Positional arguments](https://docs.python.org/3.2/howto/argparse.html#introducing-positional-arguments)
Only two options, witch specify snapshot sending direction
  - usb - send snapshots to USB drive
  Firstly it check for same snapshots on OS and USB drive.
  Then it creates newest snapshots on your system according to [config file](#config_file)
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
  
* [Optional arguments](https://docs.python.org/3.2/howto/argparse.html#introducing-optional-arguments)
currently ony one option
  - '-v', '--verbosity - turn on debug and request user confirmation before every manipulation with disk





