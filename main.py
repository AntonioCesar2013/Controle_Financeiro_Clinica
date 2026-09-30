import os
import sys
import threading
from pathlib import Path

# pythonw não fornece console; configure os registros antes de importar o sistema.
if __name__ == "__main__":
    for stream, variable in [('stdout', 'CLINICA_LOG_SAIDA'), ('stderr', 'CLINICA_LOG_ERROS')]:
        if os.environ.get(variable):
            setattr(sys, stream, open(os.environ[variable], 'a', encoding='utf-8', buffering=1))

from src.interface.servidor import criar_servidor
from src.infraestrutura.uso_banco import BancoEmUsoError


def configurar_webview2_economico():
    """Reduz processos e tarefas de navegador que a interface local não utiliza."""
    os.environ.setdefault(
        "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS",
        " ".join((
            "--renderer-process-limit=1",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-domain-reliability",
            "--disable-sync",
            "--no-first-run",
        )),
    )


def main():
    configurar_webview2_economico()
    try:
        import webview
    except ImportError as erro:
        raise SystemExit(
            "A interface WebView2 não está instalada. Execute: "
            "python -m pip install -r requirements.txt"
        ) from erro

    try:
        servidor, endereco, backup = criar_servidor()
    except BancoEmUsoError:
        print('O sistema já está aberto ou o banco está indisponível para uso exclusivo.', file=sys.stderr)
        raise SystemExit(2)
    except ModuleNotFoundError as erro:
        raise SystemExit(
            f"Dependência do sistema ausente: {erro.name}. "
            "Execute iniciar.cmd para instalar os componentes necessários, ou "
            "python -m pip install -r requirements.txt no mesmo ambiente Python."
        ) from erro
    thread_servidor = threading.Thread(
        target=servidor.serve_forever,
        name="servidor-clinica",
        daemon=True,
    )
    thread_servidor.start()
    print(f"Controle Financeiro iniciado em janela WebView2: {endereco}")
    print(backup)

    try:
        janela = webview.create_window(
            "Controle Financeiro — Clínica da Cruz",
            endereco,
            width=1280,
            height=800,
            min_size=(980, 640),
            text_select=True,
        )
        janela.events.closed += servidor.shutdown
        webview.start(gui="edgechromium", debug=False,
                      icon=str(Path(__file__).resolve().parent / 'frontend' / 'assets' / 'logo-clinica.ico'))
    except Exception as erro:
        raise SystemExit(
            "Não foi possível iniciar o WebView2. Verifique se o Microsoft Edge "
            "WebView2 Runtime está instalado neste computador."
        ) from erro
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread_servidor.join(timeout=5)


if __name__ == "__main__":
    main()
