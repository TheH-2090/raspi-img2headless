#! /usr/bin/python3

import subprocess
from sys import argv
from os import getcwd, getuid, path
from getpass import getpass


class Imager(object):
    def __init__(self):
        self.init_messages()
        self.check_privileges()
        self.init_settings()
        self.selection_loop()
        self.execute_workflow()

    def execute_workflow(self):
        self.perform_cleanup()
        self.create_partition_table()
        self.format_partitions()
        self.prepare_target()
        self.mount_copy_image()
        if self.settings['Activate SSH']:
            self.exception_handler(self.activate_ssh, 5)
        if self.settings['Activate wifi']:
            self.exception_handler(self.activate_wifi, 6)
        self.exception_handler(self.set_root, 7)
        self.exception_handler(self.modify_fstab, 8)
        if self.settings['Modify hostname']:
            self.exception_handler(self.modify_hostname, 9)
        self.perform_cleanup()

    def check_privileges(self):
        if getuid() != 0:
                self.error_quit('Error: ' + self.error_messages[21])

    def init_messages(self):
        self.input_messages = {
            0: 'Select the drive you want to install the image to.',
            1: 'Enter number or [c]ancel: ',
            2: 'Do you want to enable SSH after installation?',
            3: 'Do you want to enable wifi after installation?',
            4: 'country for wifi settings',
            5: 'SSID of your wifi network',
            6: 'password of your wifi network',
            7: 'Do you want to set the hostname for your pi?',
            8: 'hostname of your pi',
            9: 'Please confirm the above settings.\nPLEASE NOTE: SELECTED DRIVE WILL BE DELETED AND ALL DATA WILL BE LOST.\nProceed? ',
            10: 'Which value would you like to change?',

        }
        self.status_messages = {
            0: 'Initiating cleanup.',
            1: 'Creating partition table.',
            2: 'Formatting partitions.',
            3: 'Preparing target for copy.',
            4: 'Mounting image and copying to target.',
            5: 'Creating file that activates SSH on first boot.',
            6: 'Creating wifi settings.',
            7: 'Adapting root in boot file cmdline.txt.',
            8: 'Modifying fstab.',
            9: 'Setting new hostname.',
            20: 'Script stopped on user input.',
            21: 'The following settings have been set.',
        }
        self.error_messages = {
            0: 'There was an error during cleanup.',
            1: 'There was an error creating the partition table.',
            2: 'There was an error formatting the partitions.',
            3: 'There was an error preparing the target.',
            4: 'There was an error during copying.',
            5: 'There was an error while creating the file to activate SSH.',
            6: 'There was an error creating wifi settings.',
            7: 'There was an error while adapting boot file cmdline.txt.',
            8: 'There was an error while modifying fstab.',
            9: 'There was an error setting the hostname.',
            20: 'Usage: raspi-img2headless.py <path-to-image>',
            21: 'Insufficient access rights.\nRun as root or by using sudo.',
            22: 'Input could not be recognized.',
        }
        self.confirmation_messages = {
            0: 'Cleanup finished successful.',
            1: 'Partition table created.',
            2: 'Partitions formatted.',
            3: 'Target successfully prepared.',
            4: 'Image copied to target.',
            5: 'File created. SSH will be activated on first boot.',
            6: 'Wifi settings successfully created.',
            7: 'Root set successful in boot file cmdline.txt.',
            8: 'Modification of fstab successful.',
            9: 'New hostname successfully set.',
        }

    def init_settings(self):
        self.settings = {
            'Image path': self.set_image_path(),
            'Target': 'not set',
            'Target boot': 'not set',
            'Target root': 'not set',
            'Activate SSH': False,
            'Activate wifi': False,
            'Wifi country': 'not set',
            'Wifi SSID': 'not set',
            'Wifi password (hidden)': 'not set',
            'Modify hostname': False,
            'Hostname entered': 'not set',
        }
        self.hidden_settings = {
            'Wifi password': 'not set',
        }
        self.to_change = {
            'Target': True,
            'SSH activation': True,
            'Wifi activation': True,
            'Wifi country': False,
            'Wifi SSID': False,
            'Wifi password': False,
            'Hostname modification': True,
            'Enter hostname': False,
        }

    def selection_loop(self):
        while True:
            self.change_settings()
            self.show_settings()
            finalize_settings = self.confirm(self.input_messages[9])
            if finalize_settings:
                break
            change_options = list(self.to_change.keys())
            to_change = self.make_selection(change_options, self.input_messages[10])
            if to_change in ['Wifi country', 'Wifi SSID', 'Wifi password'] and not(self.settings['Activate wifi']):
                self.to_change['Wifi activation'] = True
            elif to_change == 'Enter hostname' and not(self.settings['Modify hostname']):
                self.to_change['Hostname modification'] = True
            else:
                self.to_change[to_change] = True

    def set_image_path(self):
        try:
            app, image_path = argv
        except Exception as e:
            self.error_quit('\n'.join(e.args) + '\nError: ' + self.error_messages[20])
        image_path = f'{getcwd()}/{image_path}' if image_path[0] != '/' else image_path
        return image_path

    def make_selection(self, options, message):
        options_dict = {}
        options_list = []
        output = f'{message}'
        for pos, option in enumerate(options):
            options_dict[pos] = option
            options_list.append(pos)
            output += (f'\n[{str(pos)}]\t{option}')
        while True:
            error_occured = False
            print(output)
            selection = input(self.input_messages[1])
            print('')
            if selection.lower() == 'c':
                print('Info: ' + self.status_messages[20])
                quit()
            else:
                try:
                    selection = int(selection)
                    if selection in options_list:
                        return options_dict[selection]
                    else:
                        error_occured = True
                except ValueError as e:
                    error_occured = True
            if error_occured:
                print('Error: ' + '\n' + self.error_messages[22])

    def get_drives(self):
        command = subprocess.run('lsblk -d -o NAME', stderr=subprocess.PIPE, stdout = subprocess.PIPE, stdin = subprocess.PIPE, shell=True)
        output = command.stdout.decode().split('\n')[:-1]
        drives = output[1:]
        return drives

    def select_drive(self):
        drives = self.get_drives()
        selected_drive = self.make_selection(drives, self.input_messages[0])
        return selected_drive

    def enter_value(self, option):
        while True:
            while True:
                value = input(f'Please enter the {option}: ')
                if value:
                    print('')
                    break
                else:
                    print('No input made.')
                    print('')
            if self.confirm(f'Is the entered {option} [{value}] correct?'):
                return value
            else:
                print(f'The {option} was not confirmed.')

    def enter_confidential(self, option):
        while True:
            while True:
                value = getpass(f'Please enter the {option}: ')
                if value:
                    break
                else:
                    print('No input made.')
            while True:
                value2 = getpass(f'To confirm, please enter {option} again: ')
                if value:
                    break
                else:
                    print('No input made.')
            if value == value2:
                print('')
                return value
            else:
                print(f'The {option} did not match.')
                print('')

    def confirm(self, message):
        options = ['no', 'yes']
        confirmation = self.make_selection(options, message)
        return confirmation == 'yes'

    def error_quit(self, message):
        print(message)
        quit(code=-1)

    def change_settings(self):
        if self.to_change['Target']:
            self.settings['Target'] = self.select_drive()
            if self.settings['Target'][-1] in [str(digit) for digit in range(10)]:
                self.settings['Target boot'] = self.settings['Target'] + 'p1'
                self.settings['Target root'] = self.settings['Target'] + 'p2'
            else:
                self.settings['Target boot'] = self.settings['Target'] + '1'
                self.settings['Target root'] = self.settings['Target'] + '2'
            self.to_change['Target'] = False
        if self.to_change['SSH activation']:
            self.settings['Activate SSH'] = self.confirm(self.input_messages[2])
            self.to_change['SSH activation'] = False
        if self.to_change['Wifi activation']:
            self.settings['Activate wifi'] = self.confirm(self.input_messages[3])
            self.to_change['Wifi activation'] = False
            if self.settings['Activate wifi']:
                self.to_change['Wifi country'] = self.to_change['Wifi SSID'] = self.to_change['Wifi password'] = True
            else:
                self.settings['Wifi country'] = self.settings['Wifi SSID'] = self.settings['Wifi password (hidden)'] = self.hidden_settings['Wifi password'] = 'not set'
                self.to_change['Wifi country'] = self.to_change['Wifi SSID'] = self.to_change['Wifi password'] = False
        if self.to_change['Wifi country']:
            self.settings['Wifi country'] = self.enter_value(self.input_messages[4])
            self.to_change['Wifi country'] = False
        if self.to_change['Wifi SSID']:
            self.settings['Wifi SSID'] = self.enter_value(self.input_messages[5])
            self.to_change['Wifi SSID'] = False
        if self.to_change['Wifi password']:
            self.hidden_settings['Wifi password'] = self.enter_confidential(self.input_messages[6])
            self.settings['Wifi password (hidden)'] = len(self.hidden_settings['Wifi password']) * '*'
            self.to_change['Wifi password'] = False
        if self.to_change['Hostname modification']:
            self.settings['Modify hostname'] = self.confirm(self.input_messages[7])
            self.to_change['Hostname modification'] = False
            if self.settings['Modify hostname']:
                self.to_change['Enter hostname'] = True
            else:
                self.settings['Hostname entered'] = 'not set'
                self.to_change['Enter hostname'] = False
        if self.to_change['Enter hostname']:
            self.settings['Hostname entered'] = self.enter_value(self.input_messages[8])
            self.to_change['Enter hostname'] = False
        return

    def show_settings(self):
        print(self.status_messages[21])
        max_tabs = (max(len(key) for key in self.settings.keys())+7) // 8
        for key, value in self.settings.items():
            print(key, (max_tabs - (len(key)-7) // 8) * '\t', value)

    def execute_sequence(self, commands, message):
        print(self.status_messages[message])
        for command in commands:
            success = self.execute_single(command)
            if not(success[0]):
                self.error_quit('\n'.join(success[1]) + '\nError: ' + self.error_messages[message])
        print(self.confirmation_messages[message])

    def execute_single(self, command):
        task = subprocess.Popen(command , shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        task.wait()
        if task.returncode == 0:
            return [True, [line.decode('utf-8').strip('\n') for line in task.stdout.readlines()]]
        else:
            return [False, [line.decode('utf-8').strip('\n') for line in task.stdout.readlines()]]

    def exception_handler(self, function, message):
        print(self.status_messages[message])
        try:
            function()
        except Exception as e:
            self.error_quit('\n'.join(e.args) + '\nError: ' + self.error_messages[message])
        print(self.confirmation_messages[message])

    def read_file(self, filelocation):
        with open(filelocation, 'r') as file:
            content = file.readlines()
        return content

    def write_file(self, filelocation, content):
        print(f'File {filelocation} written.')
        with open(filelocation, 'w') as file:
            for line in content:
                file.write(line + '\n')

    def perform_cleanup(self):
        commands = []
        mount_return = self.execute_single('mount')[1]
        for line in mount_return:
            if self.settings['Target boot'] in line:
                commands.insert(0, 'umount ' + line.split(' ')[2])
            if self.settings['Target root'] in line:
                commands.append('umount ' + line.split(' ')[2])
            if 'loop9' in line:
                commands.append('umount ' + line.split(' ')[2])
        if path.exists('/tmp/trgt'):
            commands.append('rm -r /tmp/trgt')
        if path.exists('/tmp/src'):
            commands.append('rm -r /tmp/src')
        commands.append('losetup -D')
        self.execute_sequence(commands, 0)

    def create_partition_table(self):
        device = self.settings['Target']
        commands = [
            f'parted -s /dev/{device} mktable gpt',
            f'parted -s -a optimal /dev/{device} mkpart {device[:3]}boot fat32 4.096 256M',
            f'parted -s -a optimal /dev/{device} mkpart {device[:3]}root ext4 256M "100%"',
            'sleep 1',
        ]
        self.execute_sequence(commands, 1)

    def format_partitions(self):
        boot = self.settings['Target boot']
        root = self.settings['Target root']
        commands = [
            f'mkfs.vfat -F 32 /dev/{boot}',
            f'mkfs.ext4 /dev/{root}',
        ]
        self.execute_sequence(commands, 2)

    def prepare_target(self):
        boot = self.settings['Target boot']
        root = self.settings['Target root']
        commands = [
            'mkdir /tmp/trgt',
            f'mount /dev/{root} /tmp/trgt',
            'mkdir /tmp/trgt/boot',
            f'mount /dev/{boot} /tmp/trgt/boot',
        ]
        self.execute_sequence(commands, 3)

    def mount_copy_image(self):
        image = self.settings['Image path']
        commands = [
            f'losetup /dev/loop9 -P {image}',
            'mkdir /tmp/src',
            'mount /dev/loop9p2 /tmp/src',
            'rsync -ax /tmp/src/ /tmp/trgt/',
            'umount /tmp/src/',
            'mount /dev/loop9p1 /tmp/src',
            'rsync -ax /tmp/src/ /tmp/trgt/boot/',
            'umount /tmp/src/',
            'rm -r /tmp/src/',
        ]
        self.execute_sequence(commands, 4)

    def activate_ssh(self):
        self.write_file('/tmp/trgt/boot/ssh', [''])

    def activate_wifi(self):
        country = self.settings['Wifi country']
        ssid = self.settings['Wifi SSID']
        tmp_psk = self.hidden_settings['Wifi password']
        psk = self.execute_single(f'wpa_passphrase {ssid} {tmp_psk}')[1][-2].split('psk=')[-1]
        content = [
            'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev',
            'update_config=1',
            f'country={country}',
            '',
            'network={',
            '\tscan_ssid=1',
            f'\tssid="{ssid}"',
            f'\tpsk={psk}',
            '}'
        ]
        self.write_file('/tmp/trgt/boot/wpa_supplicant.conf', content)

    def modify_hostname(self):
        old_hostname = self.read_file('/tmp/trgt/etc/hostname')[0].strip('\n')
        new_hostname = self.settings['Hostname entered']
        file_list = ['hosts', 'hostname']
        for file in file_list:
            content = self.read_file(f'/tmp/trgt/etc/{file}')
            for linepos, line in enumerate(content):
                line = line.strip('\n')
                content[linepos] = line.replace(old_hostname, new_hostname)
            self.write_file(f'/tmp/trgt/etc/{file}', content)

    def set_root(self):
        device = self.settings['Target']
        content = self.read_file('/tmp/trgt/boot/cmdline.txt')
        for linepos, line in enumerate(content):

            parameters = line.split(' ')
            for parameterpos, parameter in enumerate(parameters):
                if 'root=' in parameter:
                    parameters[parameterpos] = f'root=PARTLABEL={device[:3]}root'
                elif 'init=' in parameter:
                    parameters[parameterpos] = ''
            content[linepos] = ' '.join(parameters)
        self.write_file('/tmp/trgt/boot/cmdline.txt', content)

    def modify_fstab(self):
        device = self.settings['Target']
        content = self.read_file('/tmp/trgt/etc/fstab')
        for linepos, line in enumerate(content):
            line = line.strip('\n')
            parameters = line.split(' ')
            if ' / ' in line:
                parameters[0] = f'PARTLABEL={device[:3]}root'
            elif '/boot' in line:
                parameters[0] = f'PARTLABEL={device[:3]}boot'
            content[linepos] = ' '.join(parameters)
        self.write_file('/tmp/trgt/etc/fstab', content)


if __name__ == '__main__':
    execute = Imager()
