#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 8 2018

@author: "Anirban Das"
"""

import os
import random
import getpass
import datetime, sys, time, csv
from azure.storage.blob import BlockBlobService, PublicAccess


block_blob_service = BlockBlobService(account_name='<Storage Account Name>', 
                account_key='<Key 1 of the Storage Account>')

container_name ='<Container to Upload Files>'
# Create the BlockBlockService
block_blob_service.create_container(container_name)

#set up the global variables
MachineTemperatureMin = 21
MachineTemperatureMax = 100
MachinePressureMin = 1
MachinePressureMax = 10
AmbientTemperature = 21
HumidityPercentMin = 24
HumidityPercentMax = 27

json_data = '''{"machine": {"temperature": "%s","pressure": "%s"},"ambient": {"temperature":"%s","humidity": "%s"},"messagesendutctime": "%s", "messageid":"%s"}'''


STATS_DIRECTORY = "."
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

#message generator
def messageGenerator():
    global MachineTemperatureMin
    global MachineTemperatureMax
    global MachinePressureMin
    global MachinePressureMax 
    global AmbientTemperature 
    global HumidityPercentMin 
    global HumidityPercentMax 
    global json_data
    global block_blob_service
    global container_name
    count = 1
    local_stats = [['messageid', 'messagesendutctime', 'payloadsize']]
    try:
        while True:
            json_payload = json_data %(
                                random.uniform(MachineTemperatureMin , MachineTemperatureMax),
                                random.uniform(MachinePressureMin, MachinePressureMax),
                                AmbientTemperature - random.uniform(0, 4),
                                random.uniform(HumidityPercentMin, HumidityPercentMax),
                                datetime.datetime.utcnow().isoformat(),
                                count
                            )
            messagesendutctime = datetime.datetime.utcnow().isoformat()
            
            block_blob_service.create_blob_from_text(container_name, "{}.json".format(count), json_payload)
            local_stats.append([count, messagesendutctime, sys.getsizeof(json_payload)])
            print("Payload: {} : {}".format(count,json_payload))
            count = count +1
            if count == 200:
                print("All messages sent")
                break
            else:
                time.sleep(5)
    except KeyboardInterrupt:
        print("cancelling Upload, json uploaded {}".format(count))
        print(e)
    finally:
        write_local_stats("AZURE_cloud_scalar_local_stats_{}.csv".format(str(datetime.datetime.now().date())), local_stats)


# Main method.
if __name__ == '__main__':
    user = getpass.getuser()
    #upload_all_files('/home/{}/Pictures/Samples'.format(user))
    messageGenerator()
