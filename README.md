# Monitoring, Scaling, and Automation using Boto3

## Develop a system that automatically manages the lifecycle of a web application hosted on  EC2 instances, monitors its health, and reacts to changes in traffic by scaling resources.  Furthermore, administrators receive notifications regarding the infrastructure's health and scaling events.

### Detailed Breakdown:
##### 1. Web Application Deployment: 
 - Use `boto3` to: 
 - Create an S3 bucket to store your web application's static files. 
 - Launch an EC2 instance and configure it as a web server (e.g., Apache, Nginx).
 - Deploy the web application onto the EC2 instance. 
##### 2. Load Balancing with ELB: 
 - Deploy an Application Load Balancer (ALB) using `boto3`. 
 - Register the EC2 instance(s) with the ALB. 
##### 3. Auto Scaling Group (ASG) Configuration: 
 - Using `boto3`, create an ASG with the deployed EC2 instance as a template. 
 - Configure scaling policies to scale in/out based on metrics like CPU utilization or network traffic. 
##### 4. SNS Notifications: 
 - Set up different SNS topics for different alerts (e.g., health issues, scaling events, high traffic). 
 - Integrate SNS with Lambda so that administrators receive SMS or email notifications. 
##### 5. Infrastructure Automation: 
 - Create a single script using `boto3` that: 
 - Deploys the entire infrastructure. 
 - Updates any component as required. 
 - Tears down everything when the application is no longer needed.
   
### The Python Boto3 script takes input from the user in the form of action. The user needs to specify 'create' to create the entire infrastructure or delete to delete the entire infrastructure.

## Execution Steps:

### Step 1: Execute the script with action as 'create':

![image](https://github.com/user-attachments/assets/e240bfc2-4df4-4509-8d91-9e9113a927cb)


### Validate whether all the resouces has been created:

![image](https://github.com/user-attachments/assets/2e0d588d-2971-45c6-88db-896d42bd64b2)

![image](https://github.com/user-attachments/assets/3b34dd2d-f822-4361-a27a-93de4e5112da)

![image](https://github.com/user-attachments/assets/bd19a1ea-1b91-4f23-8ff9-963ff253b52f)

![image](https://github.com/user-attachments/assets/e17fc0c6-1e26-4d33-a7df-fb6545b2a3a7)

![image](https://github.com/user-attachments/assets/f9d0dc26-cf0d-43d1-8762-4e97d1f6eb87)

![image](https://github.com/user-attachments/assets/966696f2-19a3-4430-8efa-0dc430f6b450)

![image](https://github.com/user-attachments/assets/236b2524-73c7-4cd3-94fe-4b7a25fd433d)

![image](https://github.com/user-attachments/assets/367cc0af-9e97-408f-bfdc-5021bbeb80b1)

![image](https://github.com/user-attachments/assets/309dbf66-6062-402b-9f0c-0749110f0cd6)

![image](https://github.com/user-attachments/assets/daef1654-c733-4f6b-99b2-dce72446df2b)


### resource.json file created with below content:

![image](https://github.com/user-attachments/assets/e27f3f63-059c-45c5-b70a-b0254701f508)


## Step 2: Execute the script with the action 'delete':

![image](https://github.com/user-attachments/assets/1a9616c0-fce3-47cc-a121-1205b4edc4ca)


## Open the S3 bucket in AWS portal that stores your web application's static files:
Go to permissions and modify the S3 Bucket Policy as below:
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::s3-deploywebapp/*"
        }
    ]
}
```
Under Block public access (bucket settings) edit the configuration and Block all public access.
Enable Static website hosting: Select Hosting type as Host a static website, Index document as index.html

![image](https://github.com/user-attachments/assets/a390915b-bea0-431f-a4a6-c85905abb494)
