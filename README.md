
#### What is EdgeBench?
EdgeBench is an open-source benchmark suite for serverless edge computing platforms. EdgeBench features these key applications: 

- A speech/audio-to-text decoder (uses [pocketsphinx-python](https://github.com/bambocher/pocketsphinx-python))
- An image recognition machine learning model (used [MXNet](https://github.com/apache/incubator-mxnet) internally)
- A scalar value generator emulating a temperature -humidity sensor
- A face detection application using [dlib](http://dlib.net/)
- A matrix dimension reduction application using PCA in `Numpy`
- A image resizing application using [Pillow](https://pillow.readthedocs.io/en/stable/)

Each application processes a bank of input data on an edge device and sends results to cloud storage. We target EdgeBench for two of the most popular edge computing platforms currently available, [AWS Greengrass](https://aws.amazon.com/greengrass/) and [Microsoft Azure IoT Edge](https://azure.microsoft.com/en-us/services/iot-edge/) , to compare not only the edge platforms to each other but also to the providers’ respective cloud-only alternatives, EdgeBench also provides cloud-based workload implementations.


## For more details look into the [Quick Start](https://github.com/akaanirban/edgebench_dev/wiki/Quick-Start)

#### EdgeBench Folder Structure

```
edgebench
│   README.md
│
│
└───Cloud_pipelines
│   │   
│   └───AWS
│   |   │   Audio-Pipeline (All files related to Audio/Speech to Text in AWS cloud)
│   |   │   Image-Pipeline (All files related to Image Recognition in AWS cloud)
│   |   │   Scalar-Pipeline (All files related to Scalar Values Generator in AWS cloud)
|   |
│   └───Azure
│       │   Audio-Pipeline (All files related to Audio/Speech to Text in Azure cloud)
│       │   Image-Pipeline (All files related to Image Recognition in Azure cloud)
|       
└───Data_upload_download (Scripts for uploading files to cloud / downloading benchmark data)
│
│
└───Edge_Pipelines
│   │   
│   └───AWS
│   |   │   lambdas (All files related to the audio, image, and scalar pipeline functions in Greengrass)
│   |   │   certs, config, initial_setup (Configuration folders used by EdgeBench)
|   |
│   └───Azure
│       │   Audio-Pipeline (All files related to Audio/Speech to Text in Azure IoT Edge)
│       │   Image-Pipeline  (All files related to Image Recognition in Azure IoT Edge)
│       │   Scalar-Pipeline  (All files related to Scalar Pipeline in Azure IoT Edge)
|
└───InputData
│   │   
│   └───Audio (sample audio files for Audio Pipeline)
│   │   
│   └───Image (sample Image files for Image Pipeline)
│
│
└───Scripts
│   │   
│   └───ScriptsForCloudUpload (OBSOLETE)  (Old depreciated scripts for uploading; use Data_upload_download instead)
│   |   │   AWS (All scripts needed to upload files in S3 bucket)
│   |   │   Azure (All scripts needed to upload files in Azure Blob Storage)
│   |
|   └─── remote_directory_setup.sh (To set up the folders in remote edge device)
|   └─── config.yaml (Settings foe the above directory setup)
|   └─── yaml.sh (Library required for parsing `yaml` files shell scripts)
|   └─── convert_to_wav.py (Convert audio files into particular `wav` format necessary for `pocketsphinx`)
```




### TODO
1. Generate Architecture specific `requirements.txt` for Azure Iot Edge 
2. Make uploading to Azure and uploading to AWS similar with similar APIs
3. Make downloading from Azure and uploading to AWS similar with similar APIs
