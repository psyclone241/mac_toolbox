#!/usr/bin/env python
import ConfigParser
import traceback
import sys
import os
import subprocess
import argparse
import plistlib
import json

class BackupState:

    def __init__(self):
        self.arg_parser = argparse.ArgumentParser()
        self.arg_parser.add_argument(
            "-c", "--config_file", help="Location of the configuration file")
        self.arg_parser.add_argument(
            "-m", "--method_to_use", help="Which method to use?", default='drive_data')
        self.arg_parser.add_argument(
            "-q", "--quiet", help="Prevents output to the screen", action="store_true", default=False)

        self.args = self.arg_parser.parse_args()

        self.defaults = {
            'config_file': 'config.ini',
            'drive_name': 'My Passport',
            'remove_tmp': True
        }

        # Collect any arguments passed to argparser
        self.quiet = self.args.quiet
        self.method_to_use = self.args.method_to_use

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
            else:
                raise Exception('No config.ini file was found')
        except:
            print('Could not load config.ini')
            exit()
        finally:
            if self.config_data:
                self.backup_name = self.config_data['drive_name']
                self.remove_tmp = self.config_data['remove_tmp']
            else:
                self.backup_name = self.defaults['drive_name']
                self.remove_tmp = self.defaults['remove_tmp']

            self.backup_device = None
            self.diskutil_plist = 'diskutil.plist'
            self.tmutil_output_file_name = 'tmutil_status.output'
            self.tmutil_running_file_name = 'tmutil_status_running.output'
            self.tmutil_percentage_file_name = 'tmutil_status_percentage.output'

    def main(self):
        if self.method_to_use:
            if self.method_to_use == 'drive_data':
                self.generateDriveData()
            else:
                print('Command not configured')
        else:
            print('No command specified')

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
            print(self.backup_device)
        else:
            print('No backup device named "' + self.backup_name + '" was found')

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
            print(e)
            return None

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
                    print(e)
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
