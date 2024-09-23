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
  


1. Web Application Deployment:

Create an S3 bucket using boto3:
import boto3
from botocore.exceptions import ClientError

def create_s3_bucket(bucket_name):
    s3 = boto3.client('s3')
    try:
        response = s3.create_bucket(Bucket=bucket_name)
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
            
bucket_name = 'your-bucket-name'   # Replace with your bucket name
create_s3_bucket(bucket_name)

Launch an EC2 instance and configure it as a web server:
def create_ec2_instance():
    ec2 = boto3.resource('ec2')
    try:
        instances = ec2.create_instances(
            ImageId='ami-0abcdef1234567890',  # Replace with your preferred AMI
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.micro',
            KeyName='your-key-pair-name',   # Replace with your key pair name
            SecurityGroupIds=['sg-0123456789abcdef0'],  # Replace with your security group ID
            UserData='''#!/bin/bash
            sudo apt-get update -y
            sudo apt-get install nginx -y
            sudo systemctl start nginx
            sudo systemctl enable nginx
            echo "Hello World from $(hostname -f)" | sudo tee /usr/share/nginx/html/index.html
            '''
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

Deploy the web application onto the EC2 instance:


2. Load Balancing with ELB
Deploy an Application Load Balancer (ALB) using boto3:

elb = boto3.client('elbv2')
response = elb.create_load_balancer(
    Name='my-load-balancer',
    Subnets=['subnet-0123456789abcdef0'],  # Replace with your subnet ID
    SecurityGroups=['sg-0123456789abcdef0'],  # Replace with your security group ID
    Scheme='internet-facing',
    Tags=[
        {
            'Key': 'Name',
            'Value': 'my-load-balancer'   # Replace with your Load Balancer name
        },
     },
    Type='application',
    IpAddressType='ipv4'
)

Register the EC2 instance(s) with the ALB:
target_group = elb.create_target_group(
    Name='my-targets',   # Replace with a target group name you wish to create
    Protocol='HTTP',
    Port=80,
    VpcId='vpc-0123456789abcdef0',  # Replace with your VPC ID
    HealthCheckProtocol='HTTP',
    HealthCheckPort='80',
    HealthCheckPath='/',
    TargetType='instance'
)

elb.register_targets(
    TargetGroupArn=target_group['TargetGroups'][0]['TargetGroupArn'],
    Targets=[
        {
            'Id': instance[0].id,
            'Port': 80
        },
    ]
)


3. Auto Scaling Group (ASG) Configuration
Using boto3, create an ASG:
autoscaling = boto3.client('autoscaling')
launch_configuration = autoscaling.create_launch_configuration(
    LaunchConfigurationName='my-launch-config',
    ImageId='ami-0abcdef1234567890',  # Replace with your preferred AMI
    InstanceType='t2.micro',
    KeyName='your-key-pair-name',
    SecurityGroups=['sg-0123456789abcdef0']  # Replace with your security group ID
)

autoscaling.create_auto_scaling_group(
    AutoScalingGroupName='my-auto-scaling-group',
    LaunchConfigurationName='my-launch-config',
    MinSize=1,
    MaxSize=3,
    DesiredCapacity=1,
    VPCZoneIdentifier='subnet-0123456789abcdef0',  # Replace with your subnet ID
    TargetGroupARNs=[target_group['TargetGroups'][0]['TargetGroupArn']]
)

Configure scaling policies:
cloudwatch = boto3.client('cloudwatch')
scaling_policy = autoscaling.put_scaling_policy(
    AutoScalingGroupName='my-auto-scaling-group',
    PolicyName='scale-out',
    PolicyType='TargetTrackingScaling',
    TargetTrackingConfiguration={
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'ASGAverageCPUUtilization'
        },
        'TargetValue': 50.0
    }
)


4. SNS Notifications
Set up SNS topics:
sns = boto3.client('sns')
topic = sns.create_topic(Name='my-topic')
topic_arn = topic['TopicArn']

sns.subscribe(
    TopicArn=topic_arn,
    Protocol='email',
    Endpoint='admin@example.com'  # Replace with your email
)

Integrate SNS with Lambda: You can create a Lambda function that triggers on specific CloudWatch alarms and publishes messages to the SNS topic.


5. Infrastructure Automation
Create a single script using boto3: Combine all the above steps into a single Python script to automate the deployment, updating, and teardown of the infrastructure.


6. Optional Enhancement – Dynamic Content Handling
Store user-generated content on S3:
# Assuming the content is uploaded to the EC2 instance
s3.upload_file('/path/to/local/file', bucket_name, 'path/in/s3')

Move content to S3 using a background process or Lambda: You can set up a Lambda function to trigger on new uploads to the EC2 instance and move them to S3.

