#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  6 16:26:15 2018

@author: "Anirban Das"
"""

import os
from pocketsphinx import Pocketsphinx, get_model_path, get_data_path, AudioFile
from timeit import default_timer as timer
import json, csv
import datetime
import sys, logging
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError


logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
STATS_DIRECTORY = '/home/moduleuser/Statistics'
AUDIO_DIRECTORY = '/home/moduleuser/Music'

# Get all the file paths from the directory specified
def get_file_paths(dirname):
    file_paths = []  
    for root, directories, files in os.walk(dirname):
        for filename in files:
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)  
    return file_paths

# Initiates and returns a pocket sphinx decoder
def getPockerSphinxDecoder():
    model_path = get_model_path()
    data_path = get_data_path()
    config = {
        'verbose': False,
        'hmm': os.path.join(model_path, 'en-us'),
        'lm': os.path.join(model_path, 'en-us.lm.bin'),
        'dict': os.path.join(model_path, 'cmudict-en-us.dict')
    }

    return Pocketsphinx(**config)

# write local stats in a csv file
def write_local_stats(filename, stats_list):
    global STATS_DIRECTORY
    try:
        filepath = STATS_DIRECTORY.rstrip(os.sep) + os.sep + filename
        with open(filepath, 'w') as file:
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

# Code for doing the actual speech 2 text conversion
def getSpeech2Text(hubManager, callback_function, outputQueueName='audiopipeline', context=0):
    global AUDIO_DIRECTORY
    stall_for_connectivity()
    try:
        time_start_get_file = timer()
        all_file_paths = get_file_paths(AUDIO_DIRECTORY)
        time_stop_get_file = timer()
        print("Got all files in {} seconds".format(time_stop_get_file - time_start_get_file))

        # get a pocketsphinx decoder
        ps_decoder = getPockerSphinxDecoder()
        time_ps_decoder = timer()
        print("Got PockerSphinx Decoder in {} seconds".format(time_ps_decoder - time_stop_get_file))
        
        local_stats = [['audiofilename', 'totalcomputetime', 'payloadsize']]

        for files in all_file_paths:
            start = timer()
            dictionary = {}
            filename = files.split(os.sep)[-1]
            ps_decoder.decode(audio_file=files,
                        buffer_size=2048,
                        no_search=False,
                        full_utt=False)
            translation = ps_decoder.hypothesis() 
            convertion_time = timer()-start
            
            #dictionary["totalcomputetime"] = convertion_time            
            dictionary["audiofilename"] = filename
            dictionary["translation"] = translation
            dictionary["messagesendutctime"] = datetime.datetime.utcnow().isoformat()
            json_payload = json.dumps(dictionary)
            message = IoTHubMessage(bytearray(json_payload, 'utf8'))

            # Publish the Payload in the specific topic
            hubManager.client.send_event_async(outputQueueName, message, callback_function, context)

            print("Payload: {}".format(json_payload))
            print("Converted audio file  {} in {} seconds\n".format(filename, convertion_time))     
            local_stats.append([files, convertion_time, sys.getsizeof(json_payload)])

        # write local stats to csv file
        write_local_stats("Azure_audio_local_stats_{}.csv".format(str(datetime.datetime.now().date())), local_stats)
            
    except :
        e = sys.exc_info()[0]
        print("Exception occured during prediction: %s" % e)
        sys.exit(0)