"""Normalização dos booleanos recebidos pelos cadastros."""


def normalizar_booleano(valor, campo="ativo"):
    if valor is True or (type(valor) is int and valor == 1) or (isinstance(valor, str) and valor.lower() in ("1", "true")):
        return 1
    if valor is False or (type(valor) is int and valor == 0) or (isinstance(valor, str) and valor.lower() in ("0", "false")):
        return 0
    raise ValueError(f"O campo {campo} deve indicar sim ou não.")
