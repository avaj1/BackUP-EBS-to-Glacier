import os
import boto
import boto.ec2
from boto.glacier.layer1 import Layer1
from boto.glacier.concurrent import ConcurrentUploader
import time
import subprocess
import json
import csv
import logging


def mountpointexists():
    if os.path.exists("/dev/xvdf1"):
        subprocess.call(
            "sudo mount /dev/xvdf1 ~/vol/",
            shell=True)
    else:
        subprocess.call(
            "sudo mount /dev/xvdf ~/vol/",
            shell=True)

if os.path.isfile("config.json"):
    with open("config.json", 'r') as cfg_data:
        try:
            data = json.load(cfg_data)
        except Exception as e:
            print e
else:
    print "config.json does not exist " + e

logger = logging.getLogger("logger_movevoltogal")
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(
    filename=data['log_filename'],
    format=log_format,
    datefmt='%d/%m/%Y %H:%M:%S',
    level=logging.INFO)

fieldnames = ['Instance_ID', 'Volume_ID',
              'Block_Device_Name', 'Vault_Name', 'Archive_ID']

conn = boto.ec2.connect_to_region(
    data['region'],
    aws_access_key_id=data['aws_access_key_id'],
    aws_secret_access_key=data['aws_secret_access_key'])
if conn is None:
    logger.error("Error connecting AWS")
else:
    reservations = conn.get_all_reservations(
        filters={
            "instance-state-name": data['instance_state'],
            "availability_zone": data['availability-zone']})
    for reservation in reservations:
        try:
            for instance in reservation.instances:
                instanceid = instance.id
                tagvalue = instance.tags['Name']
                # bdm=block-device-mapping
                bdm = instance.block_device_mapping
                try:
                    for device in bdm:
                        bdt = bdm[device]        	# bdt=block-device-type
                        volid = bdt.volume_id
                        print "\n--" + instanceid + "-----" + device + "-----" + volid + "--"
                        logger.info("--" + instanceid + "-----" +
                                    device + "-----" + volid + "--")

        # Detach volume and attach to temporary instance
                        try:
                            conn.detach_volume(volid)
                            time.sleep(10)
                            vol = conn.get_all_volumes(volid)
                            volstatus = vol[0].attachment_state()
                            if volstatus is None:
                                logger.info(
                                    volid + " is detach from " + instanceid)
                                check = conn.attach_volume(
                                    volid,
                                    data['instance_id'],
                                    "/dev/sdf")
                                time.sleep(10)
                                check1 = conn.get_all_volumes(volid)
                                checks = check1[0].attachment_state()
                                logger.info(
                                    volid + " is attached to " +
                                            data['instance_id'])
                        except Exception as e:
                            logger.error(
                                "Volume seems busy, can't attach: " + str(e))

        # Perform a archive operation of attched volume
                        archive_file = tagvalue + "_" + instanceid + "_" + volid
                        try:
                            voldir = os.path.isdir("/home/ec2-user/vol/")
                            if voldir is False:
                                subprocess.call(
                                    "sudo mkdir ~/vol/ ",
                                    shell=True)
                                mountpointexists()
                            else:
                                mountpointexists()
                            subprocess.call(
                                "sudo tar -czf " +
                                archive_file +
                                ".tar.gz ~/vol/* &> /dev/null",
                                shell=True)
                            print "Archive done for " + volid
                            subprocess.call("sudo umount ~/vol/", shell=True)
                        except Exception as e:
                            logger.error("Error in archive: " + str(e))

        # Upload archive file to AWS Glacier
                        try:
                            vault_name = str(data['vault_name'])
                            part_size = int(data['part_size'])
                            num_threads = int(data['num_threads'])
                            print "Backing archive of " + volid + " to Glacier"
                            glacierconn = Layer1(
                                aws_access_key_id=data['aws_access_key_id'],
                                aws_secret_access_key=data[
                                    'aws_secret_access_key'],
                                region_name=data['region'])
                            vault = glacierconn.describe_vault(vault_name)
                            uploader = ConcurrentUploader(
                                glacierconn,
                                vault_name,
                                part_size=part_size,
                                num_threads=num_threads)
                            archive_id = uploader.upload(
                                (archive_file + ".tar.gz"),
                                "first upload")
                            print "Download the archive using: " + archive_id
                        except Exception as e:
                            logger.error("Glacier error: " + str(e))

        # Detach the volume from temporary instance and associate it back to
        # respective instance
                        try:
                            conn.detach_volume(volid)
                            time.sleep(15)
                            vol = conn.get_all_volumes(volid)
                            volstatus = vol[0].attachment_state()
                            if volstatus is None:
                                logger.info(
                                    volid + " is detach from " +
                                    data['instance_id'])
                                conn.attach_volume(volid, instanceid, device)
                                logger.info(volid + " deleted")
                        except Exception as e:
                            logger.error(
                                "Volume seems busy, can't delete: " + str(e))

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
                    logger.error(str(e))
                    continue
        except Exception as e:
            logger.error(str(e))
