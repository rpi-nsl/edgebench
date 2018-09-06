from timeit import default_timer as timer
time_start_read1 = timer()
import sys
import os
import time
import platform
import load_model
import json
import cv2
import tempfile
import logging
import datetime


logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

results_bucket = os.getenv('RESULTS_BUCKET')
print(results_bucket)

model_path = '.{}mxnet_models{}squeezenetv1.1{}'.format(os.sep, os.sep, os.sep)
global_model = load_model.ImagenetModel(model_path+'synset.txt', model_path+'squeezenet_v1.1')
logger.info("Entering classification")
print("loaded model in {}".format(timer()- time_start_read1))

def mxnet_image_classification(client, event, N=5, reshape=(224, 224)):
    if global_model is not None:
        try:
            #for record in event['Records']:
            record = event['Records'][0]
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            logger.info("key = {} and bucket = {}".format(key, bucket))
            
            # Access the image from the S3 bucket
            time_start_access = timer()
            tmp = tempfile.NamedTemporaryFile()
            client.download_file(bucket, key, tmp.name)
            tmp.flush()

            # Read the image from the folder
            time_start_read = timer()
            im = cv2.imread(tmp.name)
            time_stop_read = timer()    
            print("Read image {} in {} seconds".format(tmp.name, time_stop_read - time_start_read))
            
            dictionary = {}
            N = 5
            
            # Predict the classification from the image
            prediction = global_model.predict_from_image(im, reshape, N)
            time_end_prediction = timer()
            print("Predicted image {} in {} seconds".format(tmp.name, time_end_prediction - time_stop_read))
            
            # Create the Payload JSON with the necessary fields
            for idx, elem in enumerate(prediction):
                temp_dict = {}
                temp_dict["probability"] = float(elem[0])
                temp_dict["wordnetid"], temp_dict["classification"] = elem[1].split(" ", 1)                    
                dictionary["classification_{}".format(idx)] = temp_dict
            dictionary["imagefilename"] = key
            dictionary["imageiotime"] = time_stop_read - time_start_access
            dictionary["predictiontime"] = time_end_prediction - time_stop_read
            dictionary["totalcomputetime"] = timer() - time_start_access
            dictionary["totalfunctiontime"] = timer()- time_start_read1
            dictionary["messagesendutctime"] = datetime.datetime.utcnow().isoformat()
            
            json_payload = json.dumps(dictionary)
            tmp = tempfile.NamedTemporaryFile()
            tmp.write(json_payload)
            tmp.flush()

            client.upload_file(tmp.name, results_bucket, "{}.json".format(key))
            logger.info(msg="Payload: {}".format(json_payload))
        except:
            e = sys.exc_info()[0]
            print("Exception occured during prediction: %s" % e)