import os
import io
import boto3
import json
import csv
import email

# grab environment variables
#ENDPOINT_NAME = os.environ['ENDPOINT_NAME']
runtime= boto3.client('runtime.sagemaker')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    print(event)
    print(event["Records"])
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    data = s3.get_object(Bucket=bucket, Key=key)
    contents = data['Body'].read()
    raw_email = contents.decode("utf-8")
    email_obj = email.message_from_string(raw_email)
    print(email_obj)

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