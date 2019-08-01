#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thursday Apr 25 13:00:14 2019

@author: "Anirban Das"
"""
from timeit import default_timer as timer
import os
from pocketsphinx import Pocketsphinx, get_model_path, get_data_path, AudioFile
import json, csv
import datetime
import sys, logging
import tempfile
import uuid

logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
logger = logging.getLogger(__name__)

results_bucket = os.getenv('RESULTS_BUCKET')

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

# Initiates and returns a pocket sphinx decoder
def getPockerSphinxDecoder():
    model_path = get_model_path()
    data_path = get_data_path()
    config = {
        'verbose': False,
        'hmm': os.path.join(model_path, 'en-us'),
        'lm': os.path.join(model_path, 'en-us.lm.bin'),
        'dict': os.path.join(model_path, 'cmudict-en-us.dict'),
        # 'topn': 2,
        # 'ds':2,
        # 'maxwpf': 5,
        # 'maxhmmpf': 3000
    }
    return Pocketsphinx(**config)

def getKeyBucket(event):
    record = event['Records'][0]
    bucket = record['s3']['bucket']['name']
    key = record['s3']['object']['key']
    key = key.replace("%3A", ":")
    key = key.replace("%3A", ":")
    key = key.replace("%40", "@")
    key = key.replace("%5E", "^")
    return key, bucket

# Code for doing the actual speech 2 text conversion
def getSpeech2Text(client, event, invoke_time, event_time):

    #try:
    func_start = invoke_time
    dictionary = {}
    key, bucket = getKeyBucket(event)
    print("key = {} and bucket = {}".format(key, bucket))

    client.download_file(bucket, key, '/tmp/{}'.format(key))
    ps_decoder = getPockerSphinxDecoder()
    ps_decoder.decode(audio_file='/tmp/{}'.format(key),
                    buffer_size=2048,
                no_search=False,
                full_utt=False)

    translation = ps_decoder.hypothesis()

    filename = key #tmp.name
    status, invocation_count = checkLambdaStatus()
    dictionary["filename"] = filename.split('^')[0]
    dictionary["edgeuploadutctime"] = filename.split('^')[1] if '^' in filename else ""
    dictionary["translation"] = translation
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

    os.remove('/tmp/{}'.format(key))
    logger.info(msg="Payload: {}".format(json_payload))
    # except :
    #     e = sys.exc_info()[0]
    #     print("Exception occured during prediction: %s" % e)
    #     sys.exit(0)
