#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May  2 16:04:34 2019

@author: "Anirban Das"
"""

import json
import pandas as pd
from tqdm import tqdm
import sys
import pandas as pd


class BlobDetailsFetcher(object):
    def __init__(self, platform, application, stats_folder, **kwargs):
        self.platform = platform.lower()
        self.application = application.lower()
        self.stats_folder = stats_folder
        if self.platform == 'aws':  
            self.service_resource, self.service_client = self.__initiate_aws(**kwargs)
        elif self.platform == 'azure':
            if 'azure_storage_account_key' not in kwargs or 'azure_storage_account_name' not in kwargs:
                print("\nYou need to give both azure storage account name and key to access container services:")
                print("""Sample Command: uploader_azure = Fileuploader(application='audio', platform='azure', stats_folder='./', input_folder='./', 
                                                        azure_storage_account_name="<acc_name>", 
                                                        azure_storage_account_key="<acc_key>")""")
                raise ValueError("Invalid Arguments in class creation")
            self.service_client = self.__initiate_azure(**kwargs)
    
    
    def __initiate_aws(self, aws_access_key_id="", aws_secret_access_key="", aws_region_name="us-east-1"):
        import boto3
        current_session = boto3.session.Session(
					aws_access_key_id = aws_access_key_id,
					aws_secret_access_key = aws_secret_access_key, 
					region_name = aws_region_name)
        service_resource = current_session.resource('s3')
        service_client   = current_session.client('s3')
        return service_resource, service_client
    
    def __initiate_azure(self, azure_storage_account_name, azure_storage_account_key):
        from azure.storage.blob import BlockBlobService
        block_blob_service = BlockBlobService(account_name=azure_storage_account_name, 
                                              account_key=azure_storage_account_key)
        
        return block_blob_service
    
    
    def get_all_bucket_objects_list(self, bucket_name):
        #returns iterable of all object names / headers in bucket or container
        if self.platform =='aws':
            aws_bucket = self.service_resource.Bucket(bucket_name)
            all_json_objects = list(aws_bucket.objects.all())
            return all_json_objects
        elif self.platform == 'azure':
            generator = self.service_client.list_blobs(bucket_name)
            return generator
    
    
    def get_all_blob_contents_from_uploads(self, bucket_name):
        #gets all the blob contents from the uploads folders 
        generator = self.get_all_bucket_objects_list(bucket_name)
        payload_list = [["object_put_in_U_bucket_utc", "filename", "edge_upload_utc", "upload_bucket_name"]]
        if self.platform == 'aws':
            for blob in tqdm(generator):
                # aws doesnot return the last modified time in the names generator so have to fetch the head of each blob only
                object_data = self.service_client.head_object(Bucket=blob.bucket_name, Key=blob.key)
                payload_list.append([object_data['LastModified'].isoformat(),
                                     blob.key.split('^')[0].replace("%3A", ':'),
                                     blob.key.split('^')[-1].replace("%3A", ':'),
                                     blob.bucket_name])
        elif self.platform =='azure':
            for blob in tqdm(generator):
                payload_list.append([blob.properties.last_modified.isoformat(),
                                     blob.name.split('^')[0].replace("%3A", ':'),
                                     blob.name.split('^')[-1].replace("%3A", ':'),
                                     bucket_name])
    
        return pd.DataFrame(payload_list[1:], columns=payload_list[0])
            

    def get_all_blob_contents_from_results(self, bucket_name, azure_folder_filter=""):
        #gets all the blob contents from the uploads folders 
        generator = self.get_all_bucket_objects_list(bucket_name)
        payload_list = []
        if self.platform == 'aws':
            first_time_flag = True
            all_keys = []
            for blob in tqdm(generator):
                object_data = blob.get() #get content of the blob
                payload_dict = json.loads(object_data["Body"].read().decode("utf-8"))
                if first_time_flag: #for setting the column name
                    all_keys = list(payload_dict.keys())
                    all_keys.append('object_put_in_R_Bucket_utc')
                    all_keys.append('bucket_name')
                    payload_list.append(all_keys)
                    first_time_flag=False
                
                temp_list = []
                for key in all_keys: # all keys from the json data
                    if key in ['object_put_in_R_Bucket_utc', 'bucket_name']:
                        continue
                    temp_list.append(payload_dict[key])
                temp_list.append(object_data['LastModified'].isoformat())
                temp_list.append(bucket_name)
                payload_list.append(temp_list)
                
        elif self.platform =='azure':
            first_time_flag = True
            all_keys = []
            for blob in tqdm(generator):
                if azure_folder_filter is not "" and azure_folder_filter in blob.name:
                    object_data = self.service_client.get_blob_to_bytes(bucket_name, blob.name) #get content of the blob
                    print(object_data, blob.name)
                    payload_dict = json.loads(object_data.content.decode('utf-8'))
                    if first_time_flag: #for setting the column name
                        all_keys = list(payload_dict.keys())
                        all_keys.append('object_put_in_R_Bucket_utc')
                        all_keys.append('bucket_name')
                        payload_list.append(all_keys)
                        first_time_flag=False
                    
                    temp_list = []
                    for key in all_keys: # all keys from the json data
                        if key in ['object_put_in_R_Bucket_utc', 'bucket_name']:
                            continue
                        temp_list.append(payload_dict[key])
                    temp_list.append(blob.properties.last_modified.isoformat())
                    temp_list.append(bucket_name)
                    payload_list.append(temp_list)
        
        return pd.DataFrame(payload_list[1:], columns=payload_list[0])













