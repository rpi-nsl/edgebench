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
import azure.functions as func
import numpy as np
from azure.storage.blob import BlockBlobService, PublicAccess
import tempfile
import uuid

# Initialize global variables -----------------------------------------------------------
NUM_COMPONENTS = os.getenv('NUM_COMPONENTS', default=2)
container_name = os.getenv('CONTAINER_NAME') #this gives the container name in which the code executes
blob_container_name = "myblobcontainer"


block_blob_service = BlockBlobService(account_name='edgebench8561', 
				account_key='0i7buxxEJ8gMW3XcMu11JBNcZllkJGdm3UkHuy24Sxj+x1iQv7bf62SKJwSBiYIZ/xhjp9zXkf3yfWtgfud1oA==')
#block_blob_service.create_container(container_name)

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


def pythonpca(blobin: func.InputStream, blobout: func.Out[bytes], context: func.Context, func_start):
    global NUM_COMPONENTS
    global blob_container_name
    global container_name
    dictionary = {}
    tempmat = tempfile.TemporaryFile() #creates a temporary file to preserver the shape of the numpy array from bytes
    tempmat.write(blobin.read())
    tempmat.seek(0)
    input_matrix = np.load(tempmat)

    #Does the PCA and sends the n_component reduced matrix
    A = input_matrix[input_matrix.files[0]]
    e, v, projections = PCA(A, NUM_COMPONENTS)

    # Create the Payload Dictionary with the necessary fields
    status, invocation_count = checkLambdaStatus()
    filename = blobin.name    
    filename = filename.split(os.sep)[-1]
    filename = filename.replace("%3A", ":")
    filename = filename.replace("%40", "@")
    filename = filename.replace("%5E", "^")
    dictionary["filename"] = str(filename.split('^')[0])
    dictionary["edgeuploadutctime"] = str(filename.split('^')[1] if '^' in filename else "")
    dictionary["func_start"] = str(func_start)
    dictionary["inputblobsize"] = str(blobin.length)        
    dictionary["n_components"] = str(NUM_COMPONENTS)
    dictionary["matrixrows"] = str(A.shape[0])
    dictionary["matrixcolumns"] = str(A.shape[1])
    dictionary["lambdastatus"] = str(status)
    dictionary["invocation_count"] = str(invocation_count)
    dictionary["container_name"] = str(container_name)
    dictionary["funccompleteutctime"] = str(datetime.datetime.utcnow().isoformat())
    pickle_payload = pickle.dumps(projections)
    print(os.environ)
    print(container_name, status,  ">>>>>>>>>>>done---------NEW-----------dddddddd-Env contname----------------Simplified------")
    #block_blob_service.create_blob_from_bytes(container_name, 
    #                        "{}^{}".format(filename, datetime.datetime.utcnow().isoformat()), pickle_payload, metadata=dictionary)
    block_blob_service.create_blob_from_bytes(blob_container_name, "{}.pkl".format(filename.split('.')[0]), pickle_payload, metadata=dictionary)
    print("finish---------------------------------------------")
