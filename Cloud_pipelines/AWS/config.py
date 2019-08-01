#==============================================================================
# ENTER PATH TO FOLDER CONTAINING DATA TO BE UPLOADED HERE
data_folder = "/home/tobias/Desktop/sample-data/Text"

# ENTER PATH TO FOLDER CONTAINING LAMBDA FUNCTION (AND SERVERLESS.YML FILE for AWS systems)
function_folder = "./Scalar-Pipeline/"

# ENTER SLEEP DELAY IN BETWEEN UPLOADS IN SECONDS. For example, if you want to upload an image every second, set sleep = 1. If you want to upload 4 images/sec, set sleep = 0.25.
upload_delay = 1

# Enter amount of time to wait for AWS to finish processing data here. Default is 60
wait_time = 7
#==============================================================================
