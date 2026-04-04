import boto3
import os
from botocore.exceptions import NoCredentialsError
from botocore.config import Config


AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME') 
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')  
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'eu-north-1')

class S3Config:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            config=Config(
                signature_version='s3v4',
                max_pool_connections=50,
                s3={'addressing_style': 'virtual'}
            ),
            aws_access_key_id=AWS_ACCESS_KEY_ID,  
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )

    def get_client(self):
        return self.s3_client

