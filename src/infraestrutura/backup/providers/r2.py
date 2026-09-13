from datetime import datetime
from ..config import validate
from .base import retry


class R2Provider:
    def __init__(self, credentials):
        self.credentials = credentials

    def _client(self, config):
        import boto3
        from botocore.config import Config
        validate(config)
        access = self.credentials.get_secret('r2_access_key_id')
        secret = self.credentials.get_secret('r2_secret_access_key')
        if not access or not secret or not config['r2_endpoint'] or not config['r2_bucket']:
            raise ValueError('Configure o R2 e suas credenciais.')
        return boto3.client('s3', endpoint_url=config['r2_endpoint'], region_name='auto',
                            aws_access_key_id=access, aws_secret_access_key=secret,
                            config=Config(connect_timeout=10, read_timeout=30, retries={'total_max_attempts': 1}))

    def test_connection(self, config):
        client = self._client(config)
        try:
            retry(lambda: client.head_bucket(Bucket=config['r2_bucket']))
        finally:
            client.close()

    def upload_backup(self, path, config):
        client = self._client(config)
        key = '/'.join(filter(None, [config['r2_prefix'].strip('/'), datetime.now().strftime('%Y/%m'), path.name]))
        try:
            # Single request: errors retain their HTTP code for bounded retry.
            def upload():
                with path.open('rb') as stream:
                    client.put_object(Bucket=config['r2_bucket'], Key=key, Body=stream)
            retry(upload)
        finally:
            client.close()
