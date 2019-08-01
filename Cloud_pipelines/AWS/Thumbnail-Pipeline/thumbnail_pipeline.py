#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on  Feb 11 2019

@author: "Anirban Das"
"""
import datetime
import boto3
from image_resizer import image_resizer

s3_client = boto3.client('s3')

def function_handler(event, context):
    record = event['Records'][0]
    event_time = record['eventTime']
    invoke_time = datetime.datetime.utcnow().isoformat()
    print('Got event{}'.format(event))
    image_resizer(s3_client, event, invoke_time, event_time)
    return
