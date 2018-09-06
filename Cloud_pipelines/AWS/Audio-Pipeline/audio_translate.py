#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 21 20:00:14 2018

@author: "Anirban Das"
"""
from timeit import default_timer as timer
start_everything_time = timer()
import os
from pocketsphinx import Pocketsphinx, get_model_path, get_data_path, AudioFile
import json, csv
import datetime
import sys, logging
import tempfile

logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
logger = logging.getLogger(__name__)

results_bucket = os.getenv('RESULTS_BUCKET')
print(results_bucket)


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
def getSpeech2Text(client, event):
    try:
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        logger.info("key = {} and bucket = {}".format(key, bucket))

        time_start_get_file = timer()
        # tmp = tempfile.NamedTemporaryFile()
        # client.download_file(bucket, key, tmp.name)
        # tmp.flush()
        client.download_file(bucket, key, '/tmp/{}'.format(key))
        time_stop_get_file = timer()
        print("Got all files in {} seconds".format(time_stop_get_file - time_start_get_file))

        ps_decoder = getPockerSphinxDecoder()
        time_ps_decoder = timer()
        print("Got PockerSphinx Decoder in {} seconds".format(time_ps_decoder - time_stop_get_file))
        
        start = timer()
        dictionary = {}
        ps_decoder.decode(audio_file='/tmp/{}'.format(key),
                        buffer_size=2048,
                    no_search=False,
                    full_utt=False)
        translation = ps_decoder.hypothesis() 
        convertion_time = timer()- start
        print("Dfsssssssssssssssss")
        filename = key #tmp.name
        dictionary["totalcomputetime"] = convertion_time 
        dictionary["audiofilename"] = filename
        dictionary["translation"] = translation
        dictionary["messagesendutctime"] = datetime.datetime.utcnow().isoformat()
        dictionary["totalfunctiontime"] = timer() - start_everything_time
        json_payload = json.dumps(dictionary)
        print("sdfdfsdfdsfsf")

        json_payload = json.dumps(dictionary)
        tmp = tempfile.NamedTemporaryFile()
        tmp.write(json_payload)
        tmp.flush()
        print("after flush")
        client.upload_file(tmp.name, results_bucket, "{}.json".format(key))
        os.remove('/tmp/{}'.format(key))
        

        print("Payload: {}".format(json_payload))
        print("Converted audio file  {} in {} seconds\n".format(filename, convertion_time))

    
    except :
        e = sys.exc_info()[0]
        print("Exception occured during prediction: %s" % e) 
        sys.exit(0)