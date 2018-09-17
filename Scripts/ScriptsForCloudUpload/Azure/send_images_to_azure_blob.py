#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 8 2018

@author: "Anirban Das"
"""

import os
import getpass
import datetime, sys, time, csv
from azure.storage.blob import BlockBlobService, PublicAccess


block_blob_service = BlockBlobService(account_name='<Storage Account Name>', 
				account_key='<Key 1 of the Storage Account>')

container_name ='<Container to Upload Files>'
# Create the BlockBlockService
block_blob_service.create_container(container_name)

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


def upload_all_files(foldername):
	local_stats = [['imagefilename', 'messagesendutctime', 'payloadsize']]
	global block_blob_service
	global container_name	
	count = 1
	try:
		all_file_names = sorted(os.listdir(os.path.expanduser(foldername)))
		for local_file_name in all_file_names:
			print("\nUploading to Blob storage as blob " + local_file_name)	
			full_path_to_file = os.path.join(foldername, local_file_name)
			# Upload the created file, use local_file_name for the blob name
			#block_blob_service.create_blob_from_path(container_name, local_file_name, full_path_to_file)
					
			local_stats.append([local_file_name, datetime.datetime.utcnow().isoformat(), os.path.getsize(full_path_to_file)])
			time.sleep(5)
			count= count+1
	except KeyboardInterrupt:
		print("cancelling Upload, image uploaded {}".format(count))
		print(e)
	finally:
		write_local_stats("Azure_image_local_stats_central{}.csv".format(str(datetime.datetime.now().date())), local_stats)


# Main method.
if __name__ == '__main__':
	user = getpass.getuser()
	upload_all_files('/home/{}/Pictures/Samples'.format(user))
