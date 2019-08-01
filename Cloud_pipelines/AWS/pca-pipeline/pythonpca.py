#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 22 18:36:43 2019

@author: "Anirban Das"
"""

import os, sys
from timeit import default_timer as timer
import datetime 
import pickle
import json , csv
import numpy as np


# Initialize global variables -----------------------------------------------------------
NUM_COMPONENTS = int(os.getenv('NUM_COMPONENTS', default=2))
results_bucket = os.getenv('RESULTS_BUCKET')

csvfilename = "Matrixpca_stats_local_{}_{}.csv".format(str(datetime.datetime.now().date()), "AWS")



def PCA(input_data, n_components = 2):
    centered_data = input_data - input_data.mean(axis=0)
    eigenValues, eigenVectors = np.linalg.eigh(centered_data.T.dot(centered_data))
    idx = eigenValues.argsort()[::-1]   
    eigenValues = eigenValues[idx]
    components = eigenVectors[:, idx[:n_components]]
    projection = centered_data.dot(components)
    return eigenValues[:n_components], components, projection

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

def pythonpca(client, event, invoke_time, event_time):
    global NUM_COMPONENTS
    global results_bucket
    func_start = invoke_time
    dictionary = {}
    key, bucket = getKeyBucket(event)
    client.download_file(bucket, key, '/tmp/{}'.format(key)) #creates a temporary file to preserver the shape of the numpy array from bytes
    input_matrix = np.load('/tmp/{}'.format(key))

    #Does the PCA and sends the n_component reduced matrix
    A = input_matrix[input_matrix.files[0]]
    e, v, projections = PCA(A, NUM_COMPONENTS)

    # Create the Payload Dictionary with the necessary fields
    filename = key
    status, invocation_count = checkLambdaStatus()
    dictionary["filename"] = str(filename.split('^')[0])
    dictionary["edgeuploadutctime"] = str(filename.split('^')[1] if '^' in filename else "")
    dictionary["inputblobsize"] = ""        
    dictionary["n_components"] = str(NUM_COMPONENTS)
    dictionary["matrixrows"] = str(A.shape[0])
    dictionary["matrixcolumns"] = str(A.shape[1])
    dictionary["func_start"] = str(func_start)
    dictionary["eventTime"] = event_time
    dictionary["lambdastatus"] = str(status)
    dictionary["invocation_count"] = str(invocation_count)
    dictionary["container_name"] = ""
    dictionary["funccompleteutctime"] = str(datetime.datetime.utcnow().isoformat())
    pickle_payload = pickle.dumps(projections)
    client.put_object(Bucket=results_bucket, Key="{}.pkl".format(key.split('.')[0]), Body=pickle_payload, Metadata=dictionary)
    os.remove('/tmp/{}'.format(key))    
