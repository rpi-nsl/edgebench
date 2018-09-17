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

	audio_bucket = config["AUDIO_BUCKET"]

	# Create a bucket if not present
	if audio_bucket not in buckets:
		s3_client.create_bucket(
			Bucket= audio_bucket, 
			# CreateBucketConfiguration={
	  #       	'LocationConstraint': 'us-west-2'
	  #   		}
	    	)
		logging.info("Created S3 bucket : test_audio")


	folder_path = config["FOLDER_PATH"]
	count = 1

	local_stats = [['audiofilename', 'messagesendutctime', 'payloadsize']]
	allfiles = sorted(os.listdir(folder_path))
	for file_name in allfiles:
		file_path = folder_path + os.sep + file_name
		s3_client.upload_file(file_path, audio_bucket, file_name)
		logging.info(msg="{} : Uploaded file: {}".format(count, file_name))
		local_stats.append([file_name, datetime.datetime.utcnow().isoformat(), os.path.getsize(file_path)])

		time.sleep(5)
		count  = count + 1
except KeyboardInterrupt:
	print("cancelling Upload, audios uploaded {}".format(count))
finally:
	write_local_stats("AWS_audio_local_stats_central{}.csv".format(str(datetime.datetime.now().date())), local_stats)