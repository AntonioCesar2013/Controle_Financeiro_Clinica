"""Thin HTTP adapter; requests here MUST bypass financial idempotency/audit bodies."""
from ipaddress import ip_address

def _acesso_local(handler):
    """Autoriza o modo sem login somente no servidor e cliente locais."""
    try:
        cliente = ip_address(handler.client_address[0]).is_loopback
        servidor = ip_address(handler.server.server_address[0]).is_loopback
        return cliente and servidor
    except (AttributeError, IndexError, TypeError, ValueError):
        return False


def dispatch(handler, path, data=None):
    # Instalação local de administrador único: nenhuma consulta de login ou sessão.
    if not _acesso_local(handler):
        return handler._json({'erro': 'O backup sem login está disponível somente no acesso local.'}, 403)
    service = handler.server.backup_service
    try:
        if data is None:
            if path == '/api/backup/status':
                return handler._json(service.status())
            if path == '/api/backup/config':
                return handler._json(service.settings())
        else:
            origin = handler.headers.get('Origin')
            if origin and origin != 'http://' + handler.headers.get('Host', ''):
                return handler._json({'erro': 'Origem não autorizada.'}, 403)
            if handler.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return handler._json({'erro': 'Envie JSON.'}, 415)
            if path == '/api/backup/config':
                if not service.lock.acquire(blocking=False):
                    return handler._json({'erro': 'Aguarde a operação em andamento.'}, 409)
                try:
                    return handler._json(service.save_settings(data))
                finally:
                    service.lock.release()
            if path == '/api/backup/folder':
                from src.infraestrutura.backup.folder import select_directory
                return handler._json({'directory': select_directory()})
            action = path.removeprefix('/api/backup/')
            if action in ('backup', 'connect', 'disconnect', 'test-r2', 'test-drive'):
                accepted = service.start(action)
                return handler._json({'accepted': accepted}, 202 if accepted else 409)
        return handler._json({'erro': 'Rota não encontrada.'}, 404)
    except Exception:
        return handler._json({'erro': 'Não foi possível concluir. Verifique os campos, a pasta e o Credential Manager.'}, 400)
