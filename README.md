
### BackUP-EBS-to-Glacier

These script is created with a purpose to backup(tar) all the EBS volumes attached to EC2 instances which are in **stopped** state and upload the tarball to AWS Glacier, script will delete the volumes attached to instances once backup is done. Script should be running on completely new instance, which will also generate CSV report file containg data such as Instane-Id, Volume-Id, Archive-Id on which the operations have been performed. A logger file will also be generated to go through failure logs.

Pre-requisites:
EC2 instance with boto installed - For running these script

##### Environment Setup
1. Launch a new EC2 instance
2. Download these script
3. Edit the config.json file

##### How it Works:
1. Script will pick one of the instances in stopped state and detach the volume attached to it. These volume is then attched to new EC2 instance (one where these script is running)
2. Attached volume will be mounted and tar file of the entire volume will be created
3. These tarball file will be uploaded to AWS Glacier which in turn will reterive the archive-id (Copy the archive-id to download the uploaded file)
4. The volume attached will now be un-mounted and re-attached to previous machines

##### Running the Script
$ python movevoltogal.py

