"""Diagnósticos locais com rotação, sem corpos de requisição ou credenciais."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import threading
import traceback

PASTA_LOGS = Path(__file__).resolve().parents[2] / 'dados' / 'logs'
LOCK = threading.Lock()


def logger():
    log = logging.getLogger('clinica')
    with LOCK:
        if not log.handlers:
            PASTA_LOGS.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(PASTA_LOGS / 'sistema.log', maxBytes=2_000_000, backupCount=5, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            log.addHandler(handler)
            log.setLevel(logging.INFO)
            log.propagate = False
    return log


def registrar(evento, referencia, metodo, rota, status, erro=None):
    # Não registrar a mensagem da exceção: ela pode conter dados de entrada.
    # Caminhos e linhas bastam para localizar a falha com a referência da tela.
    pontos = '' if erro is None else ','.join(f'{Path(f.filename).name}:{f.lineno}:{f.name}' for f in traceback.extract_tb(erro.__traceback__))
    try:
        logger().log(logging.ERROR if erro else logging.INFO,
                     '%s referencia=%s metodo=%s rota=%s status=%s erro=%s pontos=%s',
                     evento, referencia, metodo, rota if rota.startswith('/api/') and len(rota)<120 else '/',
                     status, type(erro).__name__ if erro else '-', pontos)
    except OSError:
        # A falha do arquivo de diagnóstico não invalida um commit já feito.
        logging.getLogger('clinica.fallback').error('Diagnóstico local indisponível; referência=%s', referencia)
