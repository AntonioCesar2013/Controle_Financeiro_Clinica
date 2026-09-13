import threading

LOCK = threading.Lock()


def select_directory():
    import webview
    if not LOCK.acquire(blocking=False):
        raise ValueError('Seletor já aberto.')
    try:
        if not webview.windows:
            raise ValueError('Informe o caminho manualmente no navegador.')
        selected = webview.windows[0].create_file_dialog(webview.FileDialog.FOLDER)
        return selected[0] if selected else ''
    finally:
        LOCK.release()
