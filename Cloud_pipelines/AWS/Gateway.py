import boto3
import traceback

# this script is based on the following tutorial: https://docs.aws.amazon.com/apigateway/latest/developerguide/integrating-api-with-aws-services-s3.html?shortFooter=true#api-root-get-as-s3-get-service

def rollback(error, arn1, arn2, api):
    print(error)
    print("An error has occured! Rolling back...")

    # delete the API and the created roles, if they exist
    gateway_client = boto3.client('apigateway')
    iam_client = boto3.client('iam')
    try:
        iam_client.detach_role_policy(RoleName="edgebench-api", PolicyArn="arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess")
        iam_client.detach_role_policy(RoleName="edgebench-api", PolicyArn="arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs")
        iam_client.detach_role_policy(RoleName="edgebench-api", PolicyArn=arn1)
        iam_client.detach_role_policy(RoleName="edgebench-api", PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess")
        iam_client.detach_role_policy(RoleName="edgebench-api", PolicyArn=arn2)
    except:
        pass
    try:
        iam_client.delete_role(RoleName="edgebench-api")
        iam_client.delete_policy(PolicyArn=arn1)
        iam_client.delete_policy(PolicyArn=arn2)
        gateway_client.delete_rest_api(restApiId=api)
    except:
        pass

    print("API deleted, rollback successful. Program wil now exit.")
    quit()

def createAPI():
    region = boto3.Session().region_name
    temp_arn_1 = ""
    temp_arn_2 = ""
    # initialize gateway and iam clients
    gateway_client = boto3.client('apigateway')
    iam_client = boto3.client('iam')

    try:
        # create an IAM role named edgebench-api with a trust policy:
        role_arn = iam_client.create_role(RoleName='edgebench-api', AssumeRolePolicyDocument='''{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "apigateway.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
} ''')['Role']['Arn']
        iam = boto3.resource('iam')
        role = iam.Role('edgebench-api')

        # attach AmazonS3ReadOnlyAccess
        role.attach_policy(PolicyArn="arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess")

        # attach AmazonAPIGatewayPushToCloudWatchLogs
        role.attach_policy(PolicyArn="arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs")

        # create and attach custom policy #1
        temp_arn_1 = iam_client.create_policy(PolicyName="edgebench-gatewayrole-put", PolicyDocument='''{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:Put*",
            "Resource": "*"
        }
    ]
}
    ''')['Policy']['Arn']
        role.attach_policy(PolicyArn=temp_arn_1)

        # attach policy AmazonS3FullAccess
        role.attach_policy(PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess")

        # create and attach custom policy #2
        temp_arn_2 = iam_client.create_policy(PolicyName='edgebench-gatewayrole-post', PolicyDocument='''{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:Post*",
            "Resource": "*"
        }
    ]
}
    ''')['Policy']['Arn']
        role.attach_policy(PolicyArn=temp_arn_2)

        # create api
        api_id = gateway_client.create_rest_api(name="edgebench-api")['id']

        # create Folder resource
        items = gateway_client.get_resources(restApiId=api_id)['items']
        resource_id = ""
        for item in items:
            if item['path'] == '/':
                resource_id = item['id']
        gateway_client.create_resource(restApiId=api_id, parentId=resource_id, pathPart="{folder}")

        # create Item resource
        items = gateway_client.get_resources(restApiId=api_id)['items']
        resource_id = ""
        for item in items:
            if item['path'] == '/{folder}':
                resource_id = item['id']
        gateway_client.create_resource(restApiId=api_id, parentId=resource_id, pathPart="{item}")

        # create and configure PUT method on {folder}/{item}
        items = gateway_client.get_resources(restApiId=api_id)['items']
        resource_id = ""
        for item in items:
            if item['path'] == '/{folder}/{item}':
                resource_id = item['id']
        gateway_client.put_method(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", authorizationType="AWS_IAM", requestParameters={'method.request.header.Accept': False, 'method.request.header.Content-Type': False, 'method.request.path.folder': True, 'method.request.path.item': True})
        gateway_client.put_integration(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", type='AWS', uri="arn:aws:apigateway:" + region + ":s3:path/{bucket}/{object}", integrationHttpMethod="PUT", credentials=role_arn, requestParameters={'integration.request.header.Accept': 'method.request.header.Accept', 'integration.request.header.Content-Type': 'method.request.header.Content-Type', 'integration.request.header.x-amz-acl': "'authenticated-read'", 'integration.request.path.bucket': 'method.request.path.folder', 'integration.request.path.object': 'method.request.path.item'}, requestTemplates={'audio/wav': '', 'image/jpeg': '', 'image/jpg': '', 'text/plain': ''}, passthroughBehavior='WHEN_NO_MATCH')
        gateway_client.put_method_response(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", statusCode='200', responseModels={'application/json':'Empty'})
        gateway_client.put_method_response(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", statusCode='400', responseModels={'application/json':'Empty'})
        gateway_client.put_method_response(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", statusCode='500', responseModels={'application/json':'Empty'})
        gateway_client.put_integration_response(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", statusCode='200', selectionPattern='')
        gateway_client.put_integration_response(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", statusCode='400', selectionPattern='4\\d{2}')
        gateway_client.put_integration_response(restApiId=api_id, resourceId=resource_id, httpMethod="PUT", statusCode='500', selectionPattern='5\\d{2}')

        # deploy the API
        gateway_client.create_deployment(restApiId=api_id, stageName="Prod")
        invoke_url = "https://" + api_id + ".execute-api." + region + ".amazonaws.com/Prod"
        print(invoke_url)

        input("Press enter to delete everything")
        throw("Firedrill")
    except:
        rollback(traceback.format_exc(), temp_arn_1, temp_arn_2, api_id)



createAPI()
