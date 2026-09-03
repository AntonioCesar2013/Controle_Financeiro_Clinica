import threading

from src.interface.servidor import criar_servidor


def main():
    try:
        import webview
    except ImportError as erro:
        raise SystemExit(
            "A interface WebView2 não está instalada. Execute: "
            "python -m pip install -r requirements.txt"
        ) from erro

    servidor, endereco, backup = criar_servidor()
    thread_servidor = threading.Thread(
        target=servidor.serve_forever,
        name="servidor-clinica",
        daemon=True,
    )
    thread_servidor.start()
    print(f"Controle Financeiro iniciado em janela WebView2: {endereco}")
    print(f"Backup diário verificado: {backup}")

    janela = webview.create_window(
        "Controle Financeiro — Clínica da Cruz",
        endereco,
        width=1280,
        height=800,
        min_size=(980, 640),
        text_select=True,
    )
    janela.events.closed += servidor.shutdown
    try:
        webview.start(gui="edgechromium", debug=False)
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
