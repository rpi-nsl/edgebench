#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May  2 13:03:42 2019

@author: "Anirban Das"
"""
import boto3
from azure.storage.blob import BlockBlobService
import os
import sys
import datetime
import csv
import time
import uuid


class FileUploader(object):

    def __init__(self, platform, application, stats_folder, **kwargs):
        self.platform = platform.lower()
        self.application = application.lower()
        self.stats_folder = stats_folder
        if self.platform == 'aws':
            self.service_client, self.bucket = self.__initiate_aws(**kwargs)
        elif self.platform == 'azure':
            if 'azure_storage_account_key' not in kwargs or 'azure_storage_account_name' not in kwargs:
                print("\nYou need to give both azure storage account name and key to access container services:")
                print("""Sample Command: uploader_azure = Fileuploader(application='audio', platform='azure', stats_folder='./', input_folder='./',
                                                        azure_storage_account_name="<acc_name>",
                                                        azure_storage_account_key="<acc_key>",
                                                        bucket_name="<bucket_name/container_name>")""")
                raise ValueError("Invalid Arguments in class creation")
            self.service_client, self.bucket = self.__initiate_azure(**kwargs)

    def __initiate_aws(self, bucket_name="test_bucket_{}".format(uuid.uuid4()), aws_access_key_id="", aws_secret_access_key="", aws_region_name="us-east-1"):
        current_session = boto3.session.Session(
					aws_access_key_id = aws_access_key_id,
					aws_secret_access_key = aws_secret_access_key,
					region_name = aws_region_name)
        service_client = current_session.client('s3')
        bucketname = bucket_name #if bucket_name not None else "test_bucket_{}".format(uuid.uuid4())
        # Call S3 to list current buckets
        response = service_client.list_buckets()

        # Get a list of all bucket names from the response
        buckets = [bucket['Name'] for bucket in response['Buckets']]

        # Create a bucket if not present
        if bucketname not in buckets:
            service_client.create_bucket(Bucket=bucketname)
            print("Created S3 bucket {}".format(bucketname))
        else:
            print("Selected existing S3 bucket {}".format(bucketname))
        return service_client, bucketname

    def __initiate_azure(self, azure_storage_account_name, azure_storage_account_key, bucket_name="test_bucket_{}".format(uuid.uuid4()) ):
        block_blob_service = BlockBlobService(account_name=azure_storage_account_name,
                                              account_key=azure_storage_account_key)
        container_name = bucket_name
        # Create container if it not present
        exists = block_blob_service.create_container(container_name)
        if not exists:
            print("Container {} already exists".format(container_name))
        else:
            print("Created container {}".format(container_name))

        return block_blob_service, container_name

    # write local stats in a csv file
    def write_local_stats(self, filename, stats_list):
        	try:
        		filepath = self.stats_folder.rstrip(os.sep) + os.sep + filename
        		with open(filepath, 'a') as file:
        			writer = csv.writer(file, delimiter=',')
        			writer.writerows(stats_list)
        	except :
        		e = sys.exc_info()[0]
        		print("Exception occured during writting Statistics File: %s" % e)


    def __choose_azure_upload_service(self, file_path=None, count=0):
        upload_start_utc_timestamp = datetime.datetime.utcnow().isoformat()
        file_name = file_path.split(os.sep)[-1]+"^{}".format(datetime.datetime.utcnow().isoformat())
        self.service_client.create_blob_from_path(self.bucket, file_name, file_path)
        size = os.path.getsize(file_path)
        upload_stop_utc_timestamp = datetime.datetime.utcnow().isoformat()
        return True , [file_name, upload_start_utc_timestamp, upload_stop_utc_timestamp, size]

    def __choose_aws_upload_service(self, file_path=None, count=0):
        upload_start_utc_timestamp = datetime.datetime.utcnow().isoformat()
        file_name = file_path.split(os.sep)[-1]+"^{}".format(datetime.datetime.utcnow().isoformat())
        self.service_client.upload_file(file_path, self.bucket, file_name)
        size = os.path.getsize(file_path)
        upload_stop_utc_timestamp = datetime.datetime.utcnow().isoformat()
        return True , [file_name, upload_start_utc_timestamp, upload_stop_utc_timestamp, size]


    def upload_file(self, file_path=None, count=0, json_payload=None):

        try:
            if self.platform == 'aws':
                status, details_list = self.__choose_aws_upload_service(file_path, count, json_payload)
            elif self.platform == 'azure':
                status, details_list = self.__choose_azure_upload_service(file_path, count, json_payload)

            return status, details_list

        except Exception as e:
            print("Exception  in uploading {}".format(e))
            return False, ["", "", "", ""]

    def batch_upload_files(self, folder_path, sleep=1):
        all_details = []
        try:
            for count, file in enumerate(os.listdir(folder_path)):
                file_path = os.path.join(folder_path, file)
                print("Uploaded {}".format(file_path))
                status, details_list = self.upload_file(file_path=file_path, count=count)
                all_details.append(details_list)
                time.sleep(1)
            return all_details

        except Exception as e:
            print("Exception  in uploading {}".format(e))
            return [["", "", "", ""]]
