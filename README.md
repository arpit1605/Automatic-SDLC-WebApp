Overview: 
Develop a system that automatically manages the lifecycle of a web application hosted on  EC2 instances, monitors its health, and reacts to changes in traffic by scaling resources.  Furthermore, administrators receive notifications regarding the infrastructure's health and scaling events. 
Detailed Breakdown: 
1. Web Application Deployment: 
 - Use `boto3` to: 
 - Create an S3 bucket to store your web application's static files. 
 - Launch an EC2 instance and configure it as a web server (e.g., Apache, Nginx).
 - Deploy the web application onto the EC2 instance. 
2. Load Balancing with ELB: 
 - Deploy an Application Load Balancer (ALB) using `boto3`. 
 - Register the EC2 instance(s) with the ALB. 
3. Auto Scaling Group (ASG) Configuration: 
 - Using `boto3`, create an ASG with the deployed EC2 instance as a template. 
 - Configure scaling policies to scale in/out based on metrics like CPU utilization or network traffic. 
4. SNS Notifications: 
 - Set up different SNS topics for different alerts (e.g., health issues, scaling events, high traffic). 
 - Integrate SNS with Lambda so that administrators receive SMS or email notifications. 
5. Infrastructure Automation: 
 - Create a single script using `boto3` that: 
 - Deploys the entire infrastructure. 
 - Updates any component as required. 
 - Tears down everything when the application is no longer needed. 
6. Optional Enhancement – Dynamic Content Handling: 
 - Store user-generated content or uploads on S3. 
 - When a user uploads content to the web application, it gets temporarily stored on the  EC2 instance. A background process (or another Lambda function) can move this to the S3  bucket and update the application's database to point to the content's new location on S3. 

Objectives: 
- Gain a comprehensive understanding of key AWS services and their integration. - Understand the lifecycle of a dynamic web application and its infrastructure.
- Learn how to automate infrastructure deployment and management tasks using boto3. - Experience with real-time monitoring and alerting systems.
  
