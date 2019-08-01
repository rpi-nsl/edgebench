# Author: Tobias J. Park

from config import *
import subprocess
import yaml
from Fileuploader import FileUploader
from time import sleep
import pandas as pd
from boto.s3.connection import S3Connection, Bucket, Key
import boto3
from Fetchfromblobstorage import BlobDetailsFetcher
import sys
from tqdm import tqdm

region = boto3.Session().region_name

class AWS:
    # this function extracts information from serverless.yml
    def extractFromYML(self):
        # calculate full filepath for serverless.yml
        yaml_filepath = ""
        if function_folder.endswith('/'):
            yaml_filepath = function_folder + "serverless.yml"
        else:
            yaml_filepath = function_folder + "/serverless.yml"
        # extract name of created AWS Lambda Application and buckets by parsing the yaml
        print("Extracting names of AWS Application, function, and buckets from serverless.yml...")
        # open the file
        try:
            yaml_file = open(yaml_filepath, 'r')
        except:
            print("Error: serverless.yml was not found in the function_folder directory.\n")
            exit()
        yaml_text = yaml_file.read()
        # parse the file
        yaml_parsed = yaml.load(yaml_text, Loader=yaml.FullLoader)
        try:
            self.application_name = yaml_parsed["service"] + "-dev"
            self.function_name = self.application_name + "-" + list(yaml_parsed["functions"].keys())[0]
        except:
            print("Error: could not extract appliation name and/or function name from serverless.yml. Verify that serverless.yml is formatted correctly.\n")
            exit()
        try:
            self.input_bucket = yaml_parsed["functions"][next(iter(yaml_parsed["functions"]))]["events"][0]["s3"]
        except:
            print("Error: could not extract input bucket name from serverless.yml. Verify that serverless.yml is formatted correctly.")
            exit()
        try:
            self.results_bucket = yaml_parsed["custom"]["resultsBucketName"]
        except:
            print("Error: could not extract results bucket name from serverless.yml. Verify that serverless.yml is formatted correctly.")
            exit()

    # this function deploys the lambda function to AWS via Serverless
    def deploy(self):
        print("Deploying function to AWS via Serverless...")
        try:
            deployment = subprocess.Popen(["serverless", "deploy", "--region", region], cwd=function_folder)
            deployment.wait()
            out, err = deployment.communicate()
        except:
            print("Error: Invalid function_folder filepath. Aborting...")
            exit()

    def emptyBuckets(self):
        # erase anything currently in the upload or results buckets so the script doesn't get confused
        print("Emptying upload and results buckets (this might take a while)...")
        conn = S3Connection()
        b = Bucket(conn, self.input_bucket)
        for x in b.list():
            b.delete_key(x.key)
        b = Bucket(conn, self.results_bucket)
        for x in b.list():
            b.delete_key(x.key)

    def upload(self):
        # uploads the files in alphabetical order (see important note in processBenchmakrs() function before changing this function)
        print("Uploading sample data to AWS S3 bucket " + self.input_bucket + "...")
        self.uploader_aws = FileUploader(application=self.application_name, platform=self.platform, stats_folder='./', aws_region_name = region, bucket_name=self.input_bucket)
        self.data_file_1 = self.uploader_aws.batch_upload_files(folder_path=data_folder, delay=upload_delay)
        print("Waiting " + str(wait_time) + " seconds to ensue that AWS finishes processing the data before continuing...")
        sleep(wait_time)

    # this function downloads, processes, and assembles the benchmark data into a CSV file which can then be opened and analyzed in Excel.
    def processBenchmarks(self):

        # Important note to future developers: this function assumes that upload() uploaded all the files to AWS strictly in alphabetical order - ie, that
        # if you had 5 files named 1.jpg, 2.jpg, 3.jpg, 4.jpg, and 20.jpg, they would upload to AWS in this order:
        # 1.jpg, 2.jpg, 20.jpg, 3.jpg, 4.jpg. (Notice that 20.jpg is uploaded before 3.jpg due to the way 'alphabetical' is defined by filesystems)

        # This assumption will always hold true given the current way that the upload() function is coded;
        # however, if the upload() function is ever changed such that the files are uploaded in an order different than the way just described,
        # then this function must be modified; otherwise, the output data will be incorrect.

        print("Processing upload benchmark data...")
        columns = ["Filename in AWS bucket:", "Upload Stopped at time:", "Upload Size:", "Object put in upload bucket at time:", "Original Filename", "Upload started at time:", "AWS Event Trigered at time:", "Function started at time:", "Function stopped at time:", "Object put in results bucket at time:", "Size of file in results bucket:"]
        rows = [] # rows contains more vectors, each one representing a row...
        # extract key, upload stop time, and upload size from self.data_file_1 for each uploaded file
        for x in self.data_file_1:
            temp = []
            temp.append(x[0])
            temp.append(x[2])
            temp.append(x[3])
            rows.append(temp)
        # download data from upload bucket
        print("Retrieving upload bucket benchmark data...")
        downloader_aws = BlobDetailsFetcher(application=self.application_name, platform='aws', stats_folder='./', aws_region_name = region)
        all_objects_aws = downloader_aws.get_all_blob_contents_from_uploads(self.input_bucket)
        # save data for each file
        for x in range(len(rows)):
            # perform simple check to make sure filenames line up
            if rows[x][0][0:len(all_objects_aws.loc[x, 'filename'])] != all_objects_aws.loc[x, 'filename']:
                print("Error: Downloaded file order does not match uploaded file order. Please increase upload delay time! Aborting... ")
                print(rows[x][0] + " is not equal to " + all_objects_aws.loc[x, 'filename'])
                quit()
            rows[x].append(all_objects_aws.loc[x, 'object_put_in_U_bucket_utc'])
            rows[x].append(all_objects_aws.loc[x, 'filename'])
            rows[x].append(all_objects_aws.loc[x, 'edge_upload_utc'])
        # download data from results bucket
        print("Retrieving results bucket benchmark data...")
        thumbnail = False
        try:
            all_objects_aws = downloader_aws.get_all_blob_contents_from_results(self.results_bucket)
        except: # we have most likely encountered the special case of Thumbnail-Pipeline, which works
        # completely different than all the other pipelines and needs to be handled with custom code
            print("JSON download failed, perhaps this is Thumbnail-Pipeline? Attempting to download thumbnail metadata...")
            # generate an array of maps where each map is a file's metadata
            all_objects_aws = []
            # prepare to collect names of all buckets, then add all bucket metadata to all_objects_aws
            client = boto3.client('s3')
            session = boto3.session.Session()
            resource = session.resource('s3')
            aws_bucket = resource.Bucket(self.results_bucket)
            bucket_contents = list(aws_bucket.objects.all())
            names = []
            for x in bucket_contents:
                names.append(x.key)
            for name in tqdm(names):
                all_objects_aws.append(client.head_object(Bucket=self.results_bucket, Key=name))
            thumbnail = True

        print("Retrieving sizes of objects in results bucket and finishing up (this may take a while)...")
        # save data for each file
        s3 = boto3.client('s3')
        if thumbnail == False:
            for x in range(len(rows)):
                if rows[x][0][0:len(all_objects_aws.loc[x, 'filename'])] != all_objects_aws.loc[x, 'filename']: # verify that filenames match
                    print("Error: Download bucket file order does not match upload bucket file order. This probably means that AWS did not have enough time to process the data. Aborting... ")
                    print(rows[x][0] + " is not equal to " + all_objects_aws.loc[x, 'filename'])
                    quit()
                rows[x][0] = all_objects_aws.loc[x, 'filename'] + "^" + all_objects_aws.loc[x, 'edgeuploadutctime'] + ".json"
                rows[x].append(all_objects_aws.loc[x, 'eventTime'])
                rows[x].append(all_objects_aws.loc[x, 'invoke_time'])
                rows[x].append(all_objects_aws.loc[x, 'funccompleteutctime'])
                rows[x].append(all_objects_aws.loc[x, 'object_put_in_R_Bucket_utc'])
                # find the size of the file in the bucket using https://stackoverflow.com/questions/5315603/how-do-i-get-the-file-key-size-in-boto-s3
                response = s3.head_object(Bucket=self.results_bucket, Key=rows[x][0])
                size = response['ContentLength']
                rows[x].append(size)
        else: # special case for thumbnail pipeline, which works differently
            x = 0
            for entry in all_objects_aws:
                if rows[x][0][0:len(entry['Metadata']['filename'])] != entry['Metadata']['filename']: # verify that filenames match
                    print("Error: Download bucket file order does not match upload bucket file order. This probably means that AWS did not have enough time to process the data. Aborting... ")
                    print(rows[x][0] + " is not equal to " + entry['Metadata']['filename'])
                    quit()
                rows[x][0] = entry['Metadata']['filename'] + "^" + entry['Metadata']['edgeuploadutctime']
                rows[x].append(entry['Metadata']['eventtime'])
                rows[x].append(entry['Metadata']['invoke_time'])
                rows[x].append(entry['Metadata']['funccompleteutctime'])
                rows[x].append(entry['LastModified'])
                # find the size of the file in the bucket using https://stackoverflow.com/questions/5315603/how-do-i-get-the-file-key-size-in-boto-s3
                response = s3.head_object(Bucket=self.results_bucket, Key=rows[x][0])
                size = response['ContentLength']
                rows[x].append(size)
                x = x + 1
        # swap KEY and UPLOAD STARTED AT TIME so that CSV file is easier to read
        temp = columns[0]
        columns[0] = columns[5]
        columns[5] = temp
        for x in range(len(rows)):
            temp = rows[x][0]
            rows[x][0] = rows[x][5]
            rows[x][5] = temp
        # move the filenames all the way to the left...
        # 1. Bucket filenames
        # copy everything in index 5, insert() into index 0, erase column 6
        columns.insert(0, columns[5])
        del(columns[6])
        for x in range(len(rows)):
            rows[x].insert(0, rows[x][5])
            del(rows[x][6])
        # 2. Original filenames
        # copy everything in index 5, insert() into index 0, erase column 6
        columns.insert(0, columns[5])
        del(columns[6])
        for x in range(len(rows)):
            rows[x].insert(0, rows[x][5])
            del(rows[x][6])
        final_results = pd.DataFrame(rows, columns=columns)
        final_results.to_csv(path_or_buf="results.csv")
        print("All done! Results saved to results.csv.\n")

    def cleanup(self):
        # ask user whether they want to now delete the buckets and lambda function
        answer = input("Would you like to delete the input bucket, result bucket, lambda function, and API Gateway (if it exists) from Amazon AWS? [y/n]: ")
        if answer == "y":
            # delete contents of results and input buckets
            self.emptyBuckets()
            # clean up everything
            print("Asking Serverless to remove the service...")
            deployment = subprocess.Popen(["serverless", "remove", "--region", region], cwd=function_folder)
            deployment.wait()
            out, err = deployment.communicate()

            self.uploader_aws.cleanup()

            print("Removal complete.")

    def __init__(self):
        self.platform = sys.argv[1]
        self.application_name = None # name of AWS application
        self.function_name = None    # name of AWS function
        self.input_bucket = None     # name of AWS S3 input bucket
        self.results_bucket = None   # name of AWS S3 results bucket
        self.data_file_1 = None      # contents of input bucket
        self.extractFromYML()
        self.deploy()
        self.emptyBuckets()
        self.upload()
        self.processBenchmarks()
        self.cleanup()

AWS()
