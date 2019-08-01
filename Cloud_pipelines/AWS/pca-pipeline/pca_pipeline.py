#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 22 18:42:17 2019

@author: "Anirban Das"
"""

import datetime
import boto3
from pythonpca import pythonpca


s3_client = boto3.client('s3')

# Dummy Handler
def function_handler(event, context):
	invoke_time = datetime.datetime.utcnow().isoformat()
	record = event['Records'][0]
	event_time = record['eventTime']
	print('Got event{}'.format(event))
	pythonpca(s3_client, event, invoke_time, event_time)
	return