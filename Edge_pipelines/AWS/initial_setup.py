import yaml
import boto3
import fileinput
import subprocess

# this function creates and configures various roles that will be needed by EdgeBench to deploy.
# it then updates the greengo.yaml file with these new roles.

def create_role1():
    client = boto3.client('iam')
    str = '''{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": [
              "greengrass.amazonaws.com",
              "edgelambda.amazonaws.com",
              "lambda.amazonaws.com"
            ]
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }
    '''
    arn = client.create_role(RoleName="edgebench-greengrass-role-lambdas", AssumeRolePolicyDocument=str)['Role']['Arn']
    client.attach_role_policy(RoleName='edgebench-greengrass-role-lambdas', PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess')
    client.attach_role_policy(RoleName='edgebench-greengrass-role-lambdas', PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole')
    client.attach_role_policy(RoleName='edgebench-greengrass-role-lambdas', PolicyArn='arn:aws:iam::aws:policy/service-role/AWSGreengrassResourceAccessRolePolicy')
    client.attach_role_policy(RoleName='edgebench-greengrass-role-lambdas', PolicyArn='arn:aws:iam::aws:policy/AWSGreengrassFullAccess')
    client.attach_role_policy(RoleName='edgebench-greengrass-role-lambdas', PolicyArn='arn:aws:iam::aws:policy/CloudWatchEventsFullAccess')
    return arn


def create_role2():
    client = boto3.client('iam')
    str = '''{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "iot.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
    '''
    arn = client.create_role(RoleName="edgebench-greengrass-role-rules", AssumeRolePolicyDocument=str)['Role']['Arn']
    client.attach_role_policy(RoleName='edgebench-greengrass-role-rules', PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess')
    arn_policy1 = client.create_policy(PolicyName='edgebench-greengrass-role-rules-1', PolicyDocument='''{
    "Version": "2012-10-17",
    "Statement": {
        "Effect": "Allow",
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::edgelineartest/*"
    }
}''')['Policy']['Arn']
    arn_policy2 = client.create_policy(PolicyName='edgebench-greengrass-role-rules-2', PolicyDocument='''{
    "Version": "2012-10-17",
    "Statement": {
        "Effect": "Allow",
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::facedetecttest/*"
    }
}''')['Policy']['Arn']
    arn_policy3 = client.create_policy(PolicyName='edgebench-greengrass-role-rules-3', PolicyDocument='''{
    "Version": "2012-10-17",
    "Statement": {
        "Effect": "Allow",
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::audioperf-variance-test/*"
    }
}''')['Policy']['Arn']

    client.attach_role_policy(RoleName='edgebench-greengrass-role-rules', PolicyArn=arn_policy1)
    client.attach_role_policy(RoleName='edgebench-greengrass-role-rules', PolicyArn=arn_policy2)
    client.attach_role_policy(RoleName='edgebench-greengrass-role-rules', PolicyArn=arn_policy3)

    return arn

def find_and_replace(filename, text_to_search1, replacement_text1, text_to_search2, replacement_text2):
    # below code taken from https://stackoverflow.com/questions/17140886/how-to-search-and-replace-text-in-a-file-using-python
    with open(filename, 'r') as file :
        filedata = file.read()

    # Replace the target string
    filedata = filedata.replace(text_to_search1, replacement_text1)
    filedata = filedata.replace(text_to_search2, replacement_text2)

    # Write the file out again
    with open(filename.split("/")[2], 'w+') as file:
        file.write(filedata)
        file.close()


arn1 = create_role1()
print("Lambda role created successfully")
arn2 = create_role2()
print("Topic rule role created successfully")
find_and_replace('./initial_setup/scalar.yaml', '<ROLE1>', arn1, '<ROLE2>', arn2)
find_and_replace('./initial_setup/image.yaml', '<ROLE1>', arn1, '<ROLE2>', arn2)
find_and_replace('./initial_setup/audio.yaml', '<ROLE1>', arn1, '<ROLE2>', arn2)
find_and_replace('./initial_setup/facedetect.yaml', '<ROLE1>', arn1, '<ROLE2>', arn2)
find_and_replace('./initial_setup/thumbnail.yaml', '<ROLE1>', arn1, '<ROLE2>', arn2)
print("YAMLs created successfully.")
bash = subprocess.Popen(["./reset.sh"])
bash.wait()
file = open('./.edgebench/role.txt', 'w+')
file.write(arn1)
file.close()
print("./.gg folder reset, role saved in ./edgebench/role.txt. Initial setup completed successfully.")
