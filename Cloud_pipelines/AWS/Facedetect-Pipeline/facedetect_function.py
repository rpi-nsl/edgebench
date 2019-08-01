#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 18 15:09:16 2019

@author: "Anirban Das"
"""

from timeit import default_timer as timer
start_everything_time = timer()
import json , csv
import dlib
import cv2
import sys, os
import datetime
import logging
import tempfile
import uuid


logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
logger = logging.getLogger(__name__)

# Initialize global variables -----------------------------------------------------------
results_bucket = os.getenv('RESULTS_BUCKET')
print(results_bucket)

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

def facedetect(client, event, invoke_time, event_time):

    try:
        func_start = timer()
        status, invocation_count = checkLambdaStatus()
        dictionary = {}
        key, bucket = getKeyBucket(event)
        logger.info("key = {} and bucket = {}".format(key, bucket))

        # Access the image from the S3 bucket
        client.download_file(bucket, key, '/tmp/{}'.format(key))

        img = cv2.imread('/tmp/{}'.format(key))
        height, width = img.shape[0:2]

        dlib_start = timer() # for keeping the time for inference

        detector = dlib.get_frontal_face_detector()

        dets = detector(img, 1)

        dlib_end = timer()

        filename = key #tmp.name
        dictionary["totalcomputetime"] = timer() - func_start
        dictionary["filename"] = filename.split('^')[0]
        dictionary["edgeuploadutctime"] = filename.split('^')[1] if '^' in filename else ""
        dictionary["numfaces"] = len(dets)
        dictionary["imagewidth"] = width
        dictionary["imageheight"] = height
        dictionary["dlib_start"] = dlib_start
        dictionary["dlib_end"] = dlib_end
        dictionary["invoke_time"] = invoke_time
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

        client_upload_stop = timer()

        os.remove('/tmp/{}'.format(key))
        logger.info(msg="Payload: {}".format(json_payload))

    except :
        e = sys.exc_info()[0]
        print("Exception occured during prediction: %s" % e)
        sys.exit(0)
