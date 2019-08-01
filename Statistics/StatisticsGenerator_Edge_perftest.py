#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul 28 12:37:25 2018

@author: "Anirban Das"
"""

import logging
import json
import avro.datafile
import sys
from azure.storage.blob import BlockBlobService
import avro.io
import io
import pandas as pd
import dateutil.parser
import numpy as np
import matplotlib.pyplot as plt
import boto3
from operator import itemgetter
from tqdm import tqdm

font = {'weight' : 'normal',
        'size'   : 20}


logging.basicConfig(
	format='%(asctime)s|%(name).10s|%(levelname).5s: %(message)s',
	level=logging.WARNING)
logger = logging.getLogger('StatisticsGenerator')
logger.setLevel(logging.DEBUG)

class StatisticsGenerator(object):
	def __init__(self, pipeline, architecture, config):
		super(StatisticsGenerator, self).__init__()
		
		self.pipeline = pipeline
		self.architecture = architecture
		
		with open(config, 'r') as f:
			self.config = json.load(f)
		
		if 'azure' in self.architecture.lower():
			self.generator, self.block_blob_service = self.getBlobGeneratorService()
			"""
				tokens are for identifying which blobs to look for specifically in a container
			"""
			self.audioblobtoken = self.config['AZURE_CONFIG']['AUDIO_BLOB_TOKEN'] if self.config['AZURE_CONFIG']['AUDIO_BLOB_TOKEN'] else "audio"
			self.imageblobtoken = self.config['AZURE_CONFIG']['IMAGE_BLOB_TOKEN'] if self.config['AZURE_CONFIG']['IMAGE_BLOB_TOKEN'] else "image"
			self.scalarblobtoken = self.config['AZURE_CONFIG']['SCALAR_BLOB_TOKEN'] if self.config['AZURE_CONFIG']['SCALAR_BLOB_TOKEN'] else "scalar"
			
			
		elif 'aws' in self.architecture.lower():
			self.current_session = boto3.session.Session(aws_access_key_id=self.config['AWS_CONFIG']['aws_access_key_id'],
								aws_secret_access_key=self.config['AWS_CONFIG']['aws_secret_access_key'],
								region_name=self.config['AWS_CONFIG']['region_name'])
			# Create an S3 client
			self.s3_client = self.current_session.client('s3')
			self.s3_resource = self.current_session.resource('s3')
		
	
	def getLocalStats(self):
		"""
			Returns: pandas DataFrame, each row  = ['filename', 'io_time', 'prediction_time', 'total_compute_time', 'payloadsize'] or
			[['filename', 'total_compute_time', 'payloadsize']]
		"""
		stats_file_path = self.getStatsFilePath()
		all_data = np.genfromtxt(stats_file_path, dtype=None, delimiter=',', names=True)
		print(stats_file_path)
		if 'image' in self.pipeline.lower():
			imagefilename = all_data['imagefilename'].astype('U').reshape((all_data['imagefilename'].shape[0], 1))
			for idx, val in enumerate(imagefilename):
				imagefilename[idx][0] = imagefilename[idx][0].split('/')[-1]
			imageiotime = 1000 * all_data['imageiotime'].reshape((all_data['imageiotime'].shape[0], 1))
			predictiontime = 1000 * all_data['predictiontime'].reshape((all_data['predictiontime'].shape[0], 1))
			totalcomputetime = 1000 * all_data['totalcomputetime'].reshape((all_data['totalcomputetime'].shape[0], 1))
			payloadsize = all_data['payloadsize'].reshape((all_data['payloadsize'].shape[0], 1))
			
			payload_df = pd.DataFrame(np.hstack((imagefilename, imageiotime, predictiontime, totalcomputetime, payloadsize)),
							 columns=['filename', 'io_time', 'prediction_time', 'total_compute_time', 'payloadsize'])
			cols = ['io_time', 'prediction_time', 'total_compute_time', 'payloadsize']
			payload_df[cols]= payload_df[cols].apply(pd.to_numeric)
			return payload_df
		
		elif 'audio' in self.pipeline.lower():
			audiofilename = all_data['audiofilename'].astype('U').reshape((all_data['audiofilename'].shape[0], 1))
			for idx, val in enumerate(audiofilename):
				audiofilename[idx][0] = audiofilename[idx][0].split('/')[-1]
			totalcomputetime = 1000 * all_data['totalcomputetime'].reshape((all_data['totalcomputetime'].shape[0], 1)).astype(float)
			payloadsize = all_data['payloadsize'].reshape((all_data['payloadsize'].shape[0], 1)).astype(float)
			
			payload_df = pd.DataFrame(np.hstack((audiofilename, totalcomputetime, payloadsize )), 
					   columns=['filename', 'total_compute_time', 'payloadsize'])
			payload_df[['total_compute_time', 'payloadsize']]= payload_df[['total_compute_time', 'payloadsize']].apply(pd.to_numeric)
			return payload_df
		
		elif 'scalar' in self.pipeline.lower():
			messageid = all_data['messageid'].astype('U').reshape((all_data['messageid'].shape[0], 1))
			totalcomputetime = 1000 * all_data['totalcomputetime'].reshape((all_data['totalcomputetime'].shape[0], 1)).astype(float)
			payloadsize = all_data['payloadsize'].reshape((all_data['payloadsize'].shape[0], 1)).astype(float)
			
			payload_df = pd.DataFrame(np.hstack((messageid, totalcomputetime, payloadsize )), 
					   columns=['filename', 'total_compute_time', 'payloadsize'])
			payload_df[['total_compute_time', 'payloadsize']]= payload_df[['total_compute_time', 'payloadsize']].apply(pd.to_numeric)
			return payload_df
	
	def getBlobGeneratorService(self):
	    # EdCreate the BlockBlockService that is used to call the Blob service for the storage account
		block_blob_service = BlockBlobService(account_name=self.config['AZURE_CONFIG']['account_name'],
											  account_key=self.config['AZURE_CONFIG']['account_key'])
		# List the blobs in the container
		container_name = self.getPipelineContainer()
		print("\nList blobs in the container")
		generator = block_blob_service.list_blobs(container_name)
		return generator, block_blob_service
	
	def getBlobPayload(self, blob, block_blob_service ):
		container_name = self.getPipelineContainer()
		blob_bytes = block_blob_service.get_blob_to_bytes(container_name, blob.name)
		avro_content = blob_bytes.content
		last_modified = blob_bytes.properties.last_modified.isoformat()
		content_bytes = io.BytesIO(avro_content)
		all_payloads = avro.datafile.DataFileReader(content_bytes, avro.io.DatumReader())
		return all_payloads, last_modified
	
	def getPipelineContainer(self):
		if 'audio' in self.pipeline:
			container_name = self.config['AZURE_CONFIG']['AUDIO_PIPELINE_CONTAINER']
			bucket_name    = self.config['AWS_CONFIG']["AUDIO_BUCKET"]
		elif 'image' in self.pipeline:
			container_name = self.config['AZURE_CONFIG']['IMAGE_PIPELINE_CONTAINER']
			bucket_name    = self.config['AWS_CONFIG']["IMAGE_BUCKET"]
		else:
			container_name = self.config['AZURE_CONFIG']['SCALAR_PIPELINE_CONTAINER']
			bucket_name    = self.config['AWS_CONFIG']["SCALAR_BUCKET"]
		
		if 'azure' in self.architecture.lower() :
			return container_name
		else:
			return bucket_name
	
	def getOutputFileFilePath(self):
		if 'azure' in self.architecture.lower():
			if 'image' in self.pipeline.lower() : 
				return self.config['AZURE_CONFIG']['IMAGE_OUTPUT_FILE']
			elif 'audio' in self.pipeline.lower() :
				return self.config['AZURE_CONFIG']['AUDIO_OUTPUT_FILE']
			else:
				return self.config['AZURE_CONFIG']['SCALAR_OUTPUT_FILE']
				 
		elif 'aws' in self.architecture.lower():
			if 'image' in self.pipeline.lower() : 
				return self.config['AWS_CONFIG']['IMAGE_OUTPUT_FILE']
			elif 'audio' in self.pipeline.lower() :
				return self.config['AWS_CONFIG']['AUDIO_OUTPUT_FILE']
			else:
				return self.config['AWS_CONFIG']['SCALAR_OUTPUT_FILE']
		else:
			print("Unknown Architecture. Exiting...")
			return

	def getStatsFilePath(self):
		if 'azure' in self.architecture.lower():
			if 'image' in self.pipeline.lower() : 
				return self.config['AZURE_CONFIG']['IMAGE_LOCAL_STATS_FILE']
			elif 'audio' in self.pipeline.lower() :
				return self.config['AZURE_CONFIG']['AUDIO_LOCAL_STATS_FILE']
			else:
				return self.config['AZURE_CONFIG']['SCALAR_LOCAL_STATS_FILE']
				 
		elif 'aws' in self.architecture.lower():
			if 'image' in self.pipeline.lower() : 
				return self.config['AWS_CONFIG']['IMAGE_LOCAL_STATS_FILE']
			elif 'audio' in self.pipeline.lower() :
				return self.config['AWS_CONFIG']['AUDIO_LOCAL_STATS_FILE']
			else:
				return self.config['AWS_CONFIG']['SCALAR_LOCAL_STATS_FILE']
		else:
			print("Unknown Architecture. Exiting...")

	
	def getCloudStats(self, skipblobs = True):
		"""
			Returns: numpy array agg_details = [['filename', 'flight_time', 'iothub_time', 'end_to_end_time']]
		"""
		if 'azure' in self.architecture.lower():
			return self.getAzureCloudStats(skipblobs)
				 
		elif 'aws' in self.architecture.lower():
			return self.getAWSCloudStats()
		else:
			print("Unknown Architecture. Exiting...")
			return
		
	

	def getAWSCloudStats(self):
		"""
			Returns: numpy array agg_details = [['filename', 'flight_time', 'iothub_time', 'end_to_end_time', 'messagesendutctime', 'iothubutctime', 's3creationutctime', 'audiotranslation' ]]
		"""
		outputfilepath = self.getOutputFileFilePath()
		
		bucket_name = self.getPipelineContainer()

		# Define a bucket using high level API
		aws_bucket = self.s3_resource.Bucket(bucket_name)
	
		# list all objects in the bucket
		# (http://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Bucket.objects)
		all_json_objects = list(aws_bucket.objects.all())
		logger.info(msg=all_json_objects[0].get())
	
		payloads = []
		response_meta_data = []
	
		# to aggregate and find the average flight , compute and i/o times
		agg_details = []
	
		with open(outputfilepath, "w") as file:
			try:
				message_count = 1
				for json_object in tqdm(all_json_objects):
					object_data = json_object.get()
					payload_dict = json.loads(object_data["Body"].read().decode("utf-8"))
					objectputinS3utctime = object_data['LastModified'].isoformat()
					payload_dict.update({'objectputinS3utctime': objectputinS3utctime})
	
					#payloads.append(json.dumps(payload_json))
					payloads.append(payload_dict)
					response_meta_data.append(object_data['ResponseMetadata'])
					
					message_send_UTC_time = dateutil.parser.parse(payload_dict['messagesendutctime'])		
					iothub_timestamp = dateutil.parser.parse(payload_dict['iothub_timestamp'])
					object_put_in_s3_UTC_time =  dateutil.parser.parse(payload_dict['objectputinS3utctime']).replace(tzinfo=None)
					
					time_in_flight = (iothub_timestamp - message_send_UTC_time).total_seconds()
					time_in_hub = (object_put_in_s3_UTC_time - iothub_timestamp).total_seconds()
					end_to_end_time = (object_put_in_s3_UTC_time - message_send_UTC_time).total_seconds()
					 
					if 'image' in self.pipeline:
						filename = payload_dict['imagefilename'].split('/')[-1]
					elif 'audio' in self.pipeline:
						filename = payload_dict['audiofilename'].split('/')[-1]
					elif 'scalar' in self.pipeline:
						filename = str(payload_dict['messageid'])
							
					# adds in the aggregate to find the average later
					agg_details.append([filename, time_in_flight* 1000, time_in_hub* 1000, end_to_end_time* 1000,
									 message_send_UTC_time, iothub_timestamp, object_put_in_s3_UTC_time, payload_dict["audiotranslation"]])
					# ==============================================================================================
					file.write(str(payload_dict)+'\n')
					message_count = message_count + 1
				
				return pd.DataFrame(agg_details, columns=['filename', 'flight_time', 'iothub_time', 'end_to_end_time', 'messagesendutctime', 'iothubutctime', 's3creationutctime', 'audiotranslation'])
			
			except Exception as e:
				print("Ann Exception has occured: " + str(e))
	

	def getAzureCloudStats(self, skipblobs = True):
		"""
			Returns: numpy array agg_details = ['filename', 'flight_time', 'iothub_time', 'end_to_end_time', 'messagesendutctime', 'iothubutctime', 'blobmodifiedutctime']
		"""
		# to aggregate and find the average flight , compute and i/o times
		agg_details = []
		
		outputfilepath = self.getOutputFileFilePath()
		file_in_single_folder_count=0
		with open(outputfilepath , 'w') as file:
			try:
				generator, block_blob_service = self.getBlobGeneratorService()
				message_count = 1
				blob_count = 1
				print("Sfsfsdf")
				for blob in generator:
					if ( self.imageblobtoken in blob.name and 'image' in self.pipeline) or \
											(self.audioblobtoken in blob.name and 'audio' in self.pipeline) or \
											( self.scalarblobtoken in blob.name and 'scalar' in self.pipeline):
						
						# Skip the first two blobs if skipblobs flag is True
						if (blob_count == 1 or blob_count ==2) and skipblobs:
							blob_count+=1
							continue
						#print(blob.properties.__dict__)
						#print("\t Blob name: " + str(blob.name))
						
						all_payloads, last_modified = self.getBlobPayload(blob, block_blob_service)
						file_in_single_folder_count = 0
						for body in all_payloads:
							payload_dict = json.loads(body['Body'].decode('utf-8'))
							#print(payload_dict)
							#print(body)
							
							message_send_UTC_time = dateutil.parser.parse(payload_dict['messagesendutctime'])
							iothub_timestamp = dateutil.parser.parse(body['EnqueuedTimeUtc']).replace(tzinfo=None)
							object_put_in_blob_UTC_time = dateutil.parser.parse(last_modified).replace(tzinfo=None)
							#decodingtime = payload_json['decodingtime']
							
							time_in_flight = (iothub_timestamp - message_send_UTC_time ).total_seconds()
							time_in_hub = (object_put_in_blob_UTC_time - iothub_timestamp).total_seconds()   
							end_to_end_time = ( object_put_in_blob_UTC_time - message_send_UTC_time).total_seconds()
							
							if 'image' in self.pipeline:
								filename = payload_dict['imagefilename'].split('/')[-1]
							elif 'audio' in self.pipeline:
								filename = payload_dict['audiofilename'].split('/')[-1]	
							elif 'scalar' in self.pipeline:
								filename = str(payload_dict['messageid'])
							
							# adds in the aggregate to find the average later
							agg_details.append([filename, time_in_flight* 1000, time_in_hub* 1000, end_to_end_time* 1000 , 
										   message_send_UTC_time, iothub_timestamp,object_put_in_blob_UTC_time ])
							# ==============================================================================================     
							file.write(str(payload_dict)+'\n')
							message_count = message_count +1
							file_in_single_folder_count +=1
						print("There are {} files in blob {}".format(file_in_single_folder_count, blob.name))
						blob_count+=1
				
				"""
					remove details of the last blob because it may be incomplete
					if skipblob flag is True
				"""
				if skipblobs:
					agg_details = agg_details[: -file_in_single_folder_count]
					
				return pd.DataFrame(agg_details, 
						columns=['filename', 'flight_time', 'iothub_time', 'end_to_end_time', 'messagesendutctime', 'iothubutctime', 'blobmodifiedutctime' ])
				
			except Exception as e:
				print("An Exception has occured: " + str(e))
	
	def getandPlotCDFPercentile(self, metric_values, metric_name,  no_display_flag=False):
		'''
		Plots the CDF graph of the metric passed into the function.
		Prints out the Average, Variance, STD and MAX, MIN of the metric
		
		Args:
	        metric_values (ndarray): Python ndarray of the metric.
	        metric_name (str)      : The metric name.
		
		Returns:
	        float: avg_metric. The average value of the metric
		'''
		
		if not no_display_flag:
			# Plot the cfds
			num_bins = self.config['CDF_BINS']
			counts, bin_edges = np.histogram (metric_values, bins=num_bins, normed=True)
			cdf = np.cumsum (counts)
			plt.figure()
			plt.plot (bin_edges[1:], cdf/cdf[-1])
			if 'size' in metric_name.lower():
				plt.xlabel("Message Sixe in bytes")
			else:
				plt.xlabel("Time in Milliseconds")
			plt.ylabel("Probability")
			plt.title("CDF plot of {} for {} pipeline".format(metric_name, self.pipeline))
			plt.grid()
			plt.savefig("Images/CDF_{}_{}_{}.pdf".format(self.architecture, self.pipeline.upper(), metric_name), bbox_inches='tight')
			plt.close()
			
			# Print the percentiles
			print("%%%%%%%%%%%%%%%%%%%%%%%%%% {} {} of {} pipeline %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%".format(self.architecture, metric_name, self.pipeline))
			for percentile in [50, 90, 95, 100]:
				print ("{}% percentile for {} {}: {}".format (percentile, self.architecture, metric_name, np.percentile(metric_values, percentile)))
			
		unit	 = 'bytes' if 'size' in metric_name.lower() else 'ms'
		avg_metric = np.mean(metric_values)
		std_metric = np.std(metric_values)
		print("\n\nTotal messages {}".format(len(metric_values)))
		print("Average {} per message  : {} {}".format(metric_name, avg_metric, unit))
		print("Variance of {}  : {}".format(metric_name, np.var(metric_values)))
		print("Std. of {}  : {}".format(metric_name, std_metric))
		print("Max {}  : {} {}".format(metric_name, np.max(metric_values), unit))
		print("Min {}  : {} {} \n\n".format(metric_name, np.min(metric_values), unit))
		
		return avg_metric, std_metric


def plotBarGraphs(metric_list , metric_names):
	y_pos = np.arange(len(metric_names))
	plt.figure()
	plt.bar(y_pos, metric_list, align='center', alpha=0.5)
	plt.xticks(y_pos, metric_names)
	plt.ylabel('Time in Milliseconds')
	plt.title('Different compute times') 
	plt.show()

def append_nones(length, list_):
    """
    Appends Nones to list to get length of list equal to `length`.
    If list is too long raise AttributeError
    """
    diff_len = length - len(list_)
    if diff_len < 0:
        raise AttributeError('Length error list is too long.')
    return list_ + [None] * diff_len
# =============================================================================
# def main():
# 	fire.Fire(StatisticsGenerator)
# =============================================================================

if __name__ == '__main__':
	#main()
# =============================================================================
# 	prefix = "2018-20-08-run3"
# 	aggregate_folder = "AggregateResults"
# 	drop_first_rows= 10
# =============================================================================
	
	statisticsgenerator_aws_audio = StatisticsGenerator('audio', 'aws', 'Config/config.json')
	agg_audio_aws_cloud = statisticsgenerator_aws_audio.getCloudStats()
	agg_audio_aws_cloud.to_csv("Cloud_details_greengrass.csv")
# =============================================================================
# 	agg_audio_aws_local = statisticsgenerator_aws_audio.getLocalStats()
# 	all_aws_audio =  agg_audio_aws_cloud.set_index('filename').join(agg_audio_aws_local.set_index('filename'))
# 	avg_aws_audio_flight_time , std_aws_audio_flight_time =    statisticsgenerator_aws_audio.getandPlotCDFPercentile(np.array(all_aws_audio.loc[:, 'flight_time']).astype(float), "Flight Time", True)
# 	avg_aws_audio_iothub_time, std_aws_audio_iothub_time  =    statisticsgenerator_aws_audio.getandPlotCDFPercentile(np.array(all_aws_audio.loc[:, 'iothub_time']).astype(float), "IoT Hub Time", True)
# 	avg_aws_audio_endtoend_time, std_aws_audio_endtoend_time = statisticsgenerator_aws_audio.getandPlotCDFPercentile(np.array(
# 	all_aws_audio.loc[:, 'end_to_end_time'] + all_aws_audio.loc[:, 'total_compute_time']).astype(float), "End to End Time", True)
# 	#all_aws_audio.to_csv("AggregateResults/{}_aws_audio.csv".format(prefix))
# 	
# 	
# 	statisticsgenerator_aws_image = StatisticsGenerator('image', 'aws', 'Config/config.json')
# 	agg_image_aws_cloud = statisticsgenerator_aws_image.getCloudStats()
# 	agg_image_aws_local = statisticsgenerator_aws_image.getLocalStats()
# 	all_aws_image = agg_image_aws_cloud.set_index('filename').join(agg_image_aws_local.set_index('filename'))
# 	avg_aws_image_flight_time , std_aws_image_flight_time =    statisticsgenerator_aws_image.getandPlotCDFPercentile(np.array(all_aws_image.loc[:, 'flight_time']).astype(float), "Flight Time", True)
# 	avg_aws_image_iothub_time, std_aws_image_iothub_time  =    statisticsgenerator_aws_image.getandPlotCDFPercentile(np.array(all_aws_image.loc[:, 'iothub_time']).astype(float), "IoT Hub Time", True)
# 	avg_aws_image_endtoend_time, std_aws_image_endtoend_time = statisticsgenerator_aws_image.getandPlotCDFPercentile(np.array(
# 			all_aws_image.loc[:, 'end_to_end_time'] + all_aws_image.loc[:, 'total_compute_time']).astype(float), "End to End Time", True)
# 	#all_aws_image.to_csv("AggregateResults/{}_aws_image.csv".format(prefix))
# 	
# 	
# 	
# 	statisticsgenerator_aws_scalar = StatisticsGenerator('scalar', 'aws', 'Config/config.json')
# 	agg_scalar_aws_cloud = statisticsgenerator_aws_scalar.getCloudStats()
# 	agg_scalar_aws_local = statisticsgenerator_aws_scalar.getLocalStats()
# 	agg_scalar_aws_cloud['filename'] = agg_scalar_aws_cloud['filename'].astype(int)
# 	agg_scalar_aws_local['filename'] = agg_scalar_aws_local['filename'].astype(int)
# 	agg_scalar_aws_cloud = agg_scalar_aws_cloud.sort_values(by='filename').reset_index(drop=True)
# 	# discard some messages from beginning when things are being set up
# 	agg_scalar_aws_cloud = agg_scalar_aws_cloud.iloc[drop_first_rows:].reset_index(drop=True)
# 	
# 	all_aws_scalar = agg_scalar_aws_cloud.set_index('filename').join(agg_scalar_aws_local.set_index('filename'))
# 	avg_aws_scalar_flight_time , std_aws_scalar_flight_time =    statisticsgenerator_aws_scalar.getandPlotCDFPercentile(np.array(all_aws_scalar.loc[:, 'flight_time']).astype(float), "Flight Time", True)
# 	avg_aws_scalar_iothub_time, std_aws_scalar_iothub_time  =    statisticsgenerator_aws_scalar.getandPlotCDFPercentile(np.array(all_aws_scalar.loc[:, 'iothub_time']).astype(float), "IoT Hub Time", True)
# 	avg_aws_scalar_endtoend_time, std_aws_scalar_endtoend_time = statisticsgenerator_aws_scalar.getandPlotCDFPercentile(np.array(
# 			all_aws_scalar.loc[:, 'end_to_end_time'] + all_aws_scalar.loc[:, 'total_compute_time']).astype(float), "End to End Time", True)
# 	#all_aws_scalar.to_csv("AggregateResults/{}_aws_scalar.csv".format(prefix))
# 
# 
# #-----------------------------------_  AZURE -----------------------------------------	
# 	
# 
# 	statisticsgenerator_azure_audio = StatisticsGenerator('audio', 'azure', 'Config/config.json')
# 	agg_audio_azure_cloud = statisticsgenerator_azure_audio.getCloudStats(skipblobs = False)
# 	agg_audio_azure_local = statisticsgenerator_azure_audio.getLocalStats()
# 	all_azure_audio =  agg_audio_azure_cloud.set_index('filename').join(agg_audio_azure_local.set_index('filename'))
# 	all_azure_audio["end_to_end_time"] = all_azure_audio["end_to_end_time"] + all_azure_audio["total_compute_time"]
# 	avg_azure_audio_flight_time , std_azure_audio_flight_time =    statisticsgenerator_azure_audio.getandPlotCDFPercentile(np.array(all_azure_audio.loc[:, 'flight_time']).astype(float), "Flight Time", True)
# 	avg_azure_audio_iothub_time, std_azure_audio_iothub_time  =    statisticsgenerator_azure_audio.getandPlotCDFPercentile(np.array(all_azure_audio.loc[:, 'iothub_time']).astype(float), "IoT Hub Time", True)
# 	avg_azure_audio_endtoend_time, std_azure_audio_endtoend_time = statisticsgenerator_azure_audio.getandPlotCDFPercentile(np.array(all_azure_audio.loc[:, 'end_to_end_time']).astype(float), "End to End Time", True)
# 	#all_azure_audio.to_csv("{}/{}_azure_audio.csv".format(aggregate_folder,prefix))
# 	
# 	
# 	statisticsgenerator_azure_image = StatisticsGenerator('image', 'azure', 'Config/config.json')
# 	agg_image_azure_cloud = statisticsgenerator_azure_image.getCloudStats(skipblobs = False)
# 	agg_image_azure_local = statisticsgenerator_azure_image.getLocalStats()
# 	all_azure_image = agg_image_azure_cloud.set_index('filename').join(agg_image_azure_local.set_index('filename'))
# 	all_azure_image["end_to_end_time"] = all_azure_image["end_to_end_time"] + all_azure_image["total_compute_time"]
# 	avg_azure_image_flight_time , std_azure_image_flight_time =    statisticsgenerator_azure_image.getandPlotCDFPercentile(np.array(all_azure_image.loc[:, 'flight_time']).astype(float), "Flight Time", True)
# 	avg_azure_image_iothub_time, std_azure_image_iothub_time  =    statisticsgenerator_azure_image.getandPlotCDFPercentile(np.array(all_azure_image.loc[:, 'iothub_time']).astype(float), "IoT Hub Time", True)
# 	avg_azure_image_endtoend_time, std_azure_image_endtoend_time = statisticsgenerator_azure_image.getandPlotCDFPercentile(np.array(all_azure_image.loc[:, 'end_to_end_time']).astype(float), "End to End Time", True)
# 	#all_azure_image.to_csv("{}/{}_azure_image.csv".format(	aggregate_folder, prefix))
# 	
# 	statisticsgenerator_azure_scalar = StatisticsGenerator('scalar', 'azure', 'Config/config.json')
# 	agg_scalar_azure_cloud = statisticsgenerator_azure_scalar.getCloudStats(skipblobs = False)
# 	agg_scalar_azure_local = statisticsgenerator_azure_scalar.getLocalStats()
# 	all_azure_scalar = agg_scalar_azure_cloud.set_index('filename').join(agg_scalar_azure_local.set_index('filename'))
# 	all_azure_scalar["end_to_end_time"] = all_azure_scalar["end_to_end_time"] + all_azure_scalar["total_compute_time"]
# 	all_azure_scalar = all_azure_scalar.dropna()
# 	avg_azure_scalar_flight_time , std_azure_scalar_flight_time =    statisticsgenerator_azure_scalar.getandPlotCDFPercentile(np.array(all_azure_scalar.loc[:, 'flight_time']).astype(float), "Flight Time", True)
# 	avg_azure_scalar_iothub_time, std_azure_scalar_iothub_time  =    statisticsgenerator_azure_scalar.getandPlotCDFPercentile(np.array(all_azure_scalar.loc[:, 'iothub_time']).astype(float), "IoT Hub Time", True)
# 	avg_azure_scalar_endtoend_time, std_azure_scalar_endtoend_time = statisticsgenerator_azure_scalar.getandPlotCDFPercentile(np.array(all_azure_scalar.loc[:, 'end_to_end_time']).astype(float), "End to End Time", True)
# 	#all_azure_scalar.to_csv("AggregateResults/{}_azure_scalar.csv".format(prefix))
# 	
# 	print("AWS   audio total compute time {}".format(all_aws_audio.total_compute_time.mean()))
# 	print("AWS   audio payload size {}".format(all_aws_audio.payloadsize.mean()))
# 	
# 	print("AWS   image total compute time {}".format(all_aws_image.total_compute_time.mean()))
# 	print("AWS   image payload size {}".format(all_aws_image.payloadsize.mean()))
# 	
# 	print("AWS   scalar total compute time {}".format(all_aws_scalar.total_compute_time.mean()))
# 	print("AWS   scalar payload size {}".format(all_aws_scalar.payloadsize.mean()))
# 	
# 	print("Azure audio total compute time {} ".format(all_azure_audio.total_compute_time.mean()))
# 	print("Azure audio payload size {} ".format(all_azure_audio.payloadsize.mean()))
# 	
# 	print("Azure image total compute time {} ".format(all_azure_image.total_compute_time.mean()))
# 	print("Azure image payload size {} ".format(all_azure_image.payloadsize.mean()))
# 	
# 	print("Azure scalar total compute time {} ".format(all_azure_scalar.total_compute_time.mean()))
# 	print("Azure scalar payload size {} ".format(all_azure_scalar.payloadsize.mean()))
# 	
# =============================================================================
	# #--------------------------------------------------------------------------
	# """ Local Throughput Measure """
	
	# time = pd.DatetimeIndex(all_aws_audio.messagesendutctime)
	# all_aws_audio_throughput = list(all_aws_audio.groupby([time.minute]).count()['messagesendutctime'])
	
	# time = pd.DatetimeIndex(all_aws_image.messagesendutctime)
	# all_aws_image_throughput = list(all_aws_image.groupby([time.minute]).count()['messagesendutctime'])
	
	# time = pd.DatetimeIndex(all_azure_audio.messagesendutctime)
	# all_azure_audio_throughput = list(all_azure_audio.groupby([time.minute]).count()['messagesendutctime'])
	
	# time = pd.DatetimeIndex(all_azure_image.messagesendutctime)
	# all_azure_image_throughput = list(all_azure_image.groupby([time.minute]).count()['messagesendutctime'])
	
	# max_length = max(len(all_aws_audio_throughput), len(all_aws_image_throughput), len(all_azure_audio_throughput), len(all_azure_image_throughput))
	
	# plt.plot(list(range(max_length)), append_nones(max_length,all_azure_audio_throughput), label="Azure Audio")
	# plt.plot(list(range(max_length)), append_nones(max_length, all_aws_audio_throughput), label="Greengrass Audio")	
	# plt.plot(list(range(max_length)), append_nones(max_length, all_aws_image_throughput), label="Greengrass Image")	
	# plt.plot(list(range(max_length)), append_nones(max_length, all_azure_image_throughput), label="Azure Image")
	# plt.xlabel("Minutes")
	# plt.ylabel("Throughput: Messages / Minute")
	# plt.legend()
		
		
		
		
		
		
		
		
		
		
		
		
		