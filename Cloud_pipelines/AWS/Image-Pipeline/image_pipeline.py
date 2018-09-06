#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 21 20:00:04 2018

@author: "Anirban Das"
"""

import sys
import time
import platform
import os
import boto3
import logging , json
from mxnet_image_classification import mxnet_image_classification


# Set current session credentials
with open('config.json', 'r') as f:
	config = json.load(f)

current_session = boto3.session.Session(
			aws_access_key_id = config['AWS_CONFIG']['aws_access_key_id'],
			aws_secret_access_key = config['AWS_CONFIG']['aws_secret_access_key'],
			region_name=config['AWS_CONFIG']['region_name'])

# Create an S3 client
s3_client = current_session.client('s3')

def function_handler(event, context):
	print('Got event{}'.format(event))
	mxnet_image_classification(s3_client, event)
	return