import boto3
import json
import email
import string
import sys
import numpy as np

from hashlib import md5

if sys.version_info < (3,):
    maketrans = string.maketrans
else:
    maketrans = str.maketrans

def vectorize_sequences(sequences, vocabulary_length):
    results = np.zeros((len(sequences), vocabulary_length))
    for i, sequence in enumerate(sequences):
       results[i, sequence] = 1. 
    return results

def one_hot_encode(messages, vocabulary_length):
    data = []
    for msg in messages:
        temp = one_hot(msg, vocabulary_length)
        data.append(temp)
    return data

def text_to_word_sequence(text,
                          filters='!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n',
                          lower=True, split=" "):
    """Converts a text to a sequence of words (or tokens).
    # Arguments
        text: Input text (string).
        filters: list (or concatenation) of characters to filter out, such as
            punctuation. Default: `!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n`,
            includes basic punctuation, tabs, and newlines.
        lower: boolean. Whether to convert the input to lowercase.
        split: str. Separator for word splitting.
    # Returns
        A list of words (or tokens).
    """
    if lower:
        text = text.lower()

    if sys.version_info < (3,):
        if isinstance(text, unicode):
            translate_map = dict((ord(c), unicode(split)) for c in filters)
            text = text.translate(translate_map)
        elif len(split) == 1:
            translate_map = maketrans(filters, split * len(filters))
            text = text.translate(translate_map)
        else:
            for c in filters:
                text = text.replace(c, split)
    else:
        translate_dict = dict((c, split) for c in filters)
        translate_map = maketrans(translate_dict)
        text = text.translate(translate_map)

    seq = text.split(split)
    return [i for i in seq if i]

def one_hot(text, n,
            filters='!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n',
            lower=True,
            split=' '):
    """One-hot encodes a text into a list of word indexes of size n.
    This is a wrapper to the `hashing_trick` function using `hash` as the
    hashing function; unicity of word to index mapping non-guaranteed.
    # Arguments
        text: Input text (string).
        n: int. Size of vocabulary.
        filters: list (or concatenation) of characters to filter out, such as
            punctuation. Default: `!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n`,
            includes basic punctuation, tabs, and newlines.
        lower: boolean. Whether to set the text to lowercase.
        split: str. Separator for word splitting.
    # Returns
        List of integers in [1, n]. Each integer encodes a word
        (unicity non-guaranteed).
    """
    return hashing_trick(text, n,
                         hash_function='md5',
                         filters=filters,
                         lower=lower,
                         split=split)


def hashing_trick(text, n,
                  hash_function=None,
                  filters='!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n',
                  lower=True,
                  split=' '):
    """Converts a text to a sequence of indexes in a fixed-size hashing space.
    # Arguments
        text: Input text (string).
        n: Dimension of the hashing space.
        hash_function: defaults to python `hash` function, can be 'md5' or
            any function that takes in input a string and returns a int.
            Note that 'hash' is not a stable hashing function, so
            it is not consistent across different runs, while 'md5'
            is a stable hashing function.
        filters: list (or concatenation) of characters to filter out, such as
            punctuation. Default: `!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n`,
            includes basic punctuation, tabs, and newlines.
        lower: boolean. Whether to set the text to lowercase.
        split: str. Separator for word splitting.
    # Returns
        A list of integer word indices (unicity non-guaranteed).
    `0` is a reserved index that won't be assigned to any word.
    Two or more words may be assigned to the same index, due to possible
    collisions by the hashing function.
    The [probability](
        https://en.wikipedia.org/wiki/Birthday_problem#Probability_table)
    of a collision is in relation to the dimension of the hashing space and
    the number of distinct objects.
    """
    if hash_function is None:
        hash_function = hash
    elif hash_function == 'md5':
        hash_function = lambda w: int(md5(w.encode()).hexdigest(), 16)

    seq = text_to_word_sequence(text,
                                filters=filters,
                                lower=lower,
                                split=split)
    return [int(hash_function(w) % (n - 1) + 1) for w in seq]

ENDPOINT_NAME = "sms-spam-classifier-mxnet-2022-04-23-01-10-46-830"
REPLY_TO = 'markyamhs@gmail.com'
s3 = boto3.client('s3')
ses = boto3.client('ses')
sagemaker = boto3.client('sagemaker-runtime')

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
    The email was categorized as {} with a {} percent confidence."

    email_subject = email_obj['Subject']
    email_date = email_obj['Date']

    text = email_body.replace('\n', ' ').replace('\r', '')
    test_messages = [text]
    vocabulary_length = 9013
    one_hot_test_messages = one_hot_encode(test_messages, vocabulary_length)
    encoded_test_messages = vectorize_sequences(one_hot_test_messages, vocabulary_length)
    test_body= json.dumps(encoded_test_messages.tolist())
    ml_response = sagemaker.invoke_endpoint(EndpointName=ENDPOINT_NAME,ContentType='application/json',Body=test_body)
    ml_result = json.loads(ml_response['Body'].read().decode())
    ml_label = ml_result["predicted_label"][0][0]
    classification = ""
    prob =  int(100*ml_result["predicted_probability"][0][0])
    if ml_label<0.1:
        classification = "ham"
    else:
        classification = "spam"

    reply_body = reply_body_template.format(email_date,email_subject,email_body,classification,prob)

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

    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
    