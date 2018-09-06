#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 6 14:41:37 2018

@author: "Anirban Das"
"""

import sys, csv
import time
import platform
import os
from threading import Timer
import load_model
import cv2
import json
from iothub_client import IoTHubMessage
from timeit import default_timer as timer
import datetime, logging

logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')
model_path = './mxnet_models/squeezenetv1.1/'
global_model = load_model.ImagenetModel(model_path + 'synset.txt', model_path + 'squeezenet_v1.1')  
SEND_CALLBACKS = 0
STATS_DIRECTORY = '/home/moduleuser/Statistics'


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


def mxnet_image_classification(outputQueueName, hubManager, callback_function, context, N=5, reshape=(224, 224)):
    stall_for_connectivity()
    if global_model is not None:
        try:
            image_folderPath="/home/moduleuser/Images"
            local_stats = [['imagefilename', 'imageiotime', 'predictiontime', 'totalcomputetime', 'payloadsize']]

            for filename in os.listdir(image_folderPath):
                dictionary = {}
                
                # Read the image from the folder
                time_start_read = timer()
                filepath = image_folderPath + os.sep + filename
                im = cv2.imread(filepath)
                time_stop_read = timer()

                print("Read image {} in {} seconds".format(filename, time_stop_read - time_start_read))

                # Predict the classification from the image
                prediction = global_model.predict_from_image(im, reshape, N)
                time_end_prediction = timer()
                print("Predicted image {} in {} seconds".format(filename, time_end_prediction - time_stop_read))

                # Create the Payload JSON with the necessary fields
                for idx, elem in enumerate(prediction):
                    temp_dict = {}
                    temp_dict["probability"] = float(elem[0])
                    temp_dict["wordnetid"], temp_dict["classification"] = elem[1].split(" ", 1)                    
                    dictionary["classification_{}".format(idx)] = temp_dict
                dictionary["imagefilename"] = filename
                dictionary["messagesendutctime"] = datetime.datetime.utcnow().isoformat()
                json_payload = json.dumps(dictionary)
               
                # Publish the Payload in the specific topic
                message = IoTHubMessage(bytearray(json_payload, 'utf8'))
                hubManager.client.send_event_async(outputQueueName, message, callback_function, 0)
                
                logging.info(json_payload)
                print("Payload: ",json_payload)
                print("All procedure for {} done in {} seconds. \n".format(filename, timer() - time_start_read))
                local_stats.append([filename, time_stop_read - time_start_read, time_end_prediction - time_stop_read, time_end_prediction - time_start_read, sys.getsizeof(json_payload)])

            # write local stats to csv file
            write_local_stats("Azure_image_local_stats_{}.csv".format(str(datetime.datetime.now().date())), local_stats)

        except Exception as ex:
            e = sys.exc_info()[0]
            print("Exception occured during prediction: %s" % e)
            print("Exception: %s" % ex)
            sys.exit(0)

    # Asynchronously schedule this function to be run again in 1 seconds
    # Timer(0, mxnet_image_classification, (outputQueueName, hubManager, context)).start()