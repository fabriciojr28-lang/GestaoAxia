import re
import unicodedata


def limpar_nome(valor: str) -> str:
    """Maiúsculas e espaços simples: '  se  milagres ii ' -> 'SE MILAGRES II'."""
    return " ".join(str(valor or "").split()).upper()


def chave_busca(valor: str) -> str:
    """Chave para detectar duplicatas: sem acento, sem pontuação, sem espaços extras.
    'AMÉRICO DOS SANTOS' e 'AMERICO  DOS SANTOS' geram a mesma chave."""
    sem_acento = unicodedata.normalize("NFKD", limpar_nome(valor))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", " ", sem_acento).strip()
