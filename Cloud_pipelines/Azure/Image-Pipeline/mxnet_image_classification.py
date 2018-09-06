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

model_path = '.{}mxnet_models{}squeezenetv1.1{}'.format(os.sep, os.sep, os.sep)
global_model = load_model.ImagenetModel(model_path+'synset.txt', model_path+'squeezenet_v1.1')
logger.info("Entering classification")
print("loaded model in {}".format(timer()- time_start_read1))

def mxnet_image_classification(N=5, reshape=(224, 224)):
    if global_model is not None:
        try:
            dictionary = {}
            
            # Read the image from the folder
            time_start_read = timer()
            filename = "dummy"
            im = cv2.imread(os.environ['myBlob'])
            time_stop_read = timer()
            print("Read image {} in {} seconds".format(filename, time_stop_read - time_start_read))

            # Predict the classification from the image
            prediction = global_model.predict_from_image(im, reshape, N)
            time_end_prediction = timer()
            print("Predicted image {} in {} seconds".format(filename, time_end_prediction - time_stop_read))

            # Create the Payload JSON with the necessary fields
            for idx, elem in enumerate(prediction):
                temp_dict = {}
                temp_dict["probability"] = float(elem[0])
                temp_dict["wordnetid"], temp_dict["classification"] = elem[1].split(" ", 1)                    
                dictionary["classification_{}".format(idx)] = temp_dict
            # CANNOT PULL IMAGEFILENAME
            dictionary["imageiotime"] = time_stop_read - time_start_read
            dictionary["predictiontime"] = time_end_prediction - time_stop_read
            dictionary["totalcomputetime"] = timer() - time_start_read
            dictionary["messagesendutctime"] = datetime.datetime.utcnow().isoformat()
            dictionary["totalfunctiontime"] = timer()- time_start_read1
            json_payload = json.dumps(dictionary)
            
            # Output the modified file to a separate folder in the Storage Blob
            output_file = open(os.environ['outputBlob'], 'w')
            output_file.write(json_payload)
            output_file.close()
            
            logging.info(json_payload)
            print("Payload: ",json_payload)
            print("All procedure for {} done in {} seconds. \n".format(filename, timer() - time_start_read))

        except Exception as ex:
            e = sys.exc_info()[0]
            print("Exception occured during prediction: %s" % e)
            print("Exception: %s" % ex)
            sys.exit(0)