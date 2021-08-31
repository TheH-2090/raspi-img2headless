#! /usr/bin/python3

import subprocess
from sys import argv
from os import getcwd, getuid, path

def make_selection(options, message):
    options_dict = {}
    options_list = []
    output = f'{message}\n'
    for pos, option in enumerate(options):
        options_dict[pos] = option
        options_list.append(pos)
        output += (f'[{str(pos)}]\t{option}\n')
    while True:
        error_occured = False
        print(output)
        selection = input(messages['selection'])
        if selection.lower() == 'c':
            print(messages['user_cancelation'])
            quit()
        else:
            try:
                selection = int(selection)
                if selection in options_list:
                    return options_dict[selection]
                else:
                    error_occured = True
            except ValueError:
                error_occured = True
        if error_occured:
            print(messages['input_error'])

def get_drives():
    command = subprocess.run('lsblk -d -o NAME', stderr=subprocess.PIPE, stdout = subprocess.PIPE, stdin = subprocess.PIPE, shell=True)
    output = command.stdout.decode().split('\n')[:-1]
    drives = output[1:]
    return drives

def select_drive():
    drives = get_drives()
    selected_drive = make_selection(drives, messages['selected_drive'])
    return selected_drive

def confirm(message):
    options = ['no', 'yes']
    confirmation = make_selection(options, message)
    return confirmation == 'yes'

def enter_value(option):
    while True:
        value = input(f'Please enter the {option}: ')
        if confirm(f'\nIs the entered {option} [{value}] correct?'):
            return value
        else:
            print(f'{option} was not confirmed.')

