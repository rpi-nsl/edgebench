#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 23 18:39:39 2019

@author: Anirban Das
"""

import logging, json
import azure.functions as func
from io import BytesIO
import sys, os
import datetime
from PIL import Image
from timeit import default_timer as timer
from azure.storage.blob import BlockBlobService, PublicAccess
import uuid

logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
logger = logging.getLogger(__name__)

# Initialize global variables -----------------------------------------------------------
thumbnail_size = int(os.getenv('THUMBNAIL_SIZE', default=128)), int(os.getenv('THUMBNAIL_SIZE', default=128))
container_name = os.getenv('CONTAINER_NAME') #this gives the container name in which the code executes
blob_container_name = "myblobcontainer"

block_blob_service = BlockBlobService(account_name='edgebench8561', 
                account_key='0i7buxxEJ8gMW3XcMu11JBNcZllkJGdm3UkHuy24Sxj+x1iQv7bf62SKJwSBiYIZ/xhjp9zXkf3yfWtgfud1oA==')
#block_blob_service.create_container(container_name)

def checkLambdaStatus():
    if os.path.isfile("/tmp/perf_det.txt"):
        with open("/tmp/perf_det.txt", "r+") as out:
            line = out.readline()
            line = line.strip()
            uuid_val = line.split('|')[0].split('^')[-1]
            modified_time = line.split('|')[1].split('^')[-1]
            invocation_count = int(line.split('|')[2].split('^')[-1].strip()) +1
            out.seek(0)
            out.write("uuid^{}|modified_time^{}|invocation_count^{}".format(uuid_val,datetime.datetime.utcnow().isoformat(), invocation_count))
            out.truncate()
        return 'warm', invocation_count
    else:
        try:
            uuid_val = str(uuid.uuid4())
            with open("/tmp/perf_det.txt", "w") as out:
                out.write("uuid^{}|modified_time^{}|invocation_count^{}".format(uuid_val, datetime.datetime.utcnow().isoformat(), 1))
        except:
            pass
        return 'cold', 1

def image_resizer(blobin: func.InputStream, blobout: func.Out[bytes], context: func.Context, func_start):
    global thumbnail_size
    global blob_container_name
    global container_name
    dictionary = {}
    # Pillow calls blobin.read() so its a byte object
    # Image.open will work but cv2.Imread won't
    input_image = blobin
    filename = blobin.name    
    filename = filename.split(os.sep)[-1]
    filename = filename.replace("%3A", ":")
    filename = filename.replace("%40", "@")
    filename = filename.replace("%5E", "^")
    extension = os.path.splitext(filename.split('^')[0])[1].lower()
    
    # Set buffer format for image saving
    if extension in ['.jpeg', '.jpg']:
        format = 'JPEG'
    if extension in ['.png']:
        format = 'PNG'
    
    # Creating thumbnail of the image
    img = Image.open(input_image)
    height, width = img.size
    img = img.resize(thumbnail_size, Image.LANCZOS)
    
    # Save in buffer as bytes type object for uploading to S3    
    buffer = BytesIO()
    img.save(buffer, format)
    buffer.seek(0)
    
    # Create the Payload JSON with the necessary fields
    status, invocation_count = checkLambdaStatus()
    dictionary["filename"] = str(filename.split('^')[0])
    dictionary["edgeuploadutctime"] = str(filename.split('^')[1] if '^' in filename else "")
    dictionary["inputblobsize"] = str(blobin.length)        
    dictionary["imagewidth"] = str(width)
    dictionary["imageheight"] = str(height)
    dictionary["func_start"] = str(func_start)
    dictionary["inputblobsize"] = str(blobin.length)
    dictionary["lambdastatus"] = str(status)
    dictionary["invocation_count"] = str(invocation_count)
    dictionary["container_name"] = str(container_name)
    dictionary["funccompleteutctime"] = datetime.datetime.utcnow().isoformat()
    json_payload = json.dumps(dictionary)
    print(json_payload)
    # block_blob_service.create_blob_from_stream(container_name, 
    #                                 "{}^{}".format(filename, datetime.datetime.utcnow().isoformat()), buffer, metadata=dictionary)
    block_blob_service.create_blob_from_stream(blob_container_name, filename, buffer, metadata=dictionary)
    print("FINISH")