import boto3
from botocore.exceptions import ClientError
import json
import time
import os

# Replace with your actual values
region = 'us-west-2'
vpc_id = 'vpc-0321f38a7b594180d'
subnet_id1 = 'subnet-03ca36de9a927fe8e'
subnet_id2 = 'subnet-06bd72b2e4cb41d10'
security_group_id = 'sg-0effcd90abb742125'
keypair_name = 'arpit-key-ec2'
image_id = 'ami-0e42b3cc568cd07e3'
instance_type = 't4g.micro'
template_name = 'arpit-asg-template'
bucket_name = 's3-deploywebapp'
instance_name = 'EC2-DeployWebApp'
lb_name = 'LB-DeployWebApp'
tg_name = 'TG-DeployWebApp'
asg_name = 'ASG-DeployWebApp'
file_path = "index.html"
object_key = "index.html"
topics = ['HealthIssues', 'ScalingEvents', 'HighTraffic']
topic_arns = {}
lambda_arn = 'arn:aws:lambda:us-west-2:975050024946:function:Arpit-Infra-Checkup'  # Replace with your Lambda function name
resource_file = 'resources.json'

# Function to create an S3 bucket and upload object
def create_s3_bucket_and_upload_object():
    s3 = boto3.client('s3', region_name=region)
    try:
        s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
        print(f"Bucket '{bucket_name}' created successfully.")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyOwnedByYou':
            print(f"Bucket '{bucket_name}' already exists and is owned by you.")
        elif error_code == 'BucketAlreadyExists':
            print(f"Bucket '{bucket_name}' already exists and is owned by someone else.")
        else:
            print(f"Unexpected error: {e}")

    # Uploading static files to S3 bucket
    try:
        s3.upload_file(file_path, bucket_name, object_key)
        print(f'File {file_path} has been uploaded to {bucket_name}/{object_key} successfully.')
    except ClientError as e:
        print(f"Unexpected error during file upload: {e}")

# Function to create an EC2 instance
def create_ec2_instance():
    ec2 = boto3.resource('ec2', region_name=region)
    try:
        instances = ec2.create_instances(
            ImageId=image_id,
            InstanceType=instance_type,
            MinCount=1,
            MaxCount=1,
            KeyName=keypair_name,
            SubnetId=subnet_id1,
            SecurityGroupIds=[security_group_id],
            UserData='''#!/bin/bash
            sudo apt-get update -y
            sudo apt-get install nginx -y
            sudo systemctl start nginx
            sudo systemctl enable nginx
            echo "Hello World from $(hostname -f)" | sudo tee /usr/share/nginx/html/index.html
            ''',
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': instance_name},
                    ]
                }
            ]
        )
        instance = instances[0]
        instance.wait_until_running()
        instance.reload()
        if instance.state['Name'] == 'running':
            print(f"Instance ID '{instance.id}' created and running successfully.")
            return instance.id
    except ClientError as e:
        print(f"Error creating EC2 instance: {e}")
        return None

# Function to create Load Balancer and register targets
def create_load_balancer_and_register_targets(instance_id):
    elbv2 = boto3.client('elbv2', region_name=region)
    try:
        # Create Load Balancer
        response_lb = elbv2.create_load_balancer(
            Name=lb_name,
            Subnets=[subnet_id1, subnet_id2],
            SecurityGroups=[security_group_id],
            Scheme='internet-facing',
            Tags=[{'Key': 'Name', 'Value': lb_name}],
            Type='application',
            IpAddressType='ipv4'
        )
        load_balancer_arn = response_lb['LoadBalancers'][0]['LoadBalancerArn']
        print(f"Load Balancer ARN: {load_balancer_arn} created successfully.")

        # Create Target Group
        response_tg = elbv2.create_target_group(
            Name=tg_name,
            Protocol='HTTP',
            Port=80,
            VpcId=vpc_id,
            HealthCheckProtocol='HTTP',
            HealthCheckPort='80',
            HealthCheckPath='/',
            TargetType='instance'
        )
        target_group_arn = response_tg['TargetGroups'][0]['TargetGroupArn']
        print(f"Target Group ARN: {target_group_arn} created successfully.")

        # Register target group
        elbv2.register_targets(
            TargetGroupArn=target_group_arn,
            Targets=[{'Id': instance_id, 'Port': 80}]
        )
        print(f"Instance ID {instance_id} registered in the target group successfully.")

        # Create the listener
        create_response = elbv2.create_listener(
            LoadBalancerArn=load_balancer_arn,
            Protocol='HTTP',
            Port=80,
            DefaultActions=[{'Type': 'forward', 'TargetGroupArn': target_group_arn}]
        )
        listener_arn = create_response['Listeners'][0]['ListenerArn']
        print(f"Created Listener ARN: {listener_arn} successfully.")

        return load_balancer_arn, target_group_arn, listener_arn

    except Exception as e:
        print(f"Error: {e}")

