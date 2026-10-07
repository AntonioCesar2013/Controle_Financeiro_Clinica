import os
import sys
import threading
import ctypes
from pathlib import Path

# pythonw não fornece console; configure os registros antes de importar o sistema.
if __name__ == "__main__":
    for stream, variable in [('stdout', 'CLINICA_LOG_SAIDA'), ('stderr', 'CLINICA_LOG_ERROS')]:
        if os.environ.get(variable):
            setattr(sys, stream, open(os.environ[variable], 'a', encoding='utf-8', buffering=1))

from src.interface.servidor import criar_servidor
from src.infraestrutura.uso_banco import BancoEmUsoError


TITULO_JANELA = "Controle Financeiro — Clínica da Cruz"
ID_APLICATIVO_WINDOWS = "ClinicaDaCruz.ControleFinanceiro"


def caminho_icone():
    return Path(__file__).resolve().parent / "frontend" / "assets" / "logo-clinica.ico"


def configurar_identidade_windows():
    """Separa o aplicativo do Python e permite ao Windows usar seu próprio ícone."""
    if sys.platform != "win32":
        return
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ID_APLICATIVO_WINDOWS)


def aplicar_icone_janela_windows():
    """Aplica o ícone grande e pequeno à janela nativa e à barra de tarefas."""
    if sys.platform != "win32":
        return
    user32 = ctypes.windll.user32
    identificador = user32.FindWindowW(None, TITULO_JANELA)
    if not identificador:
        return
    carregar_do_arquivo = 0x0010
    tamanho_padrao = 0x0040
    icone = user32.LoadImageW(None, str(caminho_icone()), 1, 0, 0, carregar_do_arquivo | tamanho_padrao)
    if icone:
        user32.SendMessageW(identificador, 0x0080, 1, icone)
        user32.SendMessageW(identificador, 0x0080, 0, icone)


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
    configurar_identidade_windows()
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
            TITULO_JANELA,
            endereco,
            width=1280,
            height=800,
            min_size=(980, 640),
            maximized=True,
            text_select=True,
        )
        janela.events.closed += servidor.shutdown
        janela.events.loaded += aplicar_icone_janela_windows
        webview.start(gui="edgechromium", debug=False,
                      icon=str(caminho_icone()))
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
