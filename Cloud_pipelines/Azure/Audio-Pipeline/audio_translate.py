#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul  6 16:26:15 2018

@author: "Anirban Das"
"""
from timeit import default_timer as timer
start_everything_time = timer()
import os
from pocketsphinx import Pocketsphinx, get_model_path, get_data_path, AudioFile
import json, csv
import datetime
import sys, logging

logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
logger = logging.getLogger(__name__)

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
def getSpeech2Text():
    try:
        time_start_get_file = timer()
        files = os.environ['myBlob']
        time_stop_get_file = timer()
        print("Got all files in {} seconds".format(time_stop_get_file - time_start_get_file))

        # get a pocketsphinx decoder
        ps_decoder = getPockerSphinxDecoder()
        time_ps_decoder = timer()
        print("Got PockerSphinx Decoder in {} seconds".format(time_ps_decoder - time_stop_get_file))
        
        start = timer()
        dictionary = {}
        filename = files.split(os.sep)[-1]
        ps_decoder.decode(audio_file=files,
                    buffer_size=2048,
                    no_search=False,
                    full_utt=False)
        translation = ps_decoder.hypothesis() 
        convertion_time = timer()-time_start_get_file
        
        dictionary["totalcomputetime"] = convertion_time            
        dictionary["audiofilename"] = filename
        dictionary["translation"] = translation
        dictionary["messagesendutctime"] = datetime.datetime.utcnow().isoformat()
        dictionary["totalfunctiontime"] = timer() - start_everything_time
        json_payload = json.dumps(dictionary)
        

        # Output the modified file to a separate folder in the Storage Blob
        output_file = open(os.environ['outputBlob'], 'w')
        output_file.write(json_payload)
        output_file.close()

        print("Payload: {}".format(json_payload))
        print("Converted audio file  {} in {} seconds\n".format(filename, convertion_time))     
           
    except :
        e = sys.exc_info()[0]
        print("Exception occured during prediction: %s" % e)
        sys.exit(0)