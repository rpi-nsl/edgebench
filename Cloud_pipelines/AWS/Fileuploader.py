#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May  2 13:03:42 2019

@author: "Anirban Das"
@co-author: "Tobias Park"
"""

import os
import sys
import datetime
import csv
import time
import uuid
import traceback
import pickle
import requests


class AWS:
    def initBucket(self, bucket_name="test_bucket_{}".format(uuid.uuid4()), aws_access_key_id="", aws_secret_access_key="", aws_region_name="none-specified"):
        import boto3
        if aws_region_name == "none-specified":
            aws_region_name = boto3.Session().region_name

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

    def cleanupBucket(self, bucket_name):
        try:
            from boto.s3.connection import S3Connection, Bucket, Key
            conn = S3Connection()
            b = Bucket(conn, bucket_name)
            for x in b.list():
                b.delete_key(x.key)
            b.delete()
        except:
            pass # bucket must already be removed

class S3(AWS):
    def initialize(self, **kwargs):
        self.service_client, self.bucket = self.initBucket(**kwargs)

    def upload(self, file_path, count, file_name):
        self.service_client.upload_file(file_path, self.bucket, file_name)

    def cleanup(self):
        self.cleanupBucket(self.bucket)

class Gateway(AWS):
    def __init__(self):
        import boto3
        self.region = boto3.Session().region_name
        self.gateway_client = boto3.client('apigateway')
        self.iam_client = boto3.client('iam')

    def cleanup(self):
        self.cleanupBucket(self.bucket)
        self.rollback('none', '', '', '')

    def initialize(self, **kwargs):
        from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
        import boto3

        self.service_client, self.bucket = self.initBucket(**kwargs)
        self.region = boto3.Session().region_name
        self.gateway_client = boto3.client('apigateway')
        self.iam_client = boto3.client('iam')
        # use get_rest_apis to get list of API's and save list as list; for x in list['items'], check x['name']
        # for 'edgebench-api'. If found, self.api_url = x['id'] and re-generate the invoke_url. If not, run the creation script and save url
        # as self.api_url and pickle the data.
        list = self.gateway_client.get_rest_apis()
        found = False
        for x in list['items']:
            if x['name'] == 'edgebench-api':
                self.api_id = x['id']
                found = True
                print("Found API...")
                break
        if not found:
            print("Creating API...")
            self.createAPI()

        self.invoke_url = "https://" + self.api_id + ".execute-api." + self.region + ".amazonaws.com/Prod/" + self.bucket + "/"
        # taken from https://stackoverflow.com/questions/39352648/access-aws-api-gateway-with-iam-roles-from-python
        # create authentication variable so API calls will go through
        self.auth = BotoAWSRequestsAuth(
                       aws_host=self.api_id + '.execute-api.' + self.region + '.amazonaws.com',
                       aws_region=self.region,
                       aws_service='execute-api')

    def upload(self, file_path, count, file_name):
        self.upload_file(file_path, count, file_name, 0)

    def upload_file(self, file_path, count, file_name, errors):
        # helper function for upload;
        # needed because of the unique "errors" variable which keeps track of how many retries we have attempted for this file
        file = open(file_path, 'rb')
        data = file.read()
        from magic import from_file
        headers = {'Content-Type': from_file(file_path, mime=True)}
        response = requests.put(self.invoke_url + file_name, auth=self.auth, data=data, headers=headers) # have to chop off the timestamp at the end because it contains characters that are unsupported by Gateway
        try:
            response.raise_for_status() # throw exception if there was an API error
        except:
            # sometimes, especially right after API is deployed, upload will randomly fail for no reason. Retry up to 3 times...
            errors = errors + 1
            if errors <= 3:
                print("Upload failed. Trying again...")
                self.upload_file(file_path, count, file_name, errors)
            else:
                print("Error: Upload failed 3 times. Aborting... ")
                response.raise_for_status()
                quit()

    def rollback(self, error, arn1, arn2, api):
        if error != "none":
            print(error)
            print("An error has occured! Rolling back...")
        else:
            try:
                file = open('.edgebench_api_data', 'rb')
                dict = pickle.load(file)
                file.close()
                arn1 = dict['temp_arn_1']
                arn2 = dict['temp_arn_2']
                api = dict['api_id']
            except:
                pass

        print("Removing upload API (if it exists)...")
        # delete the API and the created roles, if they exist
        try:
            self.iam_client.detach_role_policy(RoleName="edgebench-api", PolicyArn="arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess")
            self.iam_client.detach_role_policy(RoleName="edgebench-api", PolicyArn="arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs")
            self.iam_client.detach_role_policy(RoleName="edgebench-api", PolicyArn=arn1)
            self.iam_client.detach_role_policy(RoleName="edgebench-api", PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess")
            self.iam_client.detach_role_policy(RoleName="edgebench-api", PolicyArn=arn2)
        except:
            pass
        try:
            self.iam_client.delete_role(RoleName="edgebench-api")
            self.iam_client.delete_policy(PolicyArn=arn1)
            self.iam_client.delete_policy(PolicyArn=arn2)
            self.gateway_client.delete_rest_api(restApiId=api)
        except:
            pass
        if error != "none":
            print("API deleted, rollback successful. Program wil now exit.")
            quit()

    def createAPI(self):
        import boto3
        temp_arn_1 = ""
        temp_arn_2 = ""
        # initialize gateway and iam clients


        try:
            # create an IAM role named edgebench-api with a trust policy:
            role_arn = self.iam_client.create_role(RoleName='edgebench-api', AssumeRolePolicyDocument='''{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "apigateway.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
} ''')['Role']['Arn']
            iam = boto3.resource('iam')
            role = iam.Role('edgebench-api')

            # attach AmazonS3ReadOnlyAccess
            role.attach_policy(PolicyArn="arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess")

            # attach AmazonAPIGatewayPushToCloudWatchLogs
            role.attach_policy(PolicyArn="arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs")

            # create and attach custom policy #1
            temp_arn_1 = self.iam_client.create_policy(PolicyName="edgebench-gatewayrole-put", PolicyDocument='''{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:Put*",
            "Resource": "*"
        }
    ]
}
    ''')['Policy']['Arn']
            role.attach_policy(PolicyArn=temp_arn_1)

            # attach policy AmazonS3FullAccess
            role.attach_policy(PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess")

            # create and attach custom policy #2
            temp_arn_2 = self.iam_client.create_policy(PolicyName='edgebench-gatewayrole-post', PolicyDocument='''{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:Post*",
            "Resource": "*"
        }
    ]
}
    ''')['Policy']['Arn']
            role.attach_policy(PolicyArn=temp_arn_2)

            # create api
            api_id = self.gateway_client.create_rest_api(name="edgebench-api", binaryMediaTypes=['image/jpg', 'image/jpeg', 'audio/wav', 'audio/x-wav'])['id']

            # create Folder resource
            items = self.gateway_client.get_resources(restApiId=api_id)['items']
            resource_id = ""
            for item in items:
                if item['path'] == '/':
                    resource_id = item['id']
            self.gateway_client.create_resource(restApiId=api_id, parentId=resource_id, pathPart="{folder}")

            # create Item resource
            items = self.gateway_client.get_resources(restApiId=api_id)['items']
            resource_id = ""
            for item in items:
                if item['path'] == '/{folder}':
                    resource_id = item['id']
            self.gateway_client.create_resource(restApiId=api_id, parentId=resource_id, pathPart="{item}")

            # create and configure PUT method on {folder}/{item}
            items = self.gateway_client.get_resources(restApiId=api_id)['items']
            resource_id = ""
            for item in items:
                if item['path'] == '/{folder}/{item}':
                    resource_id = item['id']
            self.gateway_client.put_method(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", authorizationType="AWS_IAM", requestParameters={'method.request.header.Accept': False, 'method.request.header.Content-Type': False, 'method.request.path.folder': True, 'method.request.path.item': True})
            self.gateway_client.put_integration(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", type='AWS', uri="arn:aws:apigateway:" + self.region + ":s3:path/{bucket}/{object}", integrationHttpMethod="PUT", credentials=role_arn, requestParameters={'integration.request.header.Accept': 'method.request.header.Accept', 'integration.request.header.Content-Type': 'method.request.header.Content-Type', 'integration.request.header.x-amz-acl': "'authenticated-read'", 'integration.request.path.bucket': 'method.request.path.folder', 'integration.request.path.object': 'method.request.path.item'}, requestTemplates={'audio/wav': '', 'image/jpeg': '', 'image/jpg': '', 'text/plain': ''}, passthroughBehavior='WHEN_NO_MATCH')
            self.gateway_client.put_method_response(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", statusCode='200', responseModels={'application/json':'Empty'})
            self.gateway_client.put_method_response(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", statusCode='400', responseModels={'application/json':'Empty'})
            self.gateway_client.put_method_response(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", statusCode='500', responseModels={'application/json':'Empty'})
            self.gateway_client.put_integration_response(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", statusCode='200', selectionPattern='')
            self.gateway_client.put_integration_response(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", statusCode='400', selectionPattern='4\\d{2}')
            self.gateway_client.put_integration_response(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", statusCode='500', selectionPattern='5\\d{2}')

            # deploy the API
            self.gateway_client.create_deployment(restApiId=api_id, stageName="Prod")


            # pickle the ARNs of the created resources
            data_to_save = {'temp_arn_1': temp_arn_1, 'temp_arn_2': temp_arn_2, "api_id": api_id}
            file = open('.edgebench_api_data', 'wb')
            pickle.dump(data_to_save, file)

            self.api_id = api_id

            from tqdm import tqdm
            print("Waiting to ensure that API fully deploys (this will take a while)...")
            time.sleep(120)


        except:
            self.rollback(traceback.format_exc(), temp_arn_1, temp_arn_2, api_id)


# AZURE IMPLEMENTATION (NOT YET TESTED):
# class Azure:
#     def initialize(self, **kwargs):
#         from azure.storage.blob import BlockBlobService
#         if 'azure_storage_account_key' not in kwargs or 'azure_storage_account_name' not in kwargs:
#             print("\nYou need to give both azure storage account name and key to access container services:")
#             print("""Sample Command: uploader_azure = Fileuploader(application='audio', platform='azure', stats_folder='./', input_folder='./',
#                                                     azure_storage_account_name="<acc_name>",
#                                                     azure_storage_account_key="<acc_key>",
#                                                     bucket_name="<bucket_name/container_name>")""")
#             raise ValueError("Invalid Arguments in class creation")
#         return self.setup(self, **kwargs)
#
#     def setup(self, bucket_name="test_bucket_{}".format(uuid.uuid4()), aws_access_key_id="", aws_secret_access_key="", aws_region_name="us-east-1"):
#         block_blob_service = BlockBlobService(account_name=azure_storage_account_name,
#                                               account_key=azure_storage_account_key)
#         container_name = bucket_name
#         # Create container if it not present
#         exists = block_blob_service.create_container(container_name)
#         if not exists:
#             print("Container {} already exists".format(container_name))
#         else:
#             print("Created container {}".format(container_name))
#         self.service_client = block_blob_service
#         self.bucket = container_name
#
#     def upload(self, file_path, count, file_name):
#         self.service_client.create_blob_from_path(self.bucket, file_name, file_path)

class serviceFactory:
    def createServiceObject(self, platform):
        if platform == 's3' or platform == 'aws':
            return S3()
        elif platform == 'gateway':
            return Gateway()
        elif platform == 'azure':
            return Azure()
        else:
            print("Error: Invalid upload method specified.")
            quit()

class FileUploader(object):
    def __init__(self, platform, application, stats_folder, **kwargs):
        self.platform = platform.lower()
        self.application = application.lower()
        self.stats_folder = stats_folder
        service_factory = serviceFactory()
        self.service_object = service_factory.createServiceObject(platform)
        self.service_object.initialize(**kwargs)

    def batch_upload_files(self, folder_path, delay=1):
        all_details = []
        try:
            for count, file in enumerate(sorted(os.listdir(folder_path))):
                file_path = os.path.join(folder_path, file)
                print("Uploading {}".format(file_path))
                status, details_list = self.upload_file(file_path=file_path, count=count)
                all_details.append(details_list)
                time.sleep(delay)
            return all_details
        except Exception as e:
            print("Exception in uploading: {}".format(e))
            return [["", "", "", ""]]

    def upload_file(self, file_path=None, count=0):
        try:
            upload_start_utc_timestamp = datetime.datetime.utcnow().isoformat()
            file_name = file_path.split(os.sep)[-1]+"^{}".format(datetime.datetime.utcnow().isoformat())
            self.service_object.upload(file_path, count, file_name)
            size = os.path.getsize(file_path)
            upload_stop_utc_timestamp = datetime.datetime.utcnow().isoformat()
            return True , [file_name, upload_start_utc_timestamp, upload_stop_utc_timestamp, size]
        except Exception as e:
            print("Exception in uploading: {}".format(e))
            return False, ["", "", "", ""]

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

    # clean up everything that was created during upload procedure
    def cleanup(self):
        self.service_object.cleanup()
