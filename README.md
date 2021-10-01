# raspi-img2headless
## Description:
A Python script to copy an .img to a connected drive (microSD or usb) and support with the initial headless setup.

## Table of contents:
- [History](#history)
- [Main features](#main-features)
- [Installation](#installation)

## History:
Trying different operating systems on the Raspberry Pi leads to repetetive tasks just to get the basic system up and running.  
**raspi-img2headless can be ran directly from the sd-card and install a fresh downloaded image directly to an attached usb drive.**

Usually the following steps have to be carried out to install a new image:
- Writing image to sd-card
- Activating ssh and configuring wireless settings
- Setting hostname
- Multiple reboots
- Taking out the sd-card to rectify missing settings in case something was forgotten

Additionally, it is recommended to run the system from a usb drive for performance reasons, which includes further steps.


## Main features:
- Partitioning of selected drive
- Formatting boot and root partition
- Copying system from .img file to newly created partitions
- Making necessary changes to cmdline.txt on the new boot partition
- Adapting fstab on the new root partition
Optional:
- Activating SSH
- Add wifi settings
- Set hostname

## Installation:
### Prequisits
- Raspberry Pi with firmware that supports booting from usb
- Python3

### Usage:
Download the image file.  
Download raspi-img2headless.py.  
Make the file executable: `chmod +x raspi-img2headless.py`  
Run the script: `sudo raspi-img2headless.py path/to/imagefile.img`  
**_Note_: Elevated privledges are needed for partitioning, mounting, copying and modification of the necessary files.**

After the script has finished change the boot order using `raspi-config` and reboot.

## Future plans:
There are currently no future plans for the script.
