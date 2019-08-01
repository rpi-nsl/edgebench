#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 29 12:10:48 2019

@author: Anirban Das
"""

import os
from pocketsphinx import Pocketsphinx, get_model_path, get_data_path, AudioFile
from timeit import default_timer as timer
import json , csv
import datetime
import sys, logging

logging.basicConfig(format='%(asctime)s %(name)-20s %(levelname)-5s %(message)s')


# Initialize global variables -----------------------------------------------------------
AUDIO_DIRECTORY = os.getenv('AUDIO_DIRECTORY', default='/home/pi/Music/mountedDirectory')
STATS_DIRECTORY = os.getenv('STATS_DIRECTORY', default='/home/pi/AWS/mountedStatistics')

csvfilename = "PocketSphinx_stats_local_{}_{}.csv".format(str(datetime.datetime.now().date()), "AWS")

# Get all the file paths from the directory specified
def get_file_paths(dirname):
	file_paths = []
	for root, directories, files in os.walk(dirname):
		for filename in sorted(files):
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


def decode_out(decoder, audio_file=None, buffer_size=2048,
			   no_search=False, full_utt=False):
		f_t0 = timer()
		buf = bytearray(buffer_size)
		f_t1 = timer()
		with open(audio_file or decoder.goforward, 'rb') as f:
			f_t2 = timer()
			with decoder.start_utterance():
				f_t3 = timer()
				while f.readinto(buf):
					decoder.process_raw(buf, no_search, full_utt)
					f_t4 = timer()
			f_t5 = timer()
		f_t6 = timer()
		return decoder , f_t0, f_t1, f_t2, f_t3, f_t4, f_t5, f_t6

# Code for doing the actual speech 2 text conversion
def getSpeech2Text(client, outputQueueName='greengrass/audio_pipeline'):
	global AUDIO_DIRECTORY
	global csvfilename
	stall_for_connectivity()

	try:
		t1 = timer()
		all_file_paths = get_file_paths(AUDIO_DIRECTORY)
		t2 = timer()
		print("Got all files in {} seconds".format(t2 - t1))

		# get a pocketsphinx decoder
		ps_decoder = getPockerSphinxDecoder()
		t3 = timer()
		print("Got PockerSphinx Decoder in {} seconds".format(t3 - t2))

		local_stats = [['audiofilename', 'payloadsize', 'audiofilesize', 'audiofileobjectsize', 'starttime',
						"f_t0", "f_t1", "f_t1_1", "f_t2"]]

		count = 1
		for file in all_file_paths:
                        starttime = datetime.datetime.utcnow().isoformat()
                        f_t0 = timer()
			dictionary = {}
			ps_decoder.decode(audio_file=file,
			             buffer_size=2048,
			             no_search=False,
			             full_utt=False)

			# ps_decoder, f_t0, f_t1, f_t2, f_t3, f_t4, f_t5, f_t6 = decode_out(ps_decoder, audio_file=file,
			# 			buffer_size=2048,
			# 			no_search=False,
			# 			full_utt=False)
			translation = ps_decoder.hypothesis()
			f_t1 = timer()

			filename = file.split(os.sep)[-1]
			dictionary["audiofilename"] = filename
			dictionary["audiotranslation"] = translation
			dictionary["funccompleteutctime"] = datetime.datetime.utcnow().isoformat()
			json_payload = json.dumps(dictionary)
			f_t1_1 = timer()
			# Publish the Payload in the specific topic
			client.publish(topic=outputQueueName, payload=str(json_payload))

			f_t2 = timer()
			local_stats.append([filename, sys.getsizeof(json_payload), os.path.getsize(file), sys.getsizeof(file), starttime,
								f_t0, f_t1, f_t1_1, f_t2])

			print("Payload: ",json_payload)

			# write local stats to csv file
			# if count%100==0:
			# 	write_local_stats(csvfilename, local_stats)
			# 	local_stats = []
			count+=1


	except :
		e = sys.exc_info()[0]
		print("Exception occured during prediction: %s" % e)
		sys.exit(0)

	finally:
		write_local_stats(csvfilename, local_stats)
