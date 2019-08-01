
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 26 01:32:44 2019

@author: Anirban Das
"""

import json
import datetime
import boto3
import os
import logging
import uuid
import tempfile

s3_client = boto3.client('s3')
logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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
    event_time = record['eventTime']
    bucket = record['s3']['bucket']['name']
    key = record['s3']['object']['key']
    key = key.replace("%3A", ":")
    key = key.replace("%3A", ":")
    key = key.replace("%40", "@")
    key = key.replace("%5E", "^")
    return key, bucket, event_time

def function_handler(event, context):
    global s3_client
    dictionary = {}
    func_start = datetime.datetime.utcnow().isoformat()
    key, bucket, event_time = getKeyBucket(event)

    logger.info("key = {} and bucket = {}".format(key, bucket))

    # Access the scalar file from the S3 bucket
    s3_client.download_file(bucket, key, '/tmp/{}'.format(key))

    filename = key
    status, invocation_count = checkLambdaStatus()
    dictionary["filename"] = str(filename.split('^')[0])
    dictionary["edgeuploadutctime"] = str(filename.split('^')[1] if '^' in filename else "")
    dictionary["invoke_time"] = str(func_start)
    dictionary["func_start"] = str(func_start)
    dictionary["eventTime"] = str(event_time)
    dictionary["lambdastatus"] = str(status)
    dictionary["invocation_count"] = str(invocation_count)
    dictionary["funccompleteutctime"] = str(datetime.datetime.utcnow().isoformat())
    dictionary["temperature_value"] = str(open('/tmp/{}'.format(key), 'r').readlines())
    json_payload = json.dumps(dictionary)

    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(json_payload)
        tmp.flush()
        s3_client.upload_file(tmp.name, results_bucket, "{}.json".format(key))

    os.remove('/tmp/{}'.format(key))
    logger.info(msg="Payload: {}".format(json_payload))

    # with open('/tmp/{}'.format(key), 'r') as f:
    #     lines = f.readlines()
    #     response = s3_client.put_object(
    #         Bucket=results_bucket,
    #         Body=json.dumps(lines),
    #         Key=key,
    #         ServerSideEncryption='AES256',
    #         Metadata=dictionary
    #         )
    # return {
    #     "statusCode": 200,
    #     "body": json.dumps('Hello from Lambda! {}'.format(response))
    # }
