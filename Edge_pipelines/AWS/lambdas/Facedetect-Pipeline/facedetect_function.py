#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 18 15:09:16 2019

@author: "Anirban Das"
"""

from timeit import default_timer as timer
import json , csv
import dlib
from PIL import Image
import numpy as np
import sys, os
import datetime


# Initialize global variables -----------------------------------------------------------
IMAGE_DIRECTORY = os.getenv('IMAGE_DIRECTORY', default='/home/pi/Pictures/mountedDirectory')
STATS_DIRECTORY = os.getenv('STATS_DIRECTORY', default='/home/pi/AWS/mountedStatistics')

csvfilename = "Dlib_facedetect_stats_local_{}_{}.csv".format(str(datetime.datetime.now().date()), "AWS")

# Get all the file paths from the directory specified
def get_file_paths(dirname):
    file_paths = []
    for root, directories, files in os.walk(dirname):
        for filename in sorted(files):
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)
    return file_paths


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
        
def facedetect(client, outputQueueName='greengrass/facedetect'):
    global IMAGE_DIRECTORY
    global csvfilename
    stall_for_connectivity()    
    try:
        t0 = timer()
        local_stats = [['imagefilename', 'payloadsize', 'imagefilesize', 'imagefileobjectsize', 
                        'imagewidth', 'imageheight', 'numfaces', 'count', 
                        't0', 
                        't1', 
                        't2',
                        'starttime',
                        'f_t0', 
                        'f_t1', 
                        'f_t2', 
                        'f_t3', 
                        'f_t4']]
        all_file_paths = get_file_paths(IMAGE_DIRECTORY)
        
        # write_local_stats(csvfilename, local_stats)
        
        t1 = timer()
        detector = dlib.get_frontal_face_detector()
        t2 = timer()
        
        count = 1
        for file in all_file_paths:
            starttime = datetime.datetime.utcnow().isoformat()
            f_t0 = timer()
            dictionary = {}
            
            
            filename = file.split(os.sep)[-1]
            #img = cv2.imread(file)
            img = np.array(Image.open(file))
            details = img.shape
            length = img.shape[0]
            width = img.shape[1]
            #length, width, garbage = img.shape
            
            f_t1 = timer()
            
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
            client.publish(topic=outputQueueName, payload=str(json_payload))
            
            f_t4 = timer()
            
            local_stats.append([filename, sys.getsizeof(json_payload), os.path.getsize(file), sys.getsizeof(file), 
                            width, length, len(dets), count, 
                            t0, 
                            t1, 
                            t2,
                            starttime,
                            f_t0, 
                            f_t1, 
                            f_t2, 
                            f_t3, 
                            f_t4])
            print("Got {} faces from image file  {} in {} seconds\n".format(len(dets), filename, f_t4 - f_t0))     
            
            # write local stats to csv file
#            if count%200==0:
#                write_local_stats(csvfilename, local_stats)
#                local_stats = []
            count+=1
    
    except:
        e = sys.exc_info()[0]
        print("Exception occured during prediction: %s" % e)
        sys.exit(0)
    
    finally:
        write_local_stats(csvfilename, local_stats)
