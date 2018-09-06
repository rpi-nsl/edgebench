#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 21 13:59:33 2018

@author: "Anirban Das"
"""

import sys
import greengrasssdk
import platform
import os
import logging
import json
import random
import datetime , time
from timeit import default_timer as timer
import csv

# Setting up the global variables
MachineTemperatureMin = 21
MachineTemperatureMax = 100
MachinePressureMin = 1
MachinePressureMax = 10
AmbientTemperature = 21
HumidityPercentMin = 24
HumidityPercentMax = 27
logging.basicConfig(format='%(asctime)s Content: %(message)s', level=logging.DEBUG)

STATS_DIRECTORY = '/home/pi/AWS/mountedStatistics'

client = greengrasssdk.client('iot-data')
json_data = '''{"machine": {"temperature": "%s","pressure": "%s"},"ambient": {"temperature":"%s","humidity": "%s"},"messagesendutctime": "%s", "messageid":"%s"}'''

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

# Message Payload Generator
def temperatureGenerator(outputQueueName='greengrass/scalar_pipeline'):
    stall_for_connectivity()
    global MachineTemperatureMin
    global MachineTemperatureMax
    global MachinePressureMin
    global MachinePressureMax 
    global AmbientTemperature 
    global HumidityPercentMin 
    global HumidityPercentMax
    count = 1 
    local_stats = ['messageid', 'totalcomputetime', 'payloadsize']
    with open(STATS_DIRECTORY+os.sep+"AWS_scalar_local_stats_{}.csv".format(str(datetime.datetime.now().date())), 'w') as stats_file:
        writer = csv.writer(stats_file, delimiter=',')
        writer.writerow(local_stats)
        
        while True:
            start_time = timer()
            json_payload = json_data %(
                                random.uniform(MachineTemperatureMin , MachineTemperatureMax),
                                random.uniform(MachinePressureMin, MachinePressureMax),
                                AmbientTemperature - random.uniform(0, 4),
                                random.uniform(HumidityPercentMin, HumidityPercentMax),
                                datetime.datetime.utcnow().isoformat(),
                                count
                            )
            client.publish(topic=outputQueueName, payload=json_payload)
            writer.writerow([count, timer()- start_time, sys.getsizeof(json_payload)])
            logging.info(json_payload)
            print("Payload: {} : {}".format(count,json_payload))
            count = count + 1
            if os.getenv('COUNT'):
                if count > float(os.getenv('COUNT')):
                    print("All messages sent {}".format(count))
                    break
            if os.getenv('SLEEP'):
                time.sleep(float(os.getenv('SLEEP')))
            else:
                time.sleep(1)

        
temperatureGenerator()

# Dummy Handler
def lambda_handler(event, context):
    return 'Hello from Lambda Scalar Pipeline'

