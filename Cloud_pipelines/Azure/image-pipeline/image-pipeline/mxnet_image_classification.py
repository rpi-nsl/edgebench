#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Apr 28 18:19:42 2019

@author: Anirban Das
"""


from timeit import default_timer as timer
import sys
import os
from .load_model import ImagenetModel
import json
import cv2
import logging
import datetime
import uuid, tempfile
import azure.functions as func

logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize global variables -----------------------------------------------------------
NUM_COMPONENTS = os.getenv('NUM_COMPONENTS', default=2)
container_name = os.getenv('CONTAINER_NAME') #this gives the container name in which the code executes
blob_container_name = "myblobcontainer"
model_path = '{}/{}mxnet_models{}squeezenetv1.1{}'.format(os.path.dirname(os.path.realpath(__file__)), os.sep, os.sep, os.sep)
global_model = ImagenetModel(model_path+'synset.txt', model_path+'squeezenet_v1.1')

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

def mxnet_image_classification(blobin: func.InputStream, blobout: func.Out[bytes], context: func.Context, func_start, N=5, reshape=(224, 224)):
    global blob_container_name
    global container_name
    if global_model is not None:
        try:
            dictionary = {}
            input_image = tempfile.NamedTemporaryFile(delete=False)
            with open(input_image.name, 'wb') as f:
                f.write(blobin.read())
            # Read the image from the folder
            im = cv2.imread(input_image.name)
            height, width, _ = im.shape

            # Predict the classification from the image
            prediction = global_model.predict_from_image(im, reshape, N)

            # Create the Payload JSON with the necessary fields
            for idx, elem in enumerate(prediction):
                temp_dict = {}
                temp_dict["probability"] = float(elem[0])
                temp_dict["wordnetid"], temp_dict["classification"] = elem[1].split(" ", 1)                    
                dictionary["classification_{}".format(idx)] = temp_dict
             
            filename = blobin.name    
            filename = filename.split(os.sep)[-1]
            filename = filename.replace("%3A", ":").replace("%40", "@").replace("%5E", "^")
            status, invocation_count = checkLambdaStatus()
            dictionary["filename"] = str(filename.split('^')[0])
            dictionary["container_name"] = str(container_name)
            dictionary["blob_size"] = str(blobin.length) 
            dictionary["edgeuploadutctime"] = str(filename.split('^')[1] if '^' in filename else "")
            dictionary["invoke_time"] = ""
            dictionary["imagewidth"] = width
            dictionary["imageheight"] = height
            dictionary["func_start"] = func_start
            dictionary["eventTime"] = ""
            dictionary["lambdastatus"] = status
            dictionary["invocation_count"] = invocation_count
            dictionary["funccompleteutctime"] = datetime.datetime.utcnow().isoformat() 
            json_payload = json.dumps(dictionary)
            
            # Output the modified file to a separate folder in the Storage Blob
            blobout.set(json_payload) #write the output to the out file

        except Exception as ex:
            e = sys.exc_info()[0]
            print("Exception occured during prediction: %s" % e)
            print("Exception: %s" % ex)
            sys.exit(0)
