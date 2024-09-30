import boto3
import json

def lambda_handler(event, context):
    sns = boto3.client('sns')
    print("Event:", json.dumps(event))  # Log the entire event object
    try:
        message = event['Records'][0]['Sns']['Message']
        subject = event['Records'][0]['Sns']['Subject']
        # Define the administrator's email and phone number
        admin_email = 'arpit_agr0123@yahoo.com'  # Replace with admin's email
        admin_phone = '+919993842403'            # Replace with admin's phone
        # Send email notification
        sns.publish(
            TopicArn='arn:aws:sns:us-west-2:975050024946:AdminNotifications',
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
    except KeyError as e:
        print(f"KeyError: {str(e)} - Check the event structure.")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
    return {
        'statusCode': 200,
        'body': json.dumps('Notifications sent successfully!')
    }
