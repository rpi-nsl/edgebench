#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul  6 16:26:15 2018

@author: "Anirban Das"
"""
from timeit import default_timer as timer
import os
import json
import datetime
import sys, logging
import uuid , tempfile
import azure.functions as func

sys.path.append("/home/site/wwwroot/audio-pipeline/")
sys.path.append("/home/site/wwwroot/audio-pipeline/sphinxbase")
sys.path.append("/home/site/wwwroot/audio-pipeline/pocketsphinx")
#logging.info(f"-------------------------------------- {sys.path} ---------- {os.getcwd()}")
from pocketsphinx import Pocketsphinx, get_model_path, get_data_path, AudioFile

# Initialize global variables -----------------------------------------------------------
container_name = os.getenv('CONTAINER_NAME') #this gives the container name in which the code executes
blob_container_name = "myblobcontainer"
logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
logger = logging.getLogger(__name__)

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


# Code for doing the actual speech 2 text conversion
def getSpeech2Text(blobin: func.InputStream, blobout: func.Out[bytes], context: func.Context, func_start):
    global blob_container_name
    global container_name
    
    try:
        dictionary = {}
        input_file = tempfile.NamedTemporaryFile(delete=False)
        with open(input_file.name, 'wb') as f:
            f.write(blobin.read())
        filename = blobin.name    
        filename = filename.split(os.sep)[-1]
        filename = filename.replace("%3A", ":")
        filename = filename.replace("%40", "@")
        filename = filename.replace("%5E", "^")
        
        PS_DECODER = getPockerSphinxDecoder()
    
        PS_DECODER.decode(audio_file=input_file.name,
                    buffer_size=2048,
                    no_search=False,
                    full_utt=False)

        translation = PS_DECODER.hypothesis() 
        
        status, invocation_count = checkLambdaStatus()
        filename = filename.split(os.sep)[-1]
        dictionary["filename"] = filename.split('^')[0]
        dictionary["container_name"] = str(container_name)
        dictionary["blob_size"] = str(blobin.length)
        dictionary["edgeuploadutctime"] = filename.split('^')[1] if '^' in filename else ""
        dictionary["translation"] = translation 
        dictionary["invoke_time"] = ""
        dictionary["func_start"] = func_start
        dictionary["eventTime"] = ""
        dictionary["lambdastatus"] = status
        dictionary["invocation_count"] = invocation_count        
        dictionary["container_name"] = str(container_name)
        dictionary["funccompleteutctime"] = datetime.datetime.utcnow().isoformat()
        json_payload = json.dumps(dictionary)
        
        blobout.set(json_payload) #write the output to the out file
        os.remove(input_file.name)
    except :
        e = sys.exc_info()[0]
        print("Exception occured during prediction: %s" % e)
        sys.exit(0)
