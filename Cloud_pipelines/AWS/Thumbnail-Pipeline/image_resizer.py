#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on  Feb 11 2019

@author: "Anirban Das"
"""
import sys
import os
import json
from io import BytesIO
import logging
import datetime
from PIL import Image


logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

results_bucket = os.getenv('RESULTS_BUCKET')
print(results_bucket)
if "THUMBNAIL_SIZE" in os.environ:
    thumbnail_size = int(os.environ["THUMBNAIL_SIZE"]), int(os.environ["THUMBNAIL_SIZE"])
else:
    thumbnail_size = 128, 128

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

def image_resizer(client, event, invoke_time, event_time):
    # try:
    global thumbnail_size
    global results_bucket
    func_start = invoke_time
    dictionary = {}
    key, bucket = getKeyBucket(event)
    keyname = key.split('^')[0]
    extension = os.path.splitext(keyname)[1].lower()

    # Set buffer format for image saving
    if extension in ['.jpeg', '.jpg']:
        format = 'JPEG'
    if extension in ['.png']:
        format = 'PNG'

    logger.info("key = {} and bucket = {}".format(key, bucket))

    obj = client.get_object(Bucket=bucket, Key=key)
    object_content = obj['Body'].read()

    # Creating thumbnail of the image
    img = Image.open(BytesIO(object_content))
    height, width = img.size
    img = img.resize(thumbnail_size, Image.LANCZOS)

    # Save in buffer as bytes type object for uploading to S3
    buffer = BytesIO()
    img.save(buffer, format)
    buffer.seek(0)

    # Create the Payload JSON with the necessary fields
    filename = key #tmp.name
    status, invocation_count = checkLambdaStatus()
    dictionary["filename"] = filename.split('^')[0]
    dictionary["edgeuploadutctime"] = filename.split('^')[1] if '^' in filename else ""
    dictionary["imagewidth"] = str(width)
    dictionary["imageheight"] = str(height)
    dictionary["invoke_time"] = invoke_time
    dictionary["func_start"] = str(func_start)
    dictionary["eventTime"] = event_time
    dictionary["lambdastatus"] = str(status)
    dictionary["invocation_count"] = str(invocation_count)
    dictionary["funccompleteutctime"] = datetime.datetime.utcnow().isoformat()
    json_payload = json.dumps(dictionary)
    client.upload_fileobj(buffer, results_bucket, key, ExtraArgs={"Metadata":dictionary})
    # except:
    #     e = sys.exc_info()[0]
    #     print("Exception occured during resizing: %s" % e)
