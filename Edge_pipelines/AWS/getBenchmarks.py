# Author: Tobias J. Park
import subprocess
import yaml
import json
from boto.s3.connection import S3Connection, Bucket, Key
import boto3
from time import sleep
import csv
from os import listdir
from Fetchfromblobstorage import BlobDetailsFetcher
from collections import OrderedDict
import sys
from tqdm import tqdm
from config import *
import socket

Cedge1 = 'f_t0'

yaml_folder = "./"

region = boto3.Session().region_name

stats_folder = "/home/pi/AWS/Statistics/" # (MUST END WITH /)

# handles deployment of the function to Greengrass
class AWS:
    def emptyBucket(self, bucket):
        try:
            # empty anything currently in the upload or results buckets so the script doesn't get confused
            conn = S3Connection()
            b = Bucket(conn, bucket)
            for x in b.list():
                b.delete_key(x.key)
        except:
            pass # bucket does not exist, and is therefore empty, so our job is done...

    def createTopicRule(self):
        # check that ALL the topic rules we are about to create do not exist; if they do, erase them.
        for x in self.rule_names :
            print("Verifying that topic rule " + x + " does not already exist, deleting it if it does...")
            try:
                self.rule_client.delete_topic_rule(ruleName=x)
            except:
                pass
        print("Creating new topic rule...")
        self.greengoCmd("create-topic-rule")

    def replace(self, filename, original, replacement): # puts the correct IP in ./remote_setup.sh
        # below code taken from https://stackoverflow.com/questions/17140886/how-to-search-and-replace-text-in-a-file-using-python
        with open(filename, 'r') as file :
            filedata = file.read()

        # Replace the target string
        filedata = filedata.replace(original, replacement)

        # Write the file out again
        with open(filename, 'w') as file:
            file.write(filedata)
            file.close()

    def greengoCreate(self): # create group and lambdas
        # open ./.edgebench/role.txt
        try:
            file = open('./.edgebench/role.txt', 'r')
            role = file.read().rstrip() # saves role without the \n character

        except:
            print("Error: ./.edgebench/role.txt not found. Did you run initial_setup.py?")
            quit()

        # check that the group we are about to create does not already exist; if it does, erase it
        print("Verifying that group " + self.group_name  + " does not already exist...")
        try:
            if self.group_id  != 0:
                self.greengrass_client.reset_deployments(Force=True, GroupId=self.group_id) # must reset deployment before removing group or it will fail
                self.greengrass_client.delete_group(GroupId=self.group_id )
                print("Group " + self.group_name  + " exists, deleted it...")
        except:
            pass
        # check that ALL of the lambdas we are about to create do not exist; if they do, erase them
        for x in self.function_names :
            print("Verifying that function " + x + " does not already exist...")
            try:
                self.lambda_client.delete_function(FunctionName=x)
                print("Function " + x + " exists, deleted it...")
            except:
                pass

        print("Verifying that policy " + self.group_name  + "-policy does not already exist...")
        try:
            # get targets
            target = self.rule_client.list_targets_for_policy(policyName=self.group_name  + "-policy")
            # detatch all targets
            for x in target['targets']:
                self.rule_client.detach_policy(policyName=self.group_name  + "-policy", target=x)
            # delete the policy
            self.rule_client.delete_policy(policyName=self.group_name  + "-policy")
            print("Policy " + self.group_name  + "-policy exists, deleted it...")
        except:
            pass


        # compute IP address using answer from https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib/25850698#25850698
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))  # connect() for UDP doesn't send packets
        local_ip_address = s.getsockname()[0]
        print("Adding IP address " + local_ip_address + " to configuration...")
        self.replace("./config.sh", '""', '"' + local_ip_address + '"')

        print("Creating/configuring new group, function, etc. in Greengrass...")
        self.greengoCmd("create")
        print("Retrieving certificates...")
        bash = subprocess.Popen(["./remote_setup.sh"], cwd=yaml_folder)
        bash.wait()

        print("Associating role " + role + " with new group " + self.group_name)
        self.storeGroupId()
        self.greengrass_client.associate_role_to_group(GroupId=self.group_id, RoleArn=role)
        print("Removing IP address " + local_ip_address + " from configuration...")
        self.replace("./config.sh", local_ip_address, '')

    def storeGroupId(self):
        # convert group_name to a group_id
        groups = self.greengrass_client.list_groups()
        for group in groups['Groups']:
            if group["Name"] == self.group_name :
                self.group_id  = group["Id"]

    def greengoCreateS3(self):
        # check that ALL the s3 buckets we are about to create do not exist; if they do, empty them, then erase them.
        for x in self.bucket_names:
            print("Verifying that bucket " + x + " does not already exist...")
            try:
                bucket = self.s3.Bucket(x)
                self.emptyBucket(x)
                bucket.delete()
                print("Bucket " + x + " exists, deleted it...")
            except:
                pass
        print("Creaing new s3 bucket...")
        self.greengoCmd("create-s3-buckets")

    def greengoCmd(self, x): # executes "greengo x" in the terminal from yaml_folder to run greengo commands
        bash = subprocess.Popen("~/.local/bin/greengo " + x, cwd=yaml_folder, shell=True)
        bash.wait()

    def stopGreengrass(self):
        print("Stopping Greengrass software on device (if it is running)...")
        bash = subprocess.Popen(["sudo", "./greengrassd", "stop"], cwd="/greengrass/ggc/core")
        bash.wait()

    def awsConnect(self):
        print("Establishing connections to AWS...")
        self.rule_client = boto3.client('iot')
        self.lambda_client = boto3.client('lambda')
        self.greengrass_client = boto3.client('greengrass')
        self.s3 = boto3.resource('s3')

    def extractYaml(self):
        # extract the self.group_name  and bucket_name from the YAML
        print("Collecting info from greengo.yaml...")
        yaml_filepath = ""
        try:
            if yaml_folder.endswith('/'):
                yaml_filepath = yaml_folder + "greengo.yaml"
            else:
                yaml_filepath = yaml_folder + "/greengo.yaml"
            yaml_file = open(yaml_filepath, 'r')
        except:
            print("Error: greengo.yaml not found.")
            quit()

        yaml_text = yaml_file.read()
        yaml_parsed = yaml.load(yaml_text, Loader=yaml.FullLoader)
        try:
            self.group_name  = yaml_parsed["Group"]['name']
            self.group_id  = 0
        except:
            print("Error: Group name not found in greengo.yaml.")
            quit()

        self.storeGroupId()

        try:
            # loop through all the functions in the yaml, append them to the self.function_names  list
            self.function_names  = []
            for x in range(len(yaml_parsed["Lambdas"])):
                self.function_names .append(yaml_parsed["Lambdas"][x]["name"])
        except:
            print("Error: Lambdas not found in greengo.yaml.")
            quit()

        try:
            # loop through all buckets in the yaml, append them to self.bucket_names  list
            self.bucket_names  = []
            for x in range(len(yaml_parsed["ResultS3Buckets"])):
                self.bucket_names .append(yaml_parsed['ResultS3Buckets'][x]['Bucket'])
        except:
            print("Error: Buckets not found in greengo.yaml.")
            quit()

        try:
            # loop through all the topic rules in the yaml, append them to the topic_rules list
            self.rule_names  = []
            for x in range(len(yaml_parsed["Rules"])):
                self.rule_names .append(yaml_parsed["Rules"][x]['ruleName'])
        except:
            pass # some pipelines, like thumbnail-pipeline, do not have topic rules.

    def extractJson(self):
        # extract the self.group_name  and bucket_name from the json
        print("Collecting info from ./.gg/gg_state.json")
        json_filepath = ""
        self.group = 0 # 1 = update (we're still using previoius group); 2 = remove, create (group name changed since last time); 3 = create (first time running ever)
        self.json_group_name   = ""
        self.json_bucket_name  = []

        # get json filename
        if yaml_folder.endswith('/'):
            json_filepath = yaml_folder + ".gg/gg_state.json"
        else:
            json_filepath = yaml_folder + "/.gg/gg_state.json"
        try:
            # parse the json
            json_file = open(json_filepath, 'r')
            json_text = json_file.read()
            parsed_json = json.loads(json_text)
            self.json_group_name   = parsed_json["Group"]["Name"]
            if self.group_name  == self.json_group_name  :
                self.group = 1
            else:
                self.group = 2
            for x in range(len(parsed_json["Lambdas"])):
                self.json_bucket_name .append(parsed_json["Lambdas"][x]["Environment"]["Variables"]["RESULTS_BUCKET"])

        except:
            # json does not exist, that means this is our first group ever.
            self.group = 3

    def deleteStats(self):
        # delete existing stat files
        print("Deleting existing statistics files...")
        bash = subprocess.Popen("rm -f *", cwd=stats_folder, shell=True)
        bash.wait()

    def setupGroup(self):
        # logic for how to create/update group
        if self.group == 1:
            print("Updating Greengrass group...")
            self.greengoCmd("update")
        elif self.group == 2:
            print("Removing old group...")
            self.greengoRemove(self.json_bucket_name[0])
            self.greengoCreate()
        elif self.group == 3:
            self.greengoCreate()

    def setupS3(self):
        # logic for how to create/update buckets
        if self.group == 1:
            print("Removing old s3 buckets...")
            for x in self.json_bucket_name :
                self.emptyBucket(x) # we need to do a for loop through a list of bucket names in the json and empty all of those
            bash = subprocess.Popen("~/.local/bin/greengo delete-s3-buckets", cwd=yaml_folder, shell=True)
            bash.wait()
        self.greengoCreateS3()

    def setupTopicR(self):
        # logic for how to create/update topic rule
        if self.group == 1:
            print("Deleting old topic rule...")
            self.greengoCmd("delete-topic-rule")
        self.createTopicRule()

    def startGreengrass(self):
        print("Launching Greengrass software on device...")
        bash = subprocess.Popen(["sudo", "./greengrassd", "start"], cwd="/greengrass/ggc/core")
        bash.wait()

    def deploy(self):
        print("Deploying...")
        bash = subprocess.Popen("~/.local/bin/greengo deploy", cwd=yaml_folder, shell=True)
        bash.wait()
        print("Function should now be running on the Edge device. It may take ~60 seconds before processing of the input data begins.")

    def CollectData(self, bucket):
        print("Waiting for function to finish running (this will take a few minutes)...")
        while True:
            sleep(10)
            test = listdir('/home/pi/AWS/Statistics')
            if len(test) > 0:
                break
        print('Compiling benchmark results...')
        csvrows = []
        # get statistics file's filename
        filenames = listdir('/home/pi/AWS/Statistics')
        try:
            filename = filenames[0]
        except:
            print("Error: Local statistics file not found.")
            quit()
        # load CSV file into csvrows
        with open('/home/pi/AWS/Statistics/' + filename) as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                csvrows.append(row)

        firstrow = True
        c1index = 0
        c2index = 0
        starttimeindex = 0
        dict = OrderedDict() # create a dictionary where the key is the first element and the value is an array of everything
        for row in csvrows: # for each row in the stats file
            dict[row[0]] = []
            index=0
            if firstrow == True:
                dict[row[0]].append("Compute Time (C_edge, total time required for processing one item): ") # add the headers to the top of results.csv
                dict[row[0]].append("Time when function began processing this file: ")
            c1temp = None
            c2temp = None
            starttimetemp = None
            for item in row: # for each item in this row
                if firstrow == True:
                    if item == 'starttime':
                        starttimeindex = index
                    if item == Cedge1: # locate the columns containing Cedge1 and Cedge2 and save them
                        c1index = index
                    if item == Cedge2:
                        c2index = index
                        firstrow = False
                        pass
                else:
                    if index == c1index and item != Cedge1: # if this is a column with Cedge1, save the value of Cedge1
                        c1temp = item
                    if index == c2index and item != Cedge2: # same for Cedge2
                        c2temp = item
                    if index == starttimeindex and item != 'starttime':
                        starttimetemp = item
                index = index + 1

            if c1temp and c2temp and starttimetemp:
                dict[row[0]].append(str(float(c2temp) - float(c1temp))) # compute and add Cedge = Cedge2 - Cedge1 for this row
                dict[row[0]].append(starttimetemp)


        # download the json's from the cloud, find the identifier to match it with the array in the dicionary, append the stuff to the end.
        # we assume that the identifier (unique filename or id of each item being procesed) is at position 0, 0 of csvrows:
        identifier = csvrows[0][0] # messageid, the top-left-most thing
        downloader_aws = BlobDetailsFetcher(platform='aws', application='', stats_folder='', aws_region_name=region) # application and stats_folder are not actually used, and can thus be blank
        thumbnail = False
        try:
            all_objects_aws_pd = downloader_aws.get_all_blob_contents_from_results(bucket) # download results data as a panda
            # convert panda to dictionary
            all_objects_aws = all_objects_aws_pd.to_dict('records')
        except:
            # this might be the thumbnail pipeline, which does not save a json but instead saves an image with metadata.
            #print("JSON download failed, perhaps this is Thumbnail-Pipeline? Attempting to download thumbnail metadata...")
            # generate an array of maps where each map is a file's metadata
            all_objects_aws = []
            # prepare to collect names of all buckets, then add all bucket metadata to all_objects_aws
            client = boto3.client('s3')
            session = boto3.session.Session()
            resource = session.resource('s3')
            aws_bucket = resource.Bucket(bucket)
            bucket_contents = list(aws_bucket.objects.all())
            names = []
            for x in bucket_contents:
                names.append(x.key)
            for name in tqdm(names):
                all_objects_aws.append(client.head_object(Bucket=bucket, Key=name))
            thumbnail = True


        firsttime = True

        for entry in all_objects_aws: # for each row in the panda
            if firsttime:
                # append headers to top of file
                dict[identifier].append("T1 (Time when message is published from edge device): ")
                dict[identifier].append("T2 (Time when message is en-queued in the IoT Hub): ")
                dict[identifier].append("T3 (Time when IoT blob file is created): ")
                firsttime = False
            if thumbnail == False:
                try:
                    dict[entry[identifier]].append(entry['messagesendutctime'])
                except:
                    dict[entry[identifier]].append(entry['funccompleteutctime']) # in some pipelines, messagesendutctime is called funccompleteutctime
                dict[entry[identifier]].append(entry['iothub_timestamp'])
                dict[entry[identifier]].append(entry['object_put_in_R_Bucket_utc'])
            else: # thumbnail pipeline code
                dict[entry['Metadata']['imagefilename']].append(entry['Metadata']['funccompleteutctime']) # in some pipelines, messagesendutctime is called funccompleteutctime
                dict[entry['Metadata']['imagefilename']].append("N/A") # T2 never occurs for thumbnail pipeline
                dict[entry['Metadata']['imagefilename']].append(entry['LastModified'])

        # convert dict to a 2D array
        array = []
        for key in dict:
            subarray = [key] # must include key, which is the filename
            for value in dict[key]:
                subarray.append(value) # then add everything else
            array.append(subarray)

        # save 2D array as a final CSV file
        with open('results.csv', 'w') as csvfile:
            writer = csv.writer(csvfile)
            for row in array:
                writer.writerow(row)

    def Cleanup(self, bucket):
        answer = input("All done! Would you like to clean up? (ie, remove deployment from Greengrass, delete Greengrass group and functions, s3 buckets, subscriptions, topic rules, etc?) [y/n]: ")
        if answer == 'y' or answer == 'Y':
            self.greengoRemove(bucket)

    def greengoRemove(self, bucket):
        if True:
            bash = subprocess.Popen("~/.local/bin/greengo " + "delete-topic-rule", cwd=yaml_folder, shell=True)
            bash.wait()
            # empty the buckets first!
            self.emptyBucket(bucket)
            bash = subprocess.Popen("~/.local/bin/greengo " + "delete-s3-buckets", cwd=yaml_folder, shell=True)
            bash.wait()
            # remove all the principals except for the one that we want?
            if yaml_folder.endswith('/'):
                json_filepath = yaml_folder + ".gg/gg_state.json"
            else:
                json_filepath = yaml_folder + "/.gg/gg_state.json"
            # parse the json
            json_file = open(json_filepath, 'r')
            json_text = json_file.read()
            parsed_json = json.loads(json_text)
            certificate = parsed_json["Cores"][0]["keys"]['certificateArn'] # this is the one not to remove becaue greengo will remove it for us
            print("Removing all certificates from the IoT thing except for " + certificate)
            client = boto3.client('iot')
            thing = parsed_json["Cores"][0]['thing']['thingName']
            print("Searching thing " + thing) # wait, why are we searching the policy? the certificate is attached to the thing... shoot
            list = client.list_thing_principals(thingName=thing)['principals'] # gives list of arns of certificates
            for x in list:
                print("Examining certificate " + x)
                if x != certificate:
                    id = x.split("/")[1] # extract id from the ARN
                    client.update_certificate(certificateId=id, newStatus='INACTIVE')
                    # detatch certificate from thing
                    client.detach_thing_principal(thingName=thing, principal=x)
                    print("Removed certificate. Waiting 10 seconds to make sure principal detatches from thing...")
                    sleep(10)
                    client.delete_certificate(certificateId=id, forceDelete=True)
                else:
                    print("Keeping policy " + x + " for greengo to remove")

            bash = subprocess.Popen("~/.local/bin/greengo " + "remove", cwd=yaml_folder, shell=True)
            bash.wait()

    def __init__(self):
        # initialize variables
        self.rule_client = None
        self.lambda_client = None
        self.greengrass_client = None
        self.s3 = None
        self.group_name  = None
        self.group_id  = None
        self.function_names  = None
        self.bucket_names  = None
        self.rule_names  = None
        self.json_group_name   = None
        self.json_bucket_name  = None
        self.group = None

        # execute
        if len(sys.argv) == 3 and sys.argv[1] == "retrieve_only":
            self.CollectData(sys.argv[2])
        elif len(sys.argv) == 3 and sys.argv[1] == "remove_only":
            self.Cleanup(sys.argv[2])
        else:
            self.stopGreengrass()
            self.awsConnect()
            self.extractYaml()
            self.extractJson()
            self.deleteStats()
            self.setupGroup()
            self.setupS3()
            self.setupTopicR()
            self.startGreengrass()
            self.deploy()
            self.CollectData(self.bucket_names[0])
            self.Cleanup(self.bucket_names[0])

AWS()
