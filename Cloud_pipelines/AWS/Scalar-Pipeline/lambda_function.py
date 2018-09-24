import json
import tempfile
import boto3
import os
import tempfile


s3_client = boto3.client('s3')
results_bucket = os.getenv('RESULTS_BUCKET')


def lambda_handler(event, context):
    record = event['Records'][0]
    bucket = record['s3']['bucket']['name']
    key = record['s3']['object']['key']

    tmp = tempfile.NamedTemporaryFile()
    s3_client.download_file(bucket, key, tmp.name)
    tmp.flush()

    f = open(tmp.name, 'r')
    lines = f.readlines()
    response = s3_client.put_object(
        Bucket=results_bucket,
        Body=json.dumps(lines),
        Key=key,
        ServerSideEncryption='AES256'
        )
    return {
        "statusCode": 200,
        "body": json.dumps('Hello from Lambda! {}'.format(response))
    }

