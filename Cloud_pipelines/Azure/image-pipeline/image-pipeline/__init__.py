#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Apr 28 18:19:42 2019

@author: Anirban Das
"""


import logging
import azure.functions as func
import datetime
import sys, os

from .mxnet_image_classification import mxnet_image_classification

def main(blobin: func.InputStream, blobout: func.Out[bytes], context: func.Context):
    logging.info(f"--- Python blob trigger function processed blob \n"
                 f"----- Name: {blobin.name}\n"
                 f"----- Blob Size: {blobin.length} bytes")
    
    logging.info(f"""{os.environ}--------{ sys.path}""")    
    func_start = datetime.datetime.utcnow().isoformat()
    mxnet_image_classification(blobin , blobout, context, func_start)
