import os
import io
import boto3
import json
import csv
import email

# grab environment variables
#ENDPOINT_NAME = os.environ['ENDPOINT_NAME']
runtime= boto3.client('runtime.sagemaker')
ENDPOINT_NAME = "sms-spam-classifier-mxnet-2022-04-22-03-10-01-057"
s3 = boto3.client('s3')
ses = boto3.client('ses')

def lambda_handler(event, context):
    print(event)
    print(event["Records"])
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    data = s3.get_object(Bucket=bucket, Key=key)
    contents = data['Body'].read()
    raw_email = contents.decode("utf-8")
    email_obj = email.message_from_string(raw_email)
    # print("email obj: ", email_obj)
    # body = email_obj.get_payload(decode=True)
    # print("email body: ", body)
    email_body = ""
    if email_obj.is_multipart():
        email_body = email_obj.get_payload()[0].get_payload()
    else:
        email_body = email_obj.get_payload()
    print("email body = ")
    print(email_body)
    fromAddress = email_obj["from"]
    print("from address")
    print(fromAddress)

    reply_body_template = "We received your email sent at {} with the subject {}.\n\n\
    Here is a 240 character sample of the email body:\n{}\n \
    The email was categorized as {} with a {} confidence."

    email_subject = email_obj['Subject']
    print(email_subject)
    email_date = email_obj['Date']
    print(email_date)

    reply_body = reply_body_template.format(email_date,email_subject,email_body,"spam","99%")
    print(reply_body)

    response = ses.send_email(
        Source='testing@nyucloudhw3.ga',
        Destination={
            'ToAddresses': [
                'markyamhs@gmail.com'
            ]
        },
        Message={
            'Subject': {
                'Data': 'Hi moma'
            },
            'Body': {
                'Text': {
                    'Data': reply_body
                }
            }
        }
    )
    print(response)

    text = email_body.replace('\n', ' ').replace('\r', '')
    ml_response = runtime.invoke_endpoint(EndpointName=ENDPOINT_NAME,
                                       ContentType='text/csv',
                                       Body=text)
    print(ml_response)
    # result = json.loads(response['Body'].read().decode())
    # print(result)
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
    # data = json.loads(json.dumps(event))
    # payload = data['data']
    # print(payload)
    
    # response = runtime.invoke_endpoint(EndpointName=ENDPOINT_NAME,
    #                                    ContentType='text/csv',
    #                                    Body=payload)
    # print(response)
    # result = json.loads(response['Body'].read().decode())
    # print(result)
    # pred = int(result['predictions'][0]['score'])
    # predicted_label = 'M' if pred == 1 else 'B'
    
    # return predicted_label