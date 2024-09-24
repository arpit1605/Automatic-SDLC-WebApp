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
  

import boto3
from botocore.exceptions import ClientError

# Replace with your actual values
region='us-west-2'
vpc_id='vpc-0321f38a7b594180d'
subnet_id='subnet-03ca36de9a927fe8e'
subnet_id1='subnet-03ca36de9a927fe8e'
subnet_id2='subnet-06bd72b2e4cb41d10'
security_group_id='sg-0effcd90abb742125'
keypair_name='arpit-key-ec2'
image_id='ami-0e42b3cc568cd07e3'
bucket_name='s3-deploywebapp' 
instance_id='i-0123456789abcdef0'
instance_name='EC2-DeployWebApp'
instance_type='t4g.micro'
lb_name='LB-DeployWebApp'
tg_name='TG-DeployWebApp'
asg_name='ASG-DeployWebApp'

# Create an S3 bucket
def create_s3_bucket():
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
            
create_s3_bucket()

# Launch an EC2 instance and configure it as a web server:
def create_ec2_instance():
    ec2 = boto3.resource('ec2', region_name=region)
    try:
        instances = ec2.create_instances(
            ImageId=image_id,
            MinCount=1,
            MaxCount=1,
            InstanceType=instance_type,
            KeyName=keypair_name,
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
                {'Key': 'Name', 'Value': 'WebApp'},
                    ]
                }
            ]  
        )
        instance = instances[0]
        instance.wait_until_running()
        instance.reload()
        if instance.state['Name'] == 'running':
            print(f"Instance '{instance.id}' created and running successfully.")
        else:
            print(f"Instance '{instance.id}' creation failed.")
    except ClientError as e:
        print(f"Unexpected error: {e}")

create_ec2_instance()

# Deploy the web application onto the EC2 instance:

# Load Balancing with ELB
def create_load_balancer_and_register_targets():
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
    except Exception as e:
        print(f"Error: {e}")

create_load_balancer_and_register_targets()


# Auto Scaling Group (ASG) Configuration
def create_auto_scaling_group():
    autoscaling = boto3.client('autoscaling', region_name=region)
    try:
        # Create Auto Scaling Group using the Launch Template
        autoscaling.create_auto_scaling_group(
            AutoScalingGroupName=asg_name,
            LaunchTemplate={
                'LaunchTemplateName': 'arpit-asg-template',
                'Version': '$Latest'  # Use the latest version of the template
            },
            MinSize=1,
            MaxSize=2,
            DesiredCapacity=1,
            VPCZoneIdentifier=subnet_id,
            TargetGroupARNs=['arn:aws:elasticloadbalancing:us-west-2:975050024946:targetgroup/TG-DeployWebApp/855af40abc3e9879']
        )
        print("Auto Scaling Group created successfully.")
        # Configure scaling policies for CPU utilization
        scaling_policy = autoscaling.put_scaling_policy(
            AutoScalingGroupName=asg_name,
            PolicyName='scale-out',
            PolicyType='TargetTrackingScaling',
            TargetTrackingConfiguration={
                'PredefinedMetricSpecification': {
                    'PredefinedMetricType': 'ASGAverageCPUUtilization'
                },
                'TargetValue': 50.0
            }
        )
        print(f"Scaling policy created successfully: {scaling_policy['PolicyARN']}")
        # Configure scaling policies for network traffic
        scaling_policy = autoscaling.put_scaling_policy(
            AutoScalingGroupName=asg_name,
            PolicyName='scale-out-network-traffic',
            PolicyType='TargetTrackingScaling',
            TargetTrackingConfiguration={
                'PredefinedMetricSpecification': {
                    'PredefinedMetricType': 'ASGAverageNetworkInBytes'
                },
                'TargetValue': 1000000  # Adjust the target value as needed
            }
        )
        print(f"Network traffic scaling policy created successfully: {scaling_policy['PolicyARN']}")
    except Exception as e:
        print(f"Error: {e}")

create_auto_scaling_group()

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

def lambda_handler(event, context):
    sns = boto3.client('sns')
    message = event['Records'][0]['Sns']['Message']
    subject = event['Records'][0]['Sns']['Subject']
    # Define the administrator's email and phone number
    admin_email = 'admin@example.com'
    admin_phone = '+1234567890'
    try:
        # Send email notification
        sns.publish(
            TopicArn='arn:aws:sns:region:account-id:AdminNotifications',
            Message=message,
            Subject=subject
        )
        print(f"Successfully sent email notification to {admin_email}")
        # Send SMS notification
        sns.publish(
            PhoneNumber=admin_phone,
            Message=message
        )
        print(f"Successfully sent SMS notification to {admin_phone}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
    return {
        'statusCode': 200,
        'body': json.dumps('Notifications sent successfully!')
    }

topics = ['HealthIssues', 'ScalingEvents', 'HighTraffic']
topic_arns = {}

# Create topics and store their ARNs
for topic in topics:
    arn = create_sns_topic(topic)
    if arn:
        topic_arns[topic] = arn

# Subscribe Lambda function to topics
lambda_arn = 'arn:aws:lambda:region:account-id:function:YourLambdaFunctionName'
for topic_arn in topic_arns.values():
    subscribe_lambda_to_topic(topic_arn, lambda_arn)