```
import boto3
from botocore.exceptions import ClientError
import time

# Replace with your actual values
region='us-west-2'
vpc_id='vpc-0321f38a7b594180d'
subnet_id='subnet-03ca36de9a927fe8e'
subnet_id1='subnet-03ca36de9a927fe8e'
subnet_id2='subnet-06bd72b2e4cb41d10'
security_group_id='sg-0effcd90abb742125'
keypair_name='arpit-key-ec2'
image_id='ami-0e42b3cc568cd07e3'
instance_type='t4g.micro'
template_name='arpit-asg-template'
bucket_name='s3-deploywebapp'
instance_name='EC2-DeployWebApp'
lb_name='LB-DeployWebApp'
tg_name='TG-DeployWebApp'
asg_name='ASG-DeployWebApp'
file_path="index.html"
object_key="index.html"
instance_id=''


# Function to create an S3 bucket:
def create_s3_bucket_and_upload_object():
    s3 = boto3.client('s3', region_name=region)
    try:
        response = s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print(f"Bucket '{bucket_name}' created successfully.")
        else:
            print(f"Failed to create bucket '{bucket_name}'.")
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
        print(f'File {file_path} uploaded to {bucket_name}/{object_key}')
    except ClientError as e:
        if error_code == 'FileNotFoundError':
            print(f'The file {file_path} was not found')
        else:
            print(f"Unexpected error: {e}")


# Function to create an EC2 instance and configure it as a web server:
def create_ec2_instance():
    ec2 = boto3.resource('ec2', region_name=region)
    try:
        instances = ec2.create_instances(
            ImageId=image_id,
            InstanceType=instance_type,
            MinCount=1,
            MaxCount=1,
            KeyName=keypair_name,
            #SubnetId=subnet_id,
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
            print(f"Instance '{instance.id}' created and running successfully.")
            return instance.id
        else:
            print(f"Instance '{instance.id}' creation failed.")
    except ClientError as e:
        print(f"Unexpected error: {e}")


# Function to create ELB, create target groups and register them:
def create_load_balancer_and_register_targets(instance_id):
    elbv2 = boto3.client('elbv2', region_name=region)
    try:
        # Create Load Balancer
        response_lb = elbv2.create_load_balancer(
            Name=lb_name,
            Subnets=[subnet_id1, subnet_id2],
            SecurityGroups=[security_group_id],
            Scheme='internet-facing',
            Tags=[
                {
                    'Key': 'Name',
                    'Value': lb_name
                },
            ],
            Type='application',
            IpAddressType='ipv4'
        )
        load_balancer_arn=response_lb['LoadBalancers'][0]['LoadBalancerArn']
        print(f"Load Balancer created successfully: {response_lb['LoadBalancers'][0]['LoadBalancerArn']}")
        
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
        print(f"Target Group created successfully: {response_tg['TargetGroups'][0]['TargetGroupArn']}")

        # Register target group
        target_group_arn=response_tg['TargetGroups'][0]['TargetGroupArn']
        response_reg = elbv2.register_targets(
            TargetGroupArn=response_tg['TargetGroups'][0]['TargetGroupArn'],
            Targets=[
                {
                    'Id': instance_id,
                    'Port': 80
                },
            ]
        )
        print(f"Instance {instance_id} registered successfully in the target group.")

        # Create a listener
        elbv2.create_listener(LoadBalancerArn=load_balancer_arn,Protocol='HTTP',Port=80,
            DefaultActions=[{'Type': 'forward', 'TargetGroupArn': target_group_arn}]
        )

    except Exception as e:
        print(f"Error: {e}")
    outputs = [load_balancer_arn,target_group_arn]
    return outputs


# Auto Scaling Group (ASG) Configuration
def create_auto_scaling_group(target_group_arn):
    autoscaling = boto3.client('autoscaling', region_name=region)
    try:
        # Create Auto Scaling Group using the Launch Template
        autoscaling.create_auto_scaling_group(
            AutoScalingGroupName=asg_name,
            LaunchTemplate={
                'LaunchTemplateName': template_name,
                'Version': '$Latest'  # Use the latest version of the template
            },
            MinSize=1,
            MaxSize=2,
            DesiredCapacity=1,
            VPCZoneIdentifier=subnet_id,
            TargetGroupARNs=[target_group_arn]
        )
        print("Auto Scaling Group {asg_name} created successfully.")
        
        # Configure scaling policies for CPU utilization
        scaling_policy = autoscaling.put_scaling_policy(
            AutoScalingGroupName=asg_name,
            PolicyName='scale-out-cpu-utilization',
            PolicyType='TargetTrackingScaling',
            TargetTrackingConfiguration={
                'PredefinedMetricSpecification': {
                    'PredefinedMetricType': 'ASGAverageCPUUtilization'
                },
                'TargetValue': 50.0
            }
        )
        print(f"CPU utilization scaling policy created successfully: {scaling_policy['PolicyARN']}")
        
        # Configure scaling policies for network traffic
        scaling_policy = autoscaling.put_scaling_policy(
            AutoScalingGroupName=asg_name,
            PolicyName='scale-out-network-traffic',
            PolicyType='TargetTrackingScaling',
            TargetTrackingConfiguration={
                'PredefinedMetricSpecification': {
                    'PredefinedMetricType': 'ASGAverageNetworkIn'
                },
                'TargetValue': 1000000  # Adjust the target value as needed
            }
        )
        print(f"Network traffic scaling policy created successfully: {scaling_policy['PolicyARN']}")
    except Exception as e:
        print(f"Error: {e}")


# SNS Notifications:
def create_sns_topic(topic_name):
    try:
        sns = boto3.client('sns')
        response = sns.create_topic(Name=topic_name)
        print(f"Successfully created topic '{topic_name}' with ARN: {response['TopicArn']}")
        return response['TopicArn']
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return None


# Subscribe lambda to all the topics:
def subscribe_lambda_to_topic(topic_arn, lambda_arn):
    try:
        sns = boto3.client('sns')
        response = sns.subscribe(
            TopicArn=topic_arn,
            Protocol='lambda',
            Endpoint=lambda_arn
        )
        print(f"Successfully subscribed Lambda function to topic {topic_arn} with subscription ARN: {response['SubscriptionArn']}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")


# Function to setup the entire infrastructure:
def create_infra_setup():
    topics = ['HealthIssues', 'ScalingEvents', 'HighTraffic']
    topic_arns = {}
    lambda_arn = 'arn:aws:lambda:us-west-2:975050024946:function:Arpit-Infra-Checkup'  # Replace with your Lambda function name

    # Create an S3 Bucket and upload index.html file:
    create_s3_bucket_and_upload_object()

    # Create an EC2 instance:
    instance_id = create_ec2_instance()

    # Create an ELB Load Balancer:
    load_balancer_output = create_load_balancer_and_register_targets(instance_id)
    load_balancer_arn = load_balancer_output[0]
    target_group_arn = load_balancer_output[1]

    # Create an auto scaling group:
    create_auto_scaling_group(target_group_arn)

    # Create topics and store their ARNs
    for topic in topics:
        arn = create_sns_topic(topic)
        if arn:
            topic_arns[topic] = arn

    # Subscribe Lambda function to topics
    for topic_arn in topic_arns.values():
        subscribe_lambda_to_topic(topic_arn, lambda_arn)


# Function to delete the entire infrastructure:
def delete_infra_setup(instance_ids, load_balancer_arn, target_group, listener_arn, autoscalingName, policy_name, topic_name):
    s3 = boto3.client('s3')
    ec2 = boto3.client('ec2')
    elb = boto3.client('elbv2')
    autoscaling = boto3.client('autoscaling')
    sns = boto3.client('sns')

    # Delete all the files present in the S3 bucket:
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
                    print(f'Deleted {obj["Key"]} from {bucket_name}')
    except Exception as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            print(f"Bucket '{bucket_name}' not found")
        else:
            print(f"An error occurred: {e}")

    # Delete the S3 bucket:
    try:
        s3.delete_bucket(Bucket=bucket_name)
        print(f'Bucket {bucket_name} deleted successfully')

    except Exception as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            print(f"Bucket '{bucket_name}' not found")
        else:
            print(f"An error occurred: {e}")

    # Terminate EC2 instances:
    try:
        ec2.terminate_instances(InstanceIds=instance_ids)
        print(f"Terminated EC2 instances: {', '.join(instance_ids)}")
    except ClientError as e:
        print(f"Failed to terminate instances {instance_ids}: {e}")

    # Delete the Application Load Balancer:
    try:
        elb.delete_load_balancer(LoadBalancerArn=load_balancer_arn)
        print(f"Deleted load balancer with ARN: {load_balancer_arn}")
        time.sleep(1*60)
    except ClientError as e:
        print(f"Failed to delete load balancer {load_balancer_arn}: {e}")

    # Delete the Target Group:
    try:
        elb.delete_target_group(TargetGroupArn=target_group)
        print(f"Deleted target group: {target_group}")
    except ClientError as  e:
        print(f"Failed to delete target group {target_group}: {e}")

    # Delete the Listener:
    try:
        elb.delete_listener(ListenerArn=listener_arn)
        print(f"Deleted listener with ARN: {listener_arn}")
    except ClientError as e:
        print(f"Failed to delete listener {listener_arn}: {e}")

    # Delete the Auto Scaling Group:
    try:
        autoscaling.delete_auto_scaling_group(AutoScalingGroupName=autoscalingName, ForceDelete=True)
        print(f"Deleted auto scaling group: {autoscalingName}")
    except ClientError as e:
        print(f"Failed to delete auto scaling group {autoscalingName}: {e}")

    # Delete the Auto Scaling policies:
    try:
        autoscaling.delete_policy(AutoScalingGroupName=asg_name, PolicyName=policy_name)
        print(f"Deleted scaling policy: {policy_name} for Auto Scaling Group: {asg_name}")
    except ClientError as e:
        print(f"Failed to delete scaling policy {policy_name} for Auto Scaling Group {asg_name}: {e}")

    # Delete SNS topics:
    for topic_arn in topic_arn.values():
        try:
            sns.delete_topic(TopicArn=topic_arn)
            print(f"Deleted SNS Topic: {topic_arn}")
        except ClientError as e:
                print(f"Error deleting SNS Topic {topic_name}:", e)


if __name__ == "__main__":
    action = input("Enter action: create or delete: ")
    if action == "create":
        create_infra_setup()
    elif action == "delete":
        delete_infra_setup(instance_ids=[], load_balancer_arn='', target_group='', listener_arn='', autoscalingName='', policy_name='', topic_name='')
    else:
        print("Invalid action. Please enter create or delete.")
```
