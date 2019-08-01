#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 18 15:58:20 2019

@author: "Anirban Das"
"""

import greengrasssdk
import logging
from facedetect_function import facedetect

logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
client = greengrasssdk.client('iot-data')

# get the audio translations
facedetect(client)

# Dummy Handler
def lambda_handler(event, context):
	return