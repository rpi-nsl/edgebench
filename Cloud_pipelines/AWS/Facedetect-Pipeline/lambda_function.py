#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 22 20:00:35 2019

@author: "Anirban Das"
"""
import datetime
import boto3
from facedetect_function import facedetect

s3_client = boto3.client('s3')

def function_handler(event, context):
    invoke_time = datetime.datetime.utcnow().isoformat()
    record = event['Records'][0]
    event_time = record['eventTime']
    print('Got event{}'.format(event))
    facedetect(s3_client, event, invoke_time, event_time)
    return
