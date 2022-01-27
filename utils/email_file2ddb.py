import boto3
import json 


def put_email(agency, member_name, email_address):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('squad_members')
    response = table.put_item(
    Item={
        'agency': agency,
        'member_name': member_name,
        'email_address': email_address
        }
    )
    return response    

def read_emails(email_fn):

    with open(email_fn, 'r') as f:
        email_map = json.load(f)

    return email_map

def write_addresses(email_fn, agency):

    email_map = read_emails(email_fn)
    for key, value in enumerate(email_map):
        print('{} {}'.format(value, email_map[value]))
        put_email(agency, value, email_map[value])



if __name__ == '__main__':
    write_addresses('../emails.json', 'martinsville')