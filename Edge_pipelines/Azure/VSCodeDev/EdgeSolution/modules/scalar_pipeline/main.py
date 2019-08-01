#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 30 11:42:50 2019

@author: Anirban Das
"""

import random
import time
import sys, os
import iothub_client
# pylint: disable=E0611
import logging
import datetime, time
from timeit import default_timer as timer
from iothub_client import IoTHubModuleClient, IoTHubClientError, IoTHubTransportProvider
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError
import csv

#set up the global variables
MachineTemperatureMin = 21
MachineTemperatureMax = 100
MachinePressureMin = 1
MachinePressureMax = 10
AmbientTemperature = 21
HumidityPercentMin = 24
HumidityPercentMax = 27
logging.basicConfig(format='%(asctime)s Content: %(message)s', level=logging.DEBUG)


# messageTimeout - the maximum time in milliseconds until a message times out.
# The timeout period starts at IoTHubModuleClient.send_event_async.
# By default, messages do not expire.
MESSAGE_TIMEOUT = 10000

# global counters
RECEIVE_CALLBACKS = 0
SEND_CALLBACKS = 0

# Choose HTTP, AMQP or MQTT as transport protocol.  Currently only MQTT is supported.
PROTOCOL = IoTHubTransportProvider.MQTT

STATS_DIRECTORY = os.getenv('STATS_DIRECTORY', default='/home/pi/AWS/mountedStatistics')
SLEEP_TIME = os.getenv('SLEEP', default=1)
TOTAL_MESSAGES = os.getenv('TOTAL_MESSAGES', default=1000)


json_data = '''{"machine": {"temperature": "%s","pressure": "%s"},"ambient": {"temperature":"%s","humidity": "%s"},"messagesendutctime": "%s", "messageid":"%s"}'''

csvfilename = "Scalar_local_stats_{}_{}.csv".format(str(datetime.datetime.now().date()), "Azure")


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

#message generator
def messageGenerator(hubManager, outputQueueName='scalarpipeline', context=0):
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
    local_stats = [['messageid', 'totalcomputetime', 'payloadsize', 'f_t0', 'f_t1']]
    count = 1 
    try:
        while True:
            f_t0 = timer()
            json_payload = json_data %(
                                random.uniform(MachineTemperatureMin , MachineTemperatureMax),
                                random.uniform(MachinePressureMin, MachinePressureMax),
                                AmbientTemperature - random.uniform(0, 4),
                                random.uniform(HumidityPercentMin, HumidityPercentMax),
                                datetime.datetime.utcnow().isoformat(),
                                count
                            )
            message = IoTHubMessage(bytearray(json_payload, 'utf8'))
            hubManager.client.send_event_async(outputQueueName, message, send_confirmation_callback, 0)
            f_t1 = timer()

            local_stats.append([count, f_t1- f_t0, sys.getsizeof(json_payload), f_t0, f_t1])
            print("Payload: {} : {}".format(count,json_payload))
            if count%200==0:
                    write_local_stats(csvfilename, local_stats)
                    local_stats = []
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


# Callback received when the message that we're forwarding is processed.
def send_confirmation_callback(message, result, user_context):
    global SEND_CALLBACKS
    print ( "Confirmation[%d] received for message with result = %s" % (user_context, result) )
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    SEND_CALLBACKS += 1
    print ( "    Total calls confirmed: %d" % SEND_CALLBACKS )


# receive_message_callback is invoked when an incoming message arrives on the specified 
# input queue (in the case of this sample, "input1").  Because this is a filter module, 
# we will forward this message onto the "output1" queue.
def receive_message_callback(message, hubManager):
    global RECEIVE_CALLBACKS
    message_buffer = message.get_bytearray()
    size = len(message_buffer)
    print ( "    Data: <<<%s>>> & Size=%d" % (message_buffer[:size].decode('utf-8'), size) )
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    RECEIVE_CALLBACKS += 1
    print ( "    Total calls received: %d" % RECEIVE_CALLBACKS )
    hubManager.forward_event_to_output("output1", message, 0)
    return IoTHubMessageDispositionResult.ACCEPTED


class HubManager(object):

    def __init__(
            self,
            protocol=IoTHubTransportProvider.MQTT):
        self.client_protocol = protocol
        self.client = IoTHubModuleClient()
        self.client.create_from_environment(protocol)

        # set the time until a message times out
        self.client.set_option("messageTimeout", MESSAGE_TIMEOUT)
        
        # Calls the dummy message generator
        messageGenerator(self)

    # Forwards the message received onto the next stage in the process.
    def forward_event_to_output(self, outputQueueName, event, send_context):
        self.client.send_event_async(
            outputQueueName, event, send_confirmation_callback, send_context)

def main(protocol):
    try:
        print ( "\nPython %s\n" % sys.version )
        print ( "IoT Hub Client for Python" )

        hub_manager = HubManager(protocol)

        print ( "Starting the IoT Hub Python sample using protocol %s..." % hub_manager.client_protocol )
        print ( "The sample is now waiting for messages and will indefinitely.  Press Ctrl-C to exit. ")

        while True:
            time.sleep(1)

    except IoTHubError as iothub_error:
        print ( "Unexpected error %s from IoTHub" % iothub_error )
        return
    except KeyboardInterrupt:
        print ( "IoTHubModuleClient sample stopped" )

if __name__ == '__main__':
    main(PROTOCOL)
