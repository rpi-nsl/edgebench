from Fileuploader import *
uploader_azure = Fileuploader(application='audio', platform='azure', stats_folder='./', azure_storage_account_name="edgebench8561", azure_storage_account_key="0i7buxxEJ8gMW3XcMu11JBNcZllkJGdm3UkHuy24Sxj+x1iQv7bf62SKJwSBiYIZ/xhjp9zXkf3yfWtgfud1oA==", bucket_name="edgelineartest")
uploader_azure.batch_upload_files(folder_path="/home/anirban/Music/CK_different_sized/")



downloader_azure = S3detailsFetcher(application='audio', platform='azure', stats_folder='./', azure_storage_account_name="edgebench8561", azure_storage_account_key="0i7buxxEJ8gMW3XcMu11JBNcZllkJGdm3UkHuy24Sxj+x1iQv7bf62SKJwSBiYIZ/xhjp9zXkf3yfWtgfud1oA==")
all_objects_azure = downloader_azure.get_all_blob_contents_from_uploads(bucket_name='edgelineartest')


downloader_aws = S3detailsFetcher(application='audio', platform='aws', stats_folder='./')
all_objects_aws = downloader_aws.get_all_blob_contents_from_uploads('edgelineartest')
s = downloader_aws.get_all_blob_contents_from_results('results-lambda-facedetect-coldstart-2304')











