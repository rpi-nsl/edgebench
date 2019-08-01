#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thursday Apr 25 16:45:28 2019

@author: "Anirban Das"
"""

from timeit import default_timer as timer
time_start_read1 = timer()
import os
import load_model
import json
import cv2
import tempfile
import logging
import datetime
import uuid


logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

results_bucket = os.getenv('RESULTS_BUCKET')
print(results_bucket)

model_path = '.{}mxnet_models{}squeezenetv1.1{}'.format(os.sep, os.sep, os.sep)
global_model = load_model.ImagenetModel(model_path+'synset.txt', model_path+'squeezenet_v1.1')
logger.info("Entering classification")
print("loaded model in {}".format(timer()- time_start_read1))

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

def getKeyBucket(event):
    record = event['Records'][0]
    bucket = record['s3']['bucket']['name']
    key = record['s3']['object']['key']
    key = key.replace("%3A", ":")
    key = key.replace("%3A", ":")
    key = key.replace("%40", "@")
    key = key.replace("%5E", "^")
    return key, bucket


def mxnet_image_classification(client, event, invoke_time, event_time, N=5, reshape=(224, 224)):
    if global_model is not None:
        try:
            func_start = invoke_time
            dictionary = {}
            key, bucket = getKeyBucket(event)
            logger.info("key = {} and bucket = {}".format(key, bucket))
            
            # Access the image from the S3 bucket
            client.download_file(bucket, key, '/tmp/{}'.format(key))

            # Read the image from the folder
            im = cv2.imread('/tmp/{}'.format(key))
            height, width, _ = im.shape
            
            # Predict the classification from the image
            prediction = global_model.predict_from_image(im, reshape, N)
            
            # Create the Payload JSON with the necessary fields
            for idx, elem in enumerate(prediction):
                temp_dict = {}
                temp_dict["probability"] = float(elem[0])
                temp_dict["wordnetid"], temp_dict["classification"] = elem[1].split(" ", 1)                    
                dictionary["classification_{}".format(idx)] = temp_dict
            
            filename = key
            status, invocation_count = checkLambdaStatus()
            dictionary["filename"] = filename.split('^')[0]
            dictionary["edgeuploadutctime"] = filename.split('^')[1] if '^' in filename else ""
            dictionary["invoke_time"] = invoke_time
            dictionary["imagewidth"] = width
            dictionary["imageheight"] = height
            dictionary["func_start"] = func_start
            dictionary["eventTime"] = event_time
            dictionary["lambdastatus"] = status
            dictionary["invocation_count"] = invocation_count
            dictionary["funccompleteutctime"] = datetime.datetime.utcnow().isoformat()
            json_payload = json.dumps(dictionary)
            
            with tempfile.NamedTemporaryFile() as tmp:
                tmp.write(json_payload)
                tmp.flush()
                client.upload_file(tmp.name, results_bucket, "{}.json".format(key))
            
            os.remove('/tmp/{}'.format(key))
            logger.info(msg="Payload: {}".format(json_payload))
        except:
            e = sys.exc_info()[0]
            print("Exception occured during prediction: %s" % e)