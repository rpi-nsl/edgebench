#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 8 2018

@author: "Anirban Das"
"""

import boto3
import logging
import time
import json
import os, sys
import datetime
import csv
import random

#set up the global variables
MachineTemperatureMin = 21
MachineTemperatureMax = 100
MachinePressureMin = 1
MachinePressureMax = 10
AmbientTemperature = 21
HumidityPercentMin = 24
HumidityPercentMax = 27

json_data = '''{"machine": {"temperature": "%s","pressure": "%s"},"ambient": {"temperature":"%s","humidity": "%s"},"messagesendutctime": "%s", "messageid":"%s"}'''



STATS_DIRECTORY = "."
# write local stats in a csv file
def write_local_stats(filename, stats_list):
    global STATS_DIRECTORY
    try:
        filepath = STATS_DIRECTORY.rstrip(os.sep) + os.sep + filename
        with open(filepath, 'w') as file:
            writer = csv.writer(file, delimiter=',')
            writer.writerows(stats_list)
    except :
        e = sys.exc_info()[0]
        print("Exception occured during writting Statistics File: %s" % e)        
        #sys.exit(0)

#message generator
def messageGenerator():
    global MachineTemperatureMin
    global MachineTemperatureMax
    global MachinePressureMin
    global MachinePressureMax 
    global AmbientTemperature 
    global HumidityPercentMin 
    global HumidityPercentMax 
    global json_data
    global block_blob_service
    global container_name
    count = 1
    local_stats = [['messageid', 'messagesendutctime', 'payloadsize']]
    try:
        # Set current serrion credentials
        with open('config.json', 'r') as f:
            config = json.load(f)

        current_session = boto3.session.Session(
                    aws_access_key_id = config['AWS_CONFIG']['aws_access_key_id'],
                    aws_secret_access_key = config['AWS_CONFIG']['aws_secret_access_key'],
                    region_name=config['AWS_CONFIG']['region_name'])

        # Set logging level to INFO
        logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)

        # Create an S3 client
        s3_client = current_session.client('s3')

        # Call S3 to list current buckets
        response = s3_client.list_buckets()

        # Get a list of all bucket names from the response
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        logging.info(msg = "Bucket List: {}".format(buckets))

        scalar_bucket = config["SCALAR_BUCKET"]

        # Create a bucket if not present
        if scalar_bucket not in buckets:
            s3_client.create_bucket(
                Bucket= scalar_bucket, 
                # CreateBucketConfiguration={
          #         'LocationConstraint': 'us-west-2'
          #         }
                )
            logging.info("Created S3 bucket : scalar bucket")


        while True:
            json_payload = json_data %(
                                random.uniform(MachineTemperatureMin , MachineTemperatureMax),
                                random.uniform(MachinePressureMin, MachinePressureMax),
                                AmbientTemperature - random.uniform(0, 4),
                                random.uniform(HumidityPercentMin, HumidityPercentMax),
                                datetime.datetime.utcnow().isoformat(),
                                count
                            )
            messagesendutctime = datetime.datetime.utcnow().isoformat()
            
            response = s3_client.put_object(
                            Bucket=scalar_bucket,
                            Body=json_payload,
                            Key="{}.json".format(count),
                            ServerSideEncryption='AES256'
            )
            local_stats.append([count, messagesendutctime, sys.getsizeof(json_payload)])
            print("Payload: {} : {}".format(count,json_payload))
            count = count +1
            if count == 200:
                print("All messages sent")
                break
            else:
                time.sleep(5)
    except KeyboardInterrupt:
        print("cancelling Upload, json uploaded {}".format(count))
        print(e)
    finally:
        write_local_stats("AWS_cloud_scalar_local_stats_{}.csv".format(str(datetime.datetime.now().date())), local_stats)


# Main method.
if __name__ == '__main__':
    #upload_all_files('/home/{}/Pictures/Samples'.format(user))
    messageGenerator()
