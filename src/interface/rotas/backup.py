"""Thin HTTP adapter; requests here MUST bypass financial idempotency/audit bodies."""
from src.nucleo import permissoes


def dispatch(handler, path, data=None):
    identity = handler._sessao()
    if identity is None:
        return handler._json({'erro': 'Sessão não autenticada.'}, 401)
    # Existing permission contract is currently permissive. Integrate roles HERE
    # via nucleo.permissoes; do not create a second identity/password store.
    if not permissoes.permitido(identity, 'sistema.backup.admin'):
        return handler._json({'erro': 'Acesso administrativo necessário.'}, 403)
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
