#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 28 14:21:56 2019

@author: Anirban Das
"""

import logging
import azure.functions as func
import datetime
from .audio_translate import getSpeech2Text
import sys, os

sys.path.append("/home/site/wwwroot/audio-pipeline/")

def main(blobin: func.InputStream, blobout: func.Out[bytes], context: func.Context):
    logging.info(f"--- Python blob trigger function processed blob \n"
                 f"----- Name: {blobin.name}\n"
                 f"----- Blob Size: {blobin.length} bytes")
    logging.info(f"""{os.environ}--------{ sys.path}""")
    func_start = datetime.datetime.utcnow().isoformat()
    getSpeech2Text(blobin , blobout, context, func_start)
