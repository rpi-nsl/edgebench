#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thursday Apr 25 16:45:28 2019

@author: "Anirban Das"
"""

import boto3
import datetime
from mxnet_image_classification import mxnet_image_classification

# Create an S3 client
s3_client = boto3.client('s3')

def function_handler(event, context):
	invoke_time = datetime.datetime.utcnow().isoformat()
	record = event['Records'][0]
	event_time = record['eventTime']
	print('Got event{}'.format(event))
	mxnet_image_classification(s3_client, event, invoke_time, event_time,)
	return