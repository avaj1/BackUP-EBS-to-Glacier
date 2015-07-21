import os
import boto
import boto.ec2
from boto.glacier.layer1 import Layer1
from boto.glacier.concurrent import ConcurrentUploader
import time
import subprocess
import json
import csv

if os.path.isfile("config.json"):
    with open("config.json", 'r') as cfg_data:
        try:
            data = json.load(cfg_data)
        except Exception as e:
            print e
else:
    print "config.json does not exist " + e

fieldnames = ['Instance_ID', 'Volume_ID', 'Block_Device_Name', 'Achive_ID']

conn = boto.ec2.connect_to_region(
    data['region'],
    aws_access_key_id=data['aws_access_key_id'],
    aws_secret_access_key=data['aws_secret_access_key'])
if conn is None:
    print "Error"
else:
    reservations = conn.get_all_reservations(
        filters={
            "instance-state-name": "stopped"})
    for reservation in reservations:
        try:
            for instance in reservation.instances:
                instanceid = instance.id
                tagvalue = instance.tags['Name']
                # bdm=block-device-mapping
                bdm = instance.block_device_mapping
                try:
                    for device in bdm:
                        bdt = bdm[device]    		# bdt=block-device-type
                        volid = bdt.volume_id
                        print "--"+instanceid+"-----"+device+"-----"+volid+"--"

        # Detach volume and attach to temporary instance
                        try:
                            conn.detach_volume(volid)
                            time.sleep(10)
                            conn.attach_volume(
                                volid,
                                data['instance_id'],
                                "/dev/sdf")
                            time.sleep(10)                            
                        except Exception as e:
                            print "\n Error in attaching volume: " + str(e)

        # Perform a archive operation of attched volume
                        try:
                            if os.path.isdir("/home/ec2-user/vol/"):
                                subprocess.call(
                                    "sudo mount /dev/xvdf1 ~/vol/",
                                    shell=True)
                            else:
                                subprocess.call(
                                    "sudo mkdir ~/vol/",
                                    shell=True)
                            subprocess.call(
                                "sudo mount /dev/xvdf1 ~/vol/",
                                shell=True)
                            subprocess.call(
                                "sudo tar -czf " +
                                volid +
                                ".tar.gz ~/vol/* &> /dev/null",
                                shell=True)
                            print "Archive done for " + volid
                            subprocess.call("sudo umount ~/vol/", shell=True)
                        except Exception as e:
                            print "Error while archive operation : " + str(e)

        # Upload archive file to AWS Glacier
                        try:
                            vault_name = str(data['vault_name'])
                            part_size = int(data['part_size'])
                            num_threads = int(data['num_threads'])
                            print "Backing Up archive of "+volid+" to Glacier"
                            galcierconn = Layer1(
                                aws_access_key_id=data['aws_access_key_id'],
                                aws_secret_access_key=data[
                                    'aws_secret_access_key'],
                                region_name=data['region'])
                            vault = galcierconn.describe_vault(vault_name)
                            uploader = ConcurrentUploader(
                                galcierconn,
                                vault_name,
                                part_size=part_size,
                                num_threads=num_threads)
                            archive_id = uploader.upload(
                                (volid + ".tar.gz"),
                                "first upload")
                            print "Download the archive using: " + archive_id
                        except Exception as e:
                            print "Glacier error: " + str(e)

        # Detach the volume from temporary instance and associate it back to
        # respective instance
                        try:
                            conn.detach_volume(volid)
                            time.sleep(10)
                            conn.delete_volume(volid)
                            time.sleep(10)
                        except Exception as e:
                            print "Error: " + str(e)

        # Generate CSV file
                        if os.path.isfile(data['csv_filename']):
                            reporter = csv.writer(
                                open(
                                    data['csv_filename'],
                                    'ab'),
                                delimiter=',',
                                quotechar='"',
                                escapechar='\\')
                        else:
                            reporter = csv.writer(
                                open(
                                    data['csv_filename'],
                                    'wb'),
                                delimiter=',',
                                quotechar='"',
                                escapechar='\\')

                        reporter.writerow(fieldnames)
                        csv_values = instanceid, volid, \
                            device, vault_name, archive_id
                        reporter.writerow(csv_values)

                except Exception as e:
                    print str(e)
                    continue
        except Exception as e:
            print str(e)
