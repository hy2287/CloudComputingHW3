import boto3
import json
import email

runtime= boto3.client('runtime.sagemaker')
ENDPOINT_NAME = "sms-spam-classifier-mxnet-2022-04-22-03-10-01-057"
REPLY_TO = 'markyamhs@gmail.com'
s3 = boto3.client('s3')
ses = boto3.client('ses')

def lambda_handler(event, context):
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    data = s3.get_object(Bucket=bucket, Key=key)
    contents = data['Body'].read()
    raw_email = contents.decode("utf-8")
    email_obj = email.message_from_string(raw_email)
    email_body = ""
    if email_obj.is_multipart():
        email_body = email_obj.get_payload()[0].get_payload()
    else:
        email_body = email_obj.get_payload()
    
    # fromAddress = email_obj["from"]

    reply_body_template = "We received your email sent at {} with the subject {}.\n\n\
    Here is a 240 character sample of the email body:\n{}\n \
    The email was categorized as {} with a {} confidence."

    email_subject = email_obj['Subject']
    email_date = email_obj['Date']

    reply_body = reply_body_template.format(email_date,email_subject,email_body,"spam","99%")

    response = ses.send_email(
        Source='testing@nyucloudhw3.ga',
        Destination={
            'ToAddresses': [
                REPLY_TO
            ]
        },
        Message={
            'Subject': {
                'Data': 'NYU Cloud HW3 Demo'
            },
            'Body': {
                'Text': {
                    'Data': reply_body
                }
            }
        }
    )

    text = email_body.replace('\n', ' ').replace('\r', '')
    ml_response = runtime.invoke_endpoint(EndpointName=ENDPOINT_NAME,
                                       ContentType='text/csv',
                                       Body=text)

    print(ml_response)
    temp = ml_response["Body"].read()
    print(temp)
    print(json.loads(temp))
    ml_result = json.loads(ml_response["Body"].read().decode())
    print(ml_result)
    # pred = int(result['predictions'][0]['score'])
    # predicted_label = 'M' if pred == 1 else 'B'

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
    