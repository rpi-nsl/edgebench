
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


### How to deploy the stuff in this repository?

1. Cloud_pipelines:
    
    - Azure --> [Recommended Reading 1](https://github.com/yokawasa/azure-functions-python-samples/tree/master/v2functions), [Recommended Reading 2](https://unofficialism.info/posts/quick-start-with-azure-function-v2-python-preview/)
        * audio-pipeline
        * facedetect-pipeline
        * image-pipeline
        * pca-pipeline
        * scalar-pipeline
        * thumbnail-pipeline

        Each of this application deployments are for Azure Functions V2 with Pythin runtime stack which is still in preview mode. In any case, each of these folders will contains some stuff needed to create the pythn package with ependencies and deploy the code on the Azure functions runtime.
        You may wonder why don't I use `serverless` to deploy Azure functions. As it turns out, `serverless` supports deploying only NodeJS function with Azure. So we have to use Microsoft's own cli, which is cool in its own way. 
        You need [Azure functions core tool](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local) in your machine in orer to deploy functions on Azure Funtions runtime.

        To deploy audio-pipeline:, put all the required  python dependencies in the `audio-pipeline/requirements.txt` file. **Be sure to deploy ONLY from _inside_ the root folder for the application. _Do not go_ inside the folder inside the root folder with the same name and deploy from there. For e.g. deploy from inside `audio-pipeline/` folder and do not do inside `/audio-pipeline/audio-pipeline` and deploy.**
        ```
        >> ls
        >> audio-pipeline  facedetect-pipeline  image-pipeline  pca-pipeline  scalar-pipeline  thumbnail-pipeline
        >> cd audio-pipeline
        >> audio-pipeline  bin  deploy.sh  extensions.csproj  host.json  local.settings.json  obj  requirements.txt
        >> func azure functionapp publish <your_function_app_name> --build-native-deps
        ```
        This will create the package with the native dependencies from the `requirements.txt` file. In case you need to add some C libraries or some shared libraries in order to build the python packages, you can also include them in the building process as follows:
        ```
        >> func azure functionapp publish <your_function_app_name> --build-native-deps --additional-packages "python-dev cmake gcc build-essentials"
        ```
        This will first install `python-dev, cmake, gcc, build-essentials` and then `pip install` the requirements libraries. 

        For deploying and testing the functions locally, 
        ```
        >> func start host
        ```

        This will start the functions lcoally. You can literaly bind the blob storage and then invoke functions running locally by uploading blobs files in the required container! Cool! Basically you can test if your whole pipeline works. Caveat is that packaging it and then deploying it is a pain in the butt. Everything works fine locally , but sometimes even after you successfully compile and package everything, during runtime in the serverless function, the runtime fails to find shared libraries. Look at this [gist](https://gist.github.com/akaanirban/eb239ba023894541e418bf20a486fd14) if your deployment fails to find any package or a`*.so` file.

        To deploy you can run the `deploy.sh` script inside each application.

        Ofcourse it is possible to have multiple functions inside each root folder, so that when you deploy you have multiple functions running inside one function app.But for simplicity, it is better if you have a single function inside the function app at a time while measuring performance as it will create the bnecessary isolation.


    #### Then comes the `local.settings.json` file:
    ```json
            {
            "IsEncrypted": false,
            "Values": {
                "FUNCTIONS_WORKER_RUNTIME": "python",
                "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=functiontest111;AccountKey=KFgkw2+I1eSP981mCIR0nX+sZz5Dk/i/2wUqJEM9T4X2pAC4DHvq60saxYQSpQO5TTZThwzJZ4m4oQi6/zJvEw==;EndpointSuffix=core.windows.net",
                "MyStorageConnectionAppSetting": "DefaultEndpointsProtocol=https;AccountName=functiontest111;AccountKey=KFgkw2+I1eSP981mCIR0nX+sZz5Dk/i/2wUqJEM9T4X2pAC4DHvq60saxYQSpQO5TTZThwzJZ4m4oQi6/zJvEw==;EndpointSuffix=core.windows.net"
                }
        }
    ```
    Update necessary `Values` in this json file. These **NEEDS** to be updated to the function app while deploying so that the serverless function can access these functions during runtime. Also make sure that the variable names you are mentioning here, mathces those if mentioned in `function.json` inside the inner folder.
 
2. Edge Pipelines:

    - Azure Pipelines: 
    
        Deploy Azure pipelines through `VScode`. Refer to this page as to how this can be done [Deploy Azure IoT Edge Modules from VSCode](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-deploy-modules-vscode) and install the software from [here](https://marketplace.visualstudio.com/items?itemName=vsciot-vscode.azure-iot-edge). One caveat is for arm32v7 processors, you cannot build it on the x86 machine unless you have the qemu hack. Check the ][Hypriot](https://blog.hypriot.com/post/setup-simple-ci-pipeline-for-arm-images/) page as how to enable `qemu` for building arm images on x86. 
        
        - Azure amd64 images can be easily build and deployed to the device from the VSCode. 
        - Also, there is another way you can deploy stuff wherever you want [Look Here for Details](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-deploy-modules-cli):
            * Compile and push the Docker images separately. They are all at this moment in `anirbandas/edgebench:*` `dockerhub` repository with all arm32v7 and amd64 tags.
            * Create a deployment manifest. Copy the one from what VSCode generates from previous method.
            * Use Azure cli to directly deploy to device using the deployment manifest
                ```
                az iot edge set-modules --device-id [device id] --hub-name [hub name] --content [file path]
                ```
            **DONE** !

### TODO
1. Generate Architecture specific `requirements.txt` for Azure Iot Edge 
2. Make uploading to Azure and uploading to AWS similar with similar APIs
3. Make downloading from Azure and uploading to AWS similar with similar APIs
