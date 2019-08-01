#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 29 12:10:48 2019

@author: Anirban Das
"""

import os
import greengrasssdk
import datetime
import sys, logging
from audio_translate import getSpeech2Text


logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
client = greengrasssdk.client('iot-data')

# get the audio translations
getSpeech2Text(client)

# Dummy Handler
def lambda_handler(event, context):
	return
