#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 24 17:48:46 2019

@author: "Anirban Das"
"""

import os, sys
from timeit import default_timer as timer
import datetime 
import json , csv
import dlib
from PIL import Image
import numpy as np
from iothub_client import IoTHubMessage
#from azure.storage.blob import BlockBlobService, PublicAccess


# Initialize global variables -----------------------------------------------------------
IMAGE_DIRECTORY = os.getenv('IMAGE_DIRECTORY', default='/home/moduleuser/Images')
STATS_DIRECTORY = os.getenv('STATS_DIRECTORY', default='/home/moduleuser/Statistics')
container_name = os.getenv('CONTAINER_NAME')

# block_blob_service = BlockBlobService(account_name='edgebench8561', 
#                 account_key='0i7buxxEJ8gMW3XcMu11JBNcZllkJGdm3UkHuy24Sxj+x1iQv7bf62SKJwSBiYIZ/xhjp9zXkf3yfWtgfud1oA==')

csvfilename = "Dlib_facedetect_stats_local_{}_{}.csv".format(str(datetime.datetime.now().date()), "Azure")

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

def facedetect(hubmanager, callback_function, outputQueueName='facedetectpipeline', context=0):
    stall_for_connectivity()
    global IMAGE_DIRECTORY
    global csvfilename
    try:
        t0 = timer()
        all_file_paths = get_file_paths(IMAGE_DIRECTORY)
        local_stats = [['imagefilename', 'payloadsize', 'imagefilesize', 'imagefileobjectsize',
                            'imagewidth', 'imageheight', 'numfaces', 'count', 
                            't0', 
                            't1', 
                            't2', 
                            'f_t0', 
                            'f_t1', 
                            'f_t2', 
                            'f_t3', 
                            'f_t4']]
        write_local_stats(csvfilename, local_stats)
        
        t1 = timer() # time needed to initiate the detector
        detector = dlib.get_frontal_face_detector()
        t2 = timer()
        
        count = 1
        for file in all_file_paths:
            f_t0 = timer()
            dictionary = {}

            filename = file.split(os.sep)[-1]
            #img = cv2.imread(file)
            img = np.array(Image.open(file))
            length, width, _ = img.shape
            
            f_t1 = timer() #time needed to get the faces
            
            dets = detector(img, 1)
            
            f_t2 = timer()
            
            dictionary["imagefilename"] = filename
            dictionary["numfaces"] = len(dets)
            dictionary["imagewidth"] = str(width)
            dictionary["imageheight"] = str(length)
            dictionary["func_start"] = str(f_t0)
            dictionary["totalcomputetime"] = str(timer() - f_t0) 
            dictionary["funccompleteutctime"] = datetime.datetime.utcnow().isoformat()
            json_payload = json.dumps(dictionary)
            
            f_t3 = timer()
            # Publish the Payload in the specific topic
            message = IoTHubMessage(bytearray(json.dumps(dictionary), 'utf8'))                                            
            hubmanager.client.send_event_async(outputQueueName, message, callback_function, 0)
            f_t4 = timer()
            
            local_stats.append([file, sys.getsizeof(json_payload), os.path.getsize(file), sys.getsizeof(file), 
                    width, length, len(dets), count, 
                    t0, 
                    t1, 
                    t2, 
                    f_t0, 
                    f_t1, 
                    f_t2, 
                    f_t3, 
                    f_t4])
            print("Got {} faces from image file  {} in {} seconds\n".format(len(dets), filename, f_t4 - f_t0))     
            
            # write local stats to csv file
            if count%200==0:
                write_local_stats(csvfilename, local_stats)
                local_stats = []
            count+=1
    
    except :
        e = sys.exc_info()[0]
        print("Exception occured during prediction: %s" % e) 
        sys.exit(0)
    
    finally:
        write_local_stats(csvfilename, local_stats)
