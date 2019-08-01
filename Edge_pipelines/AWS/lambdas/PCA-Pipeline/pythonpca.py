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
MATRIX_DIRECTORY = os.getenv('MATRIX_DIRECTORY', default='/home/pi/Matrices/mountedDirectory')
STATS_DIRECTORY = os.getenv('STATS_DIRECTORY', default='/home/pi/AWS/mountedStatistics')
NUM_COMPONENTS = int(os.getenv('NUM_COMPONENTS', default=2))
results_bucket = os.getenv('RESULTS_BUCKET')

csvfilename = "Matrixpca_stats_local_{}_{}.csv".format(str(datetime.datetime.now().date()), "AWS")

# Get all the file paths from the directory specified
def get_file_paths(dirname):
    file_paths = []  
    for root, directories, files in os.walk(dirname):
        for filename in files:
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)  
    return file_paths


# write local stats in a csv file
def write_local_stats(filename, stats_list):
    global STATS_DIRECTORY
    try:
        filepath = STATS_DIRECTORY.rstrip(os.sep) + os.sep + filename
        with open(filepath, 'a') as file:
            writer = csv.writer(file, delimiter=',')
            writer.writerows(stats_list)
    except :
        e = sys.exc_info()[0]
        print("Exception occured during writting Statistics File: %s" % e)        
        #sys.exit(0)


def stall_for_connectivity():
    import time
    """
        Implements a stalling function so that message
        sending starts much after edgeHub is initialized
    """
    if os.getenv('STALLTIME'):
        stalltime=int(os.getenv('STALLTIME'))
    else:
        stalltime=60
    print("Stalling for {} seconds for all TLS handshake and other stuff to get done!!! ".format(stalltime))
    for i in range(stalltime):
        print("Waiting for {} seconds".format(i))
        time.sleep(1)
    print("\n\n---------------Will Start in another 5 seconds -------------------\n\n")
    time.sleep(5)


def PCA(input_data, n_components = 2):
    centered_data = input_data - input_data.mean(axis=0)
    eigenValues, eigenVectors = np.linalg.eigh(centered_data.T.dot(centered_data))
    idx = eigenValues.argsort()[::-1]   
    eigenValues = eigenValues[idx]
    components = eigenVectors[:, idx[:n_components]]
    projection = centered_data.dot(components)
    return eigenValues[:n_components], components, projection


def pythonpca(s3_client):
    global MATRIX_DIRECTORY
    global csvfilename
    global NUM_COMPONENTS
    global results_bucket
    stall_for_connectivity()

    try:
        t0 = timer()
        all_file_paths = get_file_paths(MATRIX_DIRECTORY)
        local_stats = [['matrixname', 'payloadsize', 'matrixfilesize', 'matrixfileobjectsize', 
                        'matrixrows', 'matrixcolumns', 'count', 
                        't0', 
                        't1', 
                        'f_t0',
                        'f_t1', 
                        'f_t2']]
        write_local_stats(csvfilename, local_stats)
        t1 = timer()
        count = 1

        for file in all_file_paths:
            filename = file.split(os.sep)[-1]
            f_t0 = timer()
            dictionary = {}
            temp = np.load(file)
            A = temp[temp.files[0]]
            e, v, projections = PCA(A, NUM_COMPONENTS)
            dictionary["filename"] = filename
            dictionary["func_start"] = str(f_t0)
            dictionary["n_components"] = str(NUM_COMPONENTS)
            dictionary["matrixrows"] = str(A.shape[0])
            dictionary["matrixcolumns"] = str(A.shape[1])
            dictionary["totalfunctiontime"] = str(timer() - f_t0)
            dictionary["funccompleteutctime"] = str(datetime.datetime.utcnow().isoformat())
            pickle_payload = pickle.dumps(projections)
            
            f_t1 = timer()
            s3_client.put_object(Bucket=results_bucket, Key="{}.pkl".format(filename.split('.')[0]), Body=pickle_payload, Metadata=dictionary)            

            f_t2 = timer()

            local_stats.append([file, sys.getsizeof(pickle_payload), os.path.getsize(file), sys.getsizeof(file), 
                                A.shape[0], A.shape[1], count, 
                                t0, 
                                t1, 
                                f_t0, 
                                f_t1, 
                                f_t2])

            print("Payload: ",dictionary)
            
            if count%200==0:
                write_local_stats(csvfilename, local_stats)
                local_stats = []
            count+=1
    except:
        e = sys.exc_info()[0]
        print("Exception occured during PCA: %s" % e)

    finally:
        write_local_stats(csvfilename, local_stats)
