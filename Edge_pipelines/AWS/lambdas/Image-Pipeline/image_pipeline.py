#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 21 13:58:02 2018

@author: Anirban Das
"""
import greengrasssdk
import logging 
from mxnet_image_classification import mxnet_image_classification


logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
client = greengrasssdk.client('iot-data')
print("Setting up greengrass client")


mxnet_image_classification(client, outputQueueName='greengrass/image_pipeline')

# Placeholder Lambda Dummy doesnot do anything
def lambda_handler(event, context):
    return 'Hello from Lambda Image Pipeline'
