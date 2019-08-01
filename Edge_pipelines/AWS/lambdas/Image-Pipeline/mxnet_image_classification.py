#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 29 18:38:02 2018

@author: "Anirban Das"
"""

import sys, os
import json
import logging
from timeit import default_timer as timer
import datetime
import load_model
import cv2
import csv

# Initialize global variables -----------------------------------------------------------
IMAGE_DIRECTORY = os.getenv('IMAGE_DIRECTORY', default='/home/pi/Pictures/mountedDirectory')
STATS_DIRECTORY = os.getenv('STATS_DIRECTORY', default='/home/pi/AWS/mountedStatistics')
model_path = 'squeezenetv1.1/'
global_model = load_model.ImagenetModel(model_path + 'synset.txt', model_path + 'squeezenet_v1.1')

csvfilename = "Image_recognition_local_stats_{}_{}.csv".format(str(datetime.datetime.now().date()), "AWS")

# Get all the file paths from the directory specified
def get_file_paths(dirname):
    file_paths = []
    for root, directories, files in os.walk(dirname):
        for filename in sorted(files):
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


def mxnet_image_classification(client, outputQueueName='greengrass/image_pipeline', N = 5, reshape=(224, 224) ):
    global IMAGE_DIRECTORY
    global global_model
    global csvfilename
    stall_for_connectivity()
    if global_model is not None:
        try:
            all_file_paths = get_file_paths(IMAGE_DIRECTORY)
            local_stats = [['imagefilename', 'payloadsize', 'imagefilesize', 'imagefileobjectsize',
                        'imagewidth', 'imageheight','count', 'starttime', 
                        'f_t0','f_t1','f_t2','f_t3','f_t4', 'f_t5']]

            count = 1
            for filepath in all_file_paths:
                starttime = datetime.datetime.utcnow().isoformat()
                f_t0 = timer()
                dictionary = {}
                filename = filepath.split(os.sep)[-1]
                # Read the image from the folder
                f_t1 = timer()
                im = cv2.imread(filepath)
                length, width = im.shape[0:2]
                f_t2 = timer()

                # Predict the classification from the image
                prediction = global_model.predict_from_image(im, reshape, N)
                f_t3 = timer()

                # Create the Payload JSON with the necessary fields
                for idx, elem in enumerate(prediction):
                    temp_dict = {}
                    temp_dict["probability"] = float(elem[0])
                    temp_dict["wordnetid"], temp_dict["classification"] = elem[1].split(" ", 1)
                    dictionary["classification_{}".format(idx)] = temp_dict
                dictionary["imagefilename"] = filename
                dictionary["messagesendutctime"] = datetime.datetime.utcnow().isoformat()
                json_payload = json.dumps(dictionary)
                f_t4 = timer()

                # Publish the Payload in the specific topic
                client.publish(topic= outputQueueName, payload=str(json_payload))
                f_t5 = timer()

                print("All procedure for {} done in {} seconds. \n".format(filename, f_t5 - f_t0))
                local_stats.append([filename, sys.getsizeof(json_payload), os.path.getsize(filepath), sys.getsizeof(filepath),
                            width, length, count, starttime, 
                            f_t0,
                            f_t1,
                            f_t2,
                            f_t3,
                            f_t4,
                            f_t5])

                # write local stats to csv file
                # if count%200==0:
                #     write_local_stats(csvfilename, local_stats)
                #     local_stats = []
                count+=1
        except :
            e = sys.exc_info()[0]
            print("Exception occured during prediction: %s" % e)
            sys.exit(0)

        finally:
            write_local_stats(csvfilename, local_stats)
