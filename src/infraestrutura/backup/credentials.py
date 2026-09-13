"""Explicit Windows vault backend: never fall back to plaintext keyrings."""
import threading


class CredentialService:
    NAMES = ('r2_access_key_id', 'r2_secret_access_key', 'drive_client_secret', 'drive_token')

    def __init__(self, backend=None):
        self.backend = backend
        self.lock = threading.RLock()

    def _vault(self):
        if self.backend is None:
            from keyring.backends.Windows import WinVaultKeyring
            self.backend = WinVaultKeyring()
        return self.backend

    def _call(self, operation, name, *args):
        if name not in self.NAMES:
            raise ValueError('Credencial desconhecida.')
        with self.lock:
            try:
                return getattr(self._vault(), operation)('Controle_Financeiro_Clinica.Backup', name, *args)
            except Exception:
                raise ValueError('Credential Manager indisponível. Verifique o usuário Windows e as dependências.') from None

    def set_secret(self, name, value):
        self._call('set_password', name, value)

    def get_secret(self, name):
        return self._call('get_password', name)

    def delete_secret(self, name):
        if self.get_secret(name) is not None:
            self._call('delete_password', name)

    def configured(self):
        return {name: bool(self.get_secret(name)) for name in self.NAMES}
