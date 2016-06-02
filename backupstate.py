#!/usr/bin/env python
import ConfigParser
import traceback
import sys
import os
import subprocess
import argparse
import plistlib
import json
import re

class BackupState:

    def __init__(self):
        self.defaults = {
            'config_file': 'config.ini',
            'drive_name': 'My Passport',
            'remove_tmp': True,
            'output_json': True,
            'output_file': 'device_data.json'
        }

        self.arg_parser = argparse.ArgumentParser()
        self.arg_parser.add_argument(
            "-c", "--config_file", help="Location of the configuration file")
        self.arg_parser.add_argument(
            "-m", "--method_to_use", help="Which method to use?", default='drive_data')
        self.arg_parser.add_argument(
            "-o", "--output_file", help="Name your output file?", default=self.defaults['output_file'])
        self.arg_parser.add_argument(
            "-q", "--quiet", help="Prevents output to the screen", action="store_true", default=False)

        self.args = self.arg_parser.parse_args()

        # Collect any arguments passed to argparser
        self.quiet = self.args.quiet
        self.method_to_use = self.args.method_to_use
        self.arg_output_file = self.args.output_file

        # Set the default for the configuration file
        if self.args.config_file:
            self.config_file = self.args.config_file
        else:
            self.config_file = self.defaults['config_file']

        try:
            config = ConfigParser.ConfigParser()
            if os.path.exists('config.ini'):
                config.read("config.ini")
                self.config_data = {}
                self.config_data['drive_name'] = config.get('GeneralSettings', 'DriveName')
                self.config_data['remove_tmp'] = config.get('GeneralSettings', 'RemoveTmp')
                self.config_data['output_json'] = config.get('GeneralSettings', 'OutputJson')
                self.config_data['output_file'] = config.get('GeneralSettings', 'OutputFile')
            else:
                raise Exception('No config.ini file was found')
        except:
            self.sendToTerminal('Could not load config.ini')
            exit()
        finally:
            if self.config_data:
                if self.config_data['drive_name']:
                    self.backup_name = self.config_data['drive_name']
                else:
                    self.backup_name = self.defaults['drive_name']

                if self.config_data['remove_tmp']:
                    self.remove_tmp = self.config_data['remove_tmp']
                else:
                    self.remove_tmp = self.defaults['remove_tmp']

                if self.config_data['output_json']:
                    self.output_json = self.config_data['output_json']
                else:
                    self.output_json = self.defaults['output_json']

                if self.config_data['output_json']:
                    self.output_file = self.config_data['output_file']
                else:
                    self.output_file = self.defaults['output_file']
            else:
                self.backup_name = self.defaults['drive_name']
                self.remove_tmp = self.defaults['remove_tmp']
                self.output_json = self.defaults['output_json']

            self.backup_device = None
            self.diskutil_plist = 'diskutil.plist'
            self.tmutil_output_file_name = 'tmutil_status.output'
            self.tmutil_running_file_name = 'tmutil_status_running.output'
            self.tmutil_percentage_file_name = 'tmutil_status_percentage.output'

    def main(self):
        if self.method_to_use:
            if self.method_to_use == 'drive_data':
                self.generateDriveData()
            elif self.method_to_use == 'read_tmutil':
                self.readTmUtilStatus()
            else:
                self.sendToTerminal('Command not configured')
        else:
            self.sendToTerminal('No command specified')

    def generateDriveData(self):
        diskutil_data = self.getDiskUtilPlist(file_to_read=self.diskutil_plist, remove_tmp=self.remove_tmp)
        self.backup_device = { 'volume_name': None, 'device_identifier': None, 'mount_point': None, 'mounted': None, 'backup_in_progress': False, 'backup_raw_percentage': None }
        for disk in diskutil_data['AllDisksAndPartitions']:
            if 'VolumeName' in disk and disk['VolumeName'] == self.backup_name:
                volume_name = disk['VolumeName']
                self.backup_device['volume_name'] = volume_name
                self.device_identifier = disk['DeviceIdentifier']
                self.backup_device['device_identifier'] = self.device_identifier

                if 'MountPoint' in disk:
                    mount_point = disk['MountPoint']
                    mounted = True

                    if self.getDataFromTmUtilFile(file_to_output_to=self.tmutil_output_file_name, remove_tmp=False):
                        backup_in_progress = self.getDataFromTmUtilFile(file_to_output_to=self.tmutil_running_file_name, file_to_read=self.tmutil_output_file_name, key='Running', pattern='[0-9]', remove_tmp=self.remove_tmp)
                        if backup_in_progress == '1':
                            backup_in_progress = True
                        else:
                            backup_in_progress = False

                        backup_raw_percentage = self.getDataFromTmUtilFile(file_to_output_to=self.tmutil_percentage_file_name, file_to_read=self.tmutil_output_file_name, key='_raw_Percent', pattern='[0-9].[0-9]', remove_tmp=self.remove_tmp)
                        if not backup_raw_percentage:
                            backup_raw_percentage = None
                    else:
                        backup_in_progress = False
                        backup_raw_percentage = None

                    if self.remove_tmp:
                        os.unlink(self.tmutil_output_file_name)
                else:
                    backup_raw_percentage = None
                    backup_in_progress = False
                    mounted = False
                    mount_point = None

                self.backup_device['mount_point'] = mount_point
                self.backup_device['mounted'] = mounted
                self.backup_device['backup_in_progress'] = backup_in_progress
                self.backup_device['backup_raw_percentage'] = backup_raw_percentage

        if self.backup_device['volume_name']:
            if self.output_json:
                json_data = json.dumps(self.backup_device, indent=4)
                if self.quiet:
                    with open('device_data.json', 'w') as json_file:
                        json_file.write(json_data)
                else:
                    self.sendToTerminal(json_data)
            else:
                self.sendToTerminal(self.backup_device)
        else:
            self.sendToTerminal('No backup device named "' + self.backup_name + '" was found')

    def readTmUtilStatus(self):
        with open('tmutil.json', 'r') as tmutil_file:
            tmutil_data = tmutil_file.read()

        tmutil_data = tmutil_data.replace('Backup session status:\n', '')
        tmutil_data = tmutil_data.replace('};', '},')
        tmutil_data = tmutil_data.replace('    ', '')
        tmutil_data = re.sub(r'\s[=]\s', ':', tmutil_data)

        with open('tmutil.tmp.json', 'w') as tmp_file:
            tmp_file.write(tmutil_data)

        new_tmutil_data = ''
        with open('tmutil.tmp.json', 'r') as tmp_file_re:
            for line in tmp_file_re:
                line = line.strip()
                if ':' in line:
                    parts = line.split(':')
                    if '"' not in parts[1]:
                        value = type(parts[1])
                        if type(parts[1]) == str:
                            line = line.replace(parts[1], '"' + parts[1] + '"')

                    line = line.replace(';', ",")

                    if '"' not in parts[0]:
                        line = line.replace(parts[0], '"' + parts[0] + '"')

                print(line)
                # new_tmutil_data += line


        # print(new_tmutil_data)
        # json_data = json.loads(new_tmutil_data)
        # print(json.dumps(json_data, indent=4))

    def getDiskUtilPlist(self, file_to_read, remove_tmp):
        diskutil_plist_data = None
        try:
            os.system('diskutil list -plist > ' + file_to_read)
            with open(file_to_read, 'r') as diskutil_plist_file:
                diskutil_plist_data = diskutil_plist_file.read()
                diskutil_plist_data = plistlib.readPlistFromString(diskutil_plist_data)
            if remove_tmp:
                os.unlink(file_to_read)
            return diskutil_plist_data
        except Exception, e:
            self.sendToTerminal(e)
            return None

    def sendToTerminal(self, message):
        if not self.quiet:
            print(message)

    def getDataFromTmUtilFile(self, file_to_output_to, file_to_read=None, key=None, pattern=None, remove_tmp=False):
        devnull = open(os.devnull, 'w')
        if not key:
            try:
                with open(file_to_output_to, 'w') as tmoutput:
                    subprocess.call("tmutil status", stdout=tmoutput, stderr=devnull, shell=True)
                if remove_tmp:
                    os.unlink(file_to_output_to)
                return True
            except:
                return False
        else:
            if key and pattern and file_to_read:
                try:
                    search_command = "cat " + file_to_read + " | awk '/" + key + "/ {print $3}' | grep -o '" + pattern + "\+' | awk '{print $1}'"
                    with open(file_to_output_to, 'w') as tmoutput:
                        subprocess.call(search_command, stdout=tmoutput, stderr=devnull, shell=True)

                    with open(file_to_output_to, 'r') as tmoutput:
                        data = tmoutput.read()
                        data = data.strip()

                    if remove_tmp:
                        os.unlink(file_to_output_to)

                    return data
                except Exception, e:
                    self.sendToTerminal(e)
                    return False
            else:
                return False

debug = True
if __name__ == '__main__':
    try:
        thisapp = BackupState()
        thisapp.main()
    except Exception as main_run_exception:
        if debug:
            print('__main__: ' + str(main_run_exception))
            print(traceback.format_exc())
        else:
            # TODO: Add logging to the application
            print('We encountered an error, please look at the log file')
    except KeyboardInterrupt:
        pass
