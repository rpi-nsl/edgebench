#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 21 20:00:14 2018

@author: "Anirban Das"
"""

import os
import json 
import sys, logging
import boto3
import platform
from audio_translate import getSpeech2Text


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
	getSpeech2Text(s3_client, event)
	return
