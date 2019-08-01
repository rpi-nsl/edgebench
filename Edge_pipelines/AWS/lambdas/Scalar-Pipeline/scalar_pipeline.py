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

logging.basicConfig(format='%(asctime)s Content: %(message)s', level=logging.DEBUG)
client = greengrasssdk.client('iot-data')

# Initialize global variables -----------------------------------------------------------
MachineTemperatureMin = 21
MachineTemperatureMax = 100
MachinePressureMin = 1
MachinePressureMax = 10
AmbientTemperature = 21
HumidityPercentMin = 24
HumidityPercentMax = 27
STATS_DIRECTORY = os.getenv('STATS_DIRECTORY', default='/home/pi/AWS/mountedStatistics')
SLEEP_TIME = os.getenv('SLEEP', default=1)
TOTAL_MESSAGES = os.getenv('TOTAL_MESSAGES', default=1000)

json_data = '''{"machine": {"temperature": "%s","pressure": "%s"},"ambient": {"temperature":"%s","humidity": "%s"},"messagesendutctime": "%s", "messageid":"%s"}'''

csvfilename = "Scalar_local_stats_{}_{}.csv".format(str(datetime.datetime.now().date()), "AWS")


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
    global STATS_DIRECTORY
    global TOTAL_MESSAGES
    global SLEEP_TIME
    global json_data
    global csvfilename
    local_stats = [['messageid', 'totalcomputetime', 'payloadsize', 'starttime', 'f_t0', 'f_t0_1', 'f_t1']]
    count = 1
    try:
        while True:
            starttime = datetime.datetime.utcnow().isoformat()
            f_t0 = timer()
            json_payload = json_data %(
                                random.uniform(MachineTemperatureMin , MachineTemperatureMax),
                                random.uniform(MachinePressureMin, MachinePressureMax),
                                AmbientTemperature - random.uniform(0, 4),
                                random.uniform(HumidityPercentMin, HumidityPercentMax),
                                datetime.datetime.utcnow().isoformat(),
                                count
                            )
            f_t0_1 = timer()
            client.publish(topic=outputQueueName, payload=json_payload)
            f_t1 = timer()

            local_stats.append([count, f_t1- f_t0, sys.getsizeof(json_payload), starttime, f_t0, f_t0_1, f_t1])
            print("Payload: {} : {}".format(count,json_payload))
            # if count%200==0:
            #         write_local_stats(csvfilename, local_stats)
            #         local_stats = []
            count+=1
            if count > float(TOTAL_MESSAGES):
                print("All messages sent {}".format(count))
                break
            time.sleep(float(SLEEP_TIME))


    except:
        e = sys.exc_info()[0]
        print("Exception occured during Scalar Pipeline: %s" % e)

    finally:
        write_local_stats(csvfilename, local_stats)


temperatureGenerator()

# Dummy Handler
def lambda_handler(event, context):
    return 'Hello from Lambda Scalar Pipeline'