# Auto Scaling Group (ASG) Configuration
def create_auto_scaling_group(target_group_arn):
    autoscaling = boto3.client('autoscaling', region_name=region)
    try:
        # Create Auto Scaling Group
        autoscaling.create_auto_scaling_group(
            AutoScalingGroupName=asg_name,
            LaunchTemplate={
                'LaunchTemplateName': template_name,
                'Version': '$Latest'  # Use the latest version of the template
            },
            MinSize=1,
            MaxSize=2,
            DesiredCapacity=1,
            VPCZoneIdentifier=subnet_id1,
            TargetGroupARNs=[target_group_arn]
        )
        print(f"Auto Scaling Group '{asg_name}' created successfully.")

    except Exception as e:
        print(f"Error: {e}")

# SNS Notifications
def create_sns_topic(topic_name):
    sns = boto3.client('sns')
    try:
        response = sns.create_topic(Name=topic_name)
        print(f"Topic '{topic_name}' with ARN: {response['TopicArn']} created successfully.")
        return response['TopicArn']
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return None

# Subscribe lambda to topics
def subscribe_lambda_to_topic(topic_arn, lambda_arn):
    sns = boto3.client('sns')
    try:
        response = sns.subscribe(
            TopicArn=topic_arn,
            Protocol='lambda',
            Endpoint=lambda_arn
        )
        print(f"Lambda function to topic {topic_arn} with subscription ARN: {response['SubscriptionArn']} subscribed successfully.")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

# Function to setup the entire infrastructure
def create_infra_setup():
    create_s3_bucket_and_upload_object()
    instance_id = create_ec2_instance()
    
    # Load Balancer, Target Group, and Listener
    load_balancer_arn, target_group_arn, listener_arn = create_load_balancer_and_register_targets(instance_id)
    
    create_auto_scaling_group(target_group_arn)

    resource_details = {
        'instance_id': instance_id,
        'load_balancer_arn': load_balancer_arn,
        'target_group_arn': target_group_arn,
        'listener_arn': listener_arn,
        'asg_name': asg_name,
        'topics': {}
    }

    for topic in topics:
        arn = create_sns_topic(topic)
        if arn:
            resource_details['topics'][topic] = arn
            subscribe_lambda_to_topic(arn, lambda_arn)

    # Write resource details to a file
    with open(resource_file, 'w') as f:
        json.dump(resource_details, f, indent=4)
    print(f"Resource details saved to {resource_file}")

# Function to delete the entire infrastructure
def delete_infra_setup():
    if not os.path.exists(resource_file):
        print("Resource file not found. Cannot delete resources.")
        return

    with open(resource_file, 'r') as f:
        resource_details = json.load(f)

    instance_id = resource_details['instance_id']
    load_balancer_arn = resource_details['load_balancer_arn']
    target_group_arn = resource_details['target_group_arn']
    listener_arn = resource_details['listener_arn']
    asg_name = resource_details['asg_name']
    topics = resource_details['topics']

    # Delete Auto Scaling Group
    autoscaling = boto3.client('autoscaling', region_name=region)
    try:
        autoscaling.delete_auto_scaling_group(
            AutoScalingGroupName=asg_name,
            ForceDelete=True
        )
        print(f"Deleted Auto Scaling Group '{asg_name}'.")
    except Exception as e:
        print(f"Error deleting ASG: {e}")

    # Delete Listeners, Target Groups and Load Balancer:
    elb = boto3.client('elbv2', region_name=region)
    
    # Delete the Listener:
    try:
        elb.delete_listener(ListenerArn=listener_arn)
        print(f"Deleted listener with ARN: {listener_arn}")
    except ClientError as e:
        print(f"Failed to delete listener {listener_arn}: {e}")

    # Delete the Target Group:
    try:
        elb.delete_target_group(TargetGroupArn=target_group_arn)
        print(f"Deleted target group: {target_group_arn}")
    except ClientError as  e:
        print(f"Failed to delete target group {target_group_arn}: {e}")

    # Delete the Application Load Balancer:
    try:
        elb.delete_load_balancer(LoadBalancerArn=load_balancer_arn)
        print(f"Deleted load balancer with ARN: {load_balancer_arn}")
        time.sleep(1*60)
    except ClientError as e:
        print(f"Failed to delete load balancer {load_balancer_arn}: {e}")

    # Terminate EC2 instances
    ec2 = boto3.resource('ec2', region_name=region)
    try:
        ec2.instances.filter(InstanceIds=[instance_id]).terminate()
        print(f"Terminated EC2 instance(s): {instance_id}")
    except Exception as e:
        print(f"Error terminating EC2 instances: {e}")

    # Delete SNS Topics
    sns = boto3.client('sns', region_name=region)
    for topic, topic_arn in topics.items():
        try:
            sns.delete_topic(TopicArn=topic_arn)
            print(f"Deleted SNS Topic '{topic_arn}'.")
        except Exception as e:
            print(f"Error deleting SNS Topic '{topic_arn}': {e}")

    # Remove resource file after deletion
    os.remove(resource_file)
    print(f"Resource details file '{resource_file}' deleted.")

if __name__ == "__main__":
    action = input("Enter action: create or delete: ").strip().lower()
    if action == "create":
        create_infra_setup()
    elif action == "delete":
        delete_infra_setup()
    else:
        print("Invalid action. Please enter 'create' or 'delete'.")
