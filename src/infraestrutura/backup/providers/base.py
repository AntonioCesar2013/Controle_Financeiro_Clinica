import time


def transient(error):
    status = getattr(getattr(error, 'resp', None), 'status', None)
    response = getattr(error, 'response', {})
    if isinstance(response, dict):
        status = response.get('ResponseMetadata', {}).get('HTTPStatusCode', status)
    return status in (408, 429, 500, 502, 503, 504) or isinstance(error, (TimeoutError, ConnectionError)) or type(error).__name__ in {
        'EndpointConnectionError', 'ConnectTimeoutError', 'ReadTimeoutError', 'TransportError', 'ServerNotFoundError'}


def retry(operation, sleep=time.sleep):
    for attempt in range(3):
        try:
            return operation()
        except Exception as error:
            if attempt == 2 or not transient(error):
                raise
            sleep(2 ** attempt)
