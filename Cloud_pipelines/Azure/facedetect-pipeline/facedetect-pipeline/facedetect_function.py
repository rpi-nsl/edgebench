#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 18 15:09:16 2019

@author: "Anirban Das"
"""

from timeit import default_timer as timer
import json
import dlib
from PIL import Image
import sys, os
import datetime
import logging
import uuid
import numpy as np
import azure.functions as func

logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
logger = logging.getLogger(__name__)

# Initialize global variables -----------------------------------------------------------
NUM_COMPONENTS = os.getenv('NUM_COMPONENTS', default=2)
container_name = os.getenv('CONTAINER_NAME') #this gives the container name in which the code executes
blob_container_name = "myblobcontainer"

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

def facedetect(blobin: func.InputStream, blobout: func.Out[bytes], context: func.Context, func_start):
    global blob_container_name
    global container_name
    # try:
    dictionary = {}
    input_image = blobin

    img = np.array(Image.open(input_image))#cv2.imread(input_image.read())
    height, width, _ = img.shape
    
    dlib_start = timer()

    detector = dlib.get_frontal_face_detector()
    
    dets = detector(img, 1)
    
    dlib_end = timer()

    status, invocation_count = checkLambdaStatus()
    filename = blobin.name    
    filename = filename.split(os.sep)[-1]
    filename = filename.replace("%3A", ":")
    filename = filename.replace("%40", "@")
    filename = filename.replace("%5E", "^")
    dictionary["filename"] = str(filename.split('^')[0])
    dictionary["edgeuploadutctime"] = str(filename.split('^')[1] if '^' in filename else "")
    dictionary["numfaces"] = len(dets)
    dictionary["inputblobsize"] = str(blobin.length)        
    dictionary["imagewidth"] = width
    dictionary["imageheight"] = height
    dictionary["dlib_start"] = dlib_start
    dictionary["dlib_end"] = dlib_end
    dictionary["func_start"] = func_start
    dictionary["lambdastatus"] = str(status)
    dictionary["invocation_count"] = str(invocation_count)
    dictionary["container_name"] = str(container_name)
    dictionary["funccompleteutctime"] = datetime.datetime.utcnow().isoformat()
    json_payload = json.dumps(dictionary)

    blobout.set(json_payload) #write the output to the out file
