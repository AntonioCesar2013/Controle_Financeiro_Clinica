"""Validações escalares compartilhadas entre domínio e interface."""
import re


def inteiro(valor, nome, minimo=None):
    if isinstance(valor, bool) or not isinstance(valor, (str,int)) or not re.fullmatch(r'-?\d+', str(valor)):
        raise ValueError(f'O campo {nome} deve ser um número inteiro.')
    numero = int(valor)
    if abs(numero) > 2_000_000_000 or (minimo is not None and numero < minimo):
        raise ValueError(f'O campo {nome} está fora do intervalo permitido.')
    return numero

