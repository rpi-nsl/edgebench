#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 22 18:42:17 2019

@author: "Anirban Das"
"""

#import greengrasssdk
import logging
import boto3
from pythonpca import pythonpca

logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
#client = greengrasssdk.client('iot-data')

s3_client = boto3.client('s3')

pythonpca(s3_client)

# Dummy Handler
def lambda_handler(event, context):
	return