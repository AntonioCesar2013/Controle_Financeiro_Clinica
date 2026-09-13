import json
import threading
from .base import retry


class DriveProvider:
    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(self, credentials, config_store):
        self.credentials = credentials
        self.config_store = config_store
        self.lock = threading.RLock()

    def connect(self, config):
        from google_auth_oauthlib.flow import InstalledAppFlow
        secret = self.credentials.get_secret('drive_client_secret')
        if not config['drive_client_id'] or not secret:
            raise ValueError('Informe o Client ID e Client Secret OAuth do tipo Desktop.')
        flow = InstalledAppFlow.from_client_config({'installed': {
            'client_id': config['drive_client_id'], 'client_secret': secret,
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': ['http://localhost']}}, self.SCOPES, autogenerate_code_verifier=True)
        with self.lock:
            token = flow.run_local_server(host='127.0.0.1', port=0, timeout_seconds=180,
                                          authorization_prompt_message='', success_message='Conta conectada. Pode fechar esta janela.',
                                          access_type='offline', prompt='consent')
            if not token.refresh_token:
                raise ValueError('Consentimento não forneceu acesso offline. Conecte novamente.')
            self.credentials.set_secret('drive_token', token.to_json())
            self.test_connection(config)

    def disconnect(self):
        with self.lock:
            self.credentials.delete_secret('drive_token')

    def _api(self):
        import httplib2
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_httplib2 import AuthorizedHttp
        from googleapiclient.discovery import build
        raw = self.credentials.get_secret('drive_token')
        if not raw:
            raise ValueError('Google Drive desconectado. Conecte a conta.')
        token = Credentials.from_authorized_user_info(json.loads(raw), self.SCOPES)
        if not token.valid:
            retry(lambda: token.refresh(Request()))
            self.credentials.set_secret('drive_token', token.to_json())
        return build('drive', 'v3', http=AuthorizedHttp(token, http=httplib2.Http(timeout=30)), cache_discovery=False)

    def _folder(self, api, config):
        folder = config['drive_folder_id']
        if not folder:
            # Persist only the public folder ID, never the OAuth response.
            folder = api.files().create(body={'name': 'Controle Financeiro Clinica - Backups',
                'mimeType': 'application/vnd.google-apps.folder'}, fields='id').execute()['id']
            self.config_store.save({'drive_folder_id': folder})
        info = retry(lambda: api.files().get(fileId=folder,
            fields='id,mimeType,trashed,capabilities(canAddChildren)', supportsAllDrives=True).execute())
        if info.get('trashed') or info.get('mimeType') != 'application/vnd.google-apps.folder' or not info.get('capabilities', {}).get('canAddChildren'):
            raise ValueError('A pasta Drive não está disponível para gravação.')
        return folder

    def test_connection(self, config):
        with self.lock:
            api = self._api()
            try:
                self._folder(api, config)
            finally:
                api.close()

    def upload_backup(self, path, config):
        from googleapiclient.http import MediaFileUpload
        with self.lock:
            api = self._api()
            media = None
            try:
                folder = self._folder(api, config)
                media = MediaFileUpload(str(path), mimetype='application/octet-stream', resumable=True)
                request = api.files().create(body={'name': path.name, 'parents': [folder]},
                    media_body=media, fields='id', supportsAllDrives=True)
                response = None
                while response is None:
                    _, response = retry(lambda: request.next_chunk(num_retries=0))
            finally:
                if media is not None:
                    media.stream().close()
                api.close()
