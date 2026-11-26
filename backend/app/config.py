"""Configuração lida 100% de variáveis de ambiente.

Na VPS as variáveis vêm da stack do Portainer (docker-compose.yml).
Localmente, você pode criar backend/.env (ignorado pelo git) — veja .env.example.
Nenhum valor é definido no código: se faltar alguma variável, a aplicação não sobe
e informa exatamente qual está faltando.
"""
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

OBRIGATORIAS = [
    "SECRET_KEY",
    "TOKEN_EXPIRA_MINUTOS",
    "DATABASE_PATH",
    "ADMIN_EMAIL",
    "ADMIN_SENHA",
    "ADMIN_NOME",
    "CORS_ORIGINS",
    "FRONTEND_DIST",
]


def _carregar_env_local() -> None:
    """Para desenvolvimento local: lê backend/.env se existir (não sobrescreve o ambiente)."""
    arquivo = Path(__file__).resolve().parent.parent / ".env"
    if not arquivo.exists():
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Config:
    secret_key: str
    token_expira_minutos: int
    database_path: str
    admin_email: str
    admin_senha: str
    admin_nome: str
    cors_origins: list[str]
    frontend_dist: str  # pasta do build do React; vazio = não servir frontend (dev)


@lru_cache
def get_config() -> Config:
    _carregar_env_local()
    faltando = [nome for nome in OBRIGATORIAS if nome not in os.environ]
    if faltando:
        raise RuntimeError(
            "Variáveis de ambiente obrigatórias não definidas: " + ", ".join(faltando)
            + ". Configure-as na stack do Portainer (ou em backend/.env localmente)."
        )
    if len(os.environ["SECRET_KEY"]) < 32:
        raise RuntimeError("SECRET_KEY deve ter pelo menos 32 caracteres.")
    return Config(
        secret_key=os.environ["SECRET_KEY"],
        token_expira_minutos=int(os.environ["TOKEN_EXPIRA_MINUTOS"]),
        database_path=os.environ["DATABASE_PATH"],
        admin_email=os.environ["ADMIN_EMAIL"].strip().lower(),
        admin_senha=os.environ["ADMIN_SENHA"],
        admin_nome=os.environ["ADMIN_NOME"],
        cors_origins=[o.strip() for o in os.environ["CORS_ORIGINS"].split(",") if o.strip()],
        frontend_dist=os.environ["FRONTEND_DIST"].strip(),
    )
