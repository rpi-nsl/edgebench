#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 30 11:56:59 2019

@author: Anirban Das
"""

import logging
import datetime
import azure.functions as func
import uuid
import json
import os

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

def main(blobin: func.InputStream, blobout: func.Out[bytes], context: func.Context):
    logging.info(f"--- Python blob trigger function processed blob \n"
                 f"----- Name: {blobin.name}\n"
                 f"----- Blob Size: {blobin.length} bytes")
    func_start = datetime.datetime.utcnow().isoformat()
    dictionary = json.load(blobin)
    filename = blobin.name
    status, invocation_count = checkLambdaStatus()
    dictionary["filename"] = str(filename.split('^')[0])
    dictionary["edgeuploadutctime"] = str(filename.split('^')[1] if '^' in filename else "")
    dictionary["invoke_time"] = str(func_start)
    dictionary["func_start"] = str(func_start)
    dictionary["eventTime"] = ""
    dictionary["blobsize"] = str(blobin.length)
    dictionary["lambdastatus"] = str(status)
    dictionary["invocation_count"] = str(invocation_count)
    dictionary["funccompleteutctime"] = str(datetime.datetime.utcnow().isoformat())
    json_payload = json.dumps(dictionary)
    
    blobout.set(json_payload)