def show_settings(settings):
    print(messages['show_settings'])
    max_tabs = (max(len(key) for key in settings.keys())+7) // 8
    for key, value in settings.items():
        print(key, (max_tabs - (len(key)-7) // 8) * '\t', value)

def change_settings(settings, change):
    if change['drive']:
        settings['drive'] = select_drive()
        change['drive'] = False
    if change['ssh_activated']:
        settings['ssh_activated'] = confirm(messages['ssh_activated'])
        change['ssh_activated'] = False
    if change['wifi_activated']:
        settings['wifi_activated'] = confirm(messages['wifi_activated'])
        change['wifi_activated'] = False
    if settings['wifi_activated']:
        if change['wifi_country']:
            settings['wifi_country'] = enter_value(messages['wifi_country'])
            change['wifi_country'] = False
        if change['wifi_ssid']:
            settings['wifi_ssid'] = enter_value(messages['wifi_ssid'])
            change['wifi_ssid'] = False
        if change['wifi_password']:
            settings['wifi_password'] = enter_value(messages['wifi_password'])
            change['wifi_password'] = False
    else:
        settings['wifi_country'] = settings['wifi_ssid'] = settings['wifi_password'] = None
        change['wifi_country'] = change['wifi_ssid'] = change['wifi_password'] = True
    if change['set_hostname']:
        settings['set_hostname'] = confirm(messages['set_hostname'])
        change['set_hostname'] = False
    if settings['set_hostname']:
        if change['new_hostname']:
            settings['new_hostname'] = enter_value(messages['new_hostname'])
            change['new_hostname'] = False
    else:
        settings['new_hostname'] = None
        change['new_hostname'] = True
    return settings, change

def execute_sequence(commands, message):
    print(messages[message])
    for command in commands:
        success = run(command)
        if not(success[0]):
            error_quit(message + '_error', '\n'.join(success[1]))
    print(messages[message + '_success'])
 
def run(command):
    task = subprocess.Popen(command , shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    task.wait()
    if task.returncode == 0:
        return [True, [line.decode('utf-8').strip('\n') for line in task.stdout.readlines()]]
    else:
        return [False, [line.decode('utf-8').strip('\n') for line in task.stdout.readlines()]]

def exception_handler(function, message):
    print(messages[message])
    try:
        function()
    except Exception as error:
        error_quit(message + '_error', error)
    print(messages[message + '_success'])

def error_quit(message, sys_error_msg):
    print(messages[message] + '\n' + sys_error_msg)
    quit(code=-1)

def read_file(filelocation):
    with open(filelocation, 'r') as file:
        content = file.readlines()
    return content

def write_file(filelocation, content):
    print(f'File {filelocation} written.')
    with open(filelocation, 'w') as file:
        for line in content:
            file.write(line + '\n')

def perform_cleanup():
    commands = []
    mount_return = run('mount')[1]
    for line in mount_return:
        if settings['drive'] + '1' in line:
            commands.insert(0, 'umount ' + line.split(' ')[2])
        if settings['drive'] + '2' in line:
            commands.append('umount ' + line.split(' ')[2])
        if 'loop9' in line:
            commands.append('umount ' + line.split(' ')[2])
    if path.exists('/tmp/trgt'):
        commands.append('rm -r /tmp/trgt')
    if path.exists('/tmp/src'):
        commands.append('rm -r /tmp/src')
    commands.append('losetup -D')
    execute_sequence(commands, 'perform_cleanup')

def create_partition_table(device):
    commands = [
        f'parted -s /dev/{device} mktable gpt',
        f'parted -s -a optimal /dev/{device} mkpart usbboot fat32 4.096 256M',
        f'parted -s -a optimal /dev/{device} mkpart usbroot ext4 256M "100%"',
    ]
    execute_sequence(commands, 'create_partition_table')

def format_partitions(device):
    commands = [
        f'mkfs.vfat -F 32 /dev/{device}1',
        f'mkfs.ext4 /dev/{device}2',
    ]
    execute_sequence(commands, 'format_partitions')

def prepare_target(device):
    commands = [
        f'mkdir /tmp/trgt',
        f'mount /dev/{device}2 /tmp/trgt',
        f'mkdir /tmp/trgt/boot',
        f'mount /dev/{device}1 /tmp/trgt/boot',
    ]
    execute_sequence(commands, 'prepare_target')

def mount_copy_image(image):
    commands = [
        f'losetup /dev/loop9 -P {image}',
        f'mkdir /tmp/src',
        f'mount /dev/loop9p2 /tmp/src',
        f'rsync -ax /tmp/src/ /tmp/trgt/',
        f'umount /tmp/src/',
        f'mount /dev/loop9p1 /tmp/src',
        f'rsync -ax /tmp/src/ /tmp/trgt/boot/',
        f'umount /tmp/src/',
        f'rm -r /tmp/src/',
    ]
    execute_sequence(commands, 'mount_copy_image')

def activate_ssh():
    write_file('/tmp/trgt/boot/ssh', [''])

def activate_wifi():
    content = [
    'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev',
    'update_config=1',
    'country=' + settings['wifi_country'],
    '',
    'network={',
    'scan_ssid=1',
    'ssid="' + settings['wifi_ssid']  + '"',
    'psk="' + settings['wifi_password'] + '"',
    '}'
    ]
    write_file('/tmp/trgt/boot/wpa_supplicant.conf', content)

def modify_hostname():
    old_hostname = read_file('/tmp/trgt/etc/hostname')[0].strip()
    new_hostname = settings['new_hostname']
    content = read_file('/tmp/trgt/etc/hosts')
    for linepos, line in enumerate(content):
        content[linepos] = line.replace(old_hostname, new_hostname)
    write_file('/tmp/trgt/etc/hosts', content)
    content = read_file('/tmp/trgt/etc/hostname')
    for linepos, line in enumerate(content):
        content[linepos] = line.replace(old_hostname, new_hostname)
    write_file('/tmp/trgt/etc/hostname', content)

def set_root():
    content = read_file('/tmp/trgt/boot/cmdline.txt')
    for linepos, line in enumerate(content):
        parameters = line.split(' ')
        for parameterpos, parameter in enumerate(parameters):
            if 'root=' in parameter:
                parameters[parameterpos] = 'root=PARTLABEL=usbroot'
            elif 'init=' in parameter:
                parameters[parameterpos] = ''

        content[linepos] = ' '.join(parameters)
    write_file('/tmp/trgt/boot/cmdline.txt', content)

def modify_fstab():
    content = read_file('/tmp/trgt/etc/fstab')
    for linepos, line in enumerate(content):
        line = line.strip('\n')
        parameters = line.split(' ')
        if ' / ' in line:
           parameters[0] = 'PARTLABEL=usbroot'
        elif '/boot' in line:
           parameters[0] = 'PARTLABEL=usbboot'
        content[linepos] = ' '.join(parameters)
    write_file('/tmp/trgt/etc/fstab', content)

messages = {
    'startup_error': 'There was an error in the execution.',
    'missing_privledges': 'Insufficient access rights.',
    'selected_drive': '\nSelect the drive you want to install the image to.',
    'selection': 'Enter number or [c]ancel: ',
    'user_cancelation': '\nScript stopped on user input.',
    'input_error': '\nInput could not be recognized.',
    'ssh_activated': '\nDo you want to enable ssh after installation?',
    'wifi_activated': '\nDo you want to enable wifi after installation?',
    'wifi_country': 'Country your wifi network',
    'wifi_ssid': 'SSID of your wifi network',
    'wifi_password': 'Password of your wifi network',
    'set_hostname': '\nDo you want to set the hostname for pi?',
    'new_hostname': 'Hostname of your Pi',
    'show_settings': '\nThe following settings have been made.',
    'finalize_settings': 'Please confirm the above settings.\nPLEASE NOTE: SELECTED DRIVE WILL BE DELETED AND ALL DATA WILL BE LOST.\nProceed? ',
    'change_value': 'Which value would you like to change?',
    'perform_cleanup': 'Initiating cleanup.',
    'perform_cleanup_success': 'Cleanup finished successful.',
    'perform_cleanup_error': 'There was an error during cleanup.',
    'create_partition_table': 'Creating partition table.',
    'create_partition_table_success': 'Partition table created.',
    'create_partition_table_error': 'There was an error creating the partition table.',
    'format_partitions': 'Formatting partitions.',
    'format_partitions_success': 'Partitions formatted.',
    'format_partitions_error': 'There was an error formatting the partitions.',
    'prepare_target': 'Preparing target for copy.',
    'prepare_target_success': 'Target successfully prepared.',
    'prepare_target_error': 'There was an error preparing the target.',
    'mount_copy_image': 'Mounting image and copying to target.',
    'mount_copy_image_success': 'Image copied to target.',
    'mount_copy_image_error': 'There was an error during copying.',
    'activate_ssh': 'Creating file that activates SSH on first boot.',
    'activate_ssh_success': 'File created. SSH will be activated on first boot.',
    'activate_ssh_error': 'There was an error while creating the file to activate SSH.',
    'activate_wifi': 'Creating wifi settings.',
    'activate_wifi_success': 'Wifi settings successfully created.',
    'activate_wifi': 'There was an error creating wifi settings.',
    'set_root': 'Adapting root in boot file cmdline.txt.',
    'set_root_success': 'Root set successful in boot file cmdline.txt.',
    'set_root': 'There was an error while adapting boot file cmdline.txt.',
    'modify_fstab': 'Modifying fstab.',
    'modify_fstab_success': 'Modification of fstab successful.',
    'modify_fstab_error': 'There was an error while modifying fstab.',
    'modify_hostname': 'Setting new hostname.',
    'modify_hostname_success': 'New hostname successfully set.',
    'modify_hostname_error': 'There was an error setting the hostname.',
}

if getuid() != 0:
    error_quit('missing_privledges', 'Please run with sudo or as root.')

settings = {}
try:
    app, image_path = argv
except Exception as error:
    error_quit('startup_error', 'Usage: rpi-img2usb.py <path-to-image>')

settings['source_path'] = f'{getcwd()}/{image_path}' if image_path[0] != '/' else image_path

change = {
    'drive': True,
    'ssh_activated': True,
    'wifi_activated': True,
    'wifi_country': True,
    'wifi_ssid': True,
    'wifi_password': True,
    'set_hostname': True,
    'new_hostname': True
    }

while True:
    settings, change = change_settings(settings, change)
    show_settings(settings)
    finalize_settings = confirm(messages['finalize_settings'])
    if finalize_settings:
        break
    change_options=[
        'drive',
        'ssh_activated',
        'wifi_activated',
        'wifi_country',
        'wifi_ssid',
        'wifi_password',
        'set_hostname',
        'new_hostname'
    ]
    change_value = make_selection(change_options, messages['change_value'])
    change[change_value] = True

perform_cleanup()

create_partition_table(settings['drive'])
format_partitions(settings['drive'])
prepare_target(settings['drive'])
mount_copy_image(settings['source_path'])

if settings['ssh_activated']:
    exception_handler(activate_ssh, 'activate_ssh')

if settings['wifi_activated']:
    exception_handler(activate_wifi, 'modify_hostname')

if settings['set_hostname']:
    exception_handler(modify_hostname, 'activate_wifi')

exception_handler(set_root, 'set_root')
exception_handler(modify_fstab, 'modify_fstab')

perform_cleanup()
