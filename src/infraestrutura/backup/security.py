"""SDK diagnostics may contain authorization URLs, headers and tokens."""
import logging


class _DiscardSensitiveDiagnostics(logging.Filter):
    def filter(self, record):
        return False


def protect_sdk_logs():
    # A logger-level filter is not inherited; stop propagation at SDK roots too.
    for name in ('boto3', 'botocore', 's3transfer', 'google_auth_oauthlib',
                 'google.auth', 'google_auth_httplib2', 'googleapiclient',
                 'oauthlib', 'requests_oauthlib', 'urllib3', 'httplib2'):
        logger = logging.getLogger(name)
        logger.handlers = [logging.NullHandler()]
        logger.propagate = False
        logger.addFilter(_DiscardSensitiveDiagnostics())
