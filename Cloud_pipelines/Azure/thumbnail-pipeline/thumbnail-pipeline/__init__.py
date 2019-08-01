#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 14:27:04 2019

@author: Anirban Das
"""

import logging
import azure.functions as func
import datetime
from .image_resizer import image_resizer

def main(blobin: func.InputStream, blobout: func.Out[bytes], context: func.Context):
    logging.info(f"--- Python blob trigger function processed blob \n"
                 f"----- Name: {blobin.name}\n"
                 f"----- Blob Size: {blobin.length} bytes")
    
    func_start = datetime.datetime.utcnow().isoformat()
    image_resizer(blobin , blobout, context, func_start)