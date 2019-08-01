#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb 24 14:34:12 2019

@author: "Anirban Das"
"""

#import greengrasssdk
import logging
import boto3
from image_resizer import image_resizer

logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
#client = greengrasssdk.client('iot-data')

s3_client = boto3.client('s3')

image_resizer(s3_client)

# Dummy Handler
def lambda_handler(event, context):
	return