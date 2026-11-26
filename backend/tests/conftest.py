import os
import tempfile

import pytest

# Variáveis de teste definidas ANTES de importar a aplicação (que exige todas elas).
_tmp = tempfile.mkdtemp()
os.environ.update({
    "SECRET_KEY": "teste-" + "x" * 40,
    "TOKEN_EXPIRA_MINUTOS": "60",
    "DATABASE_PATH": os.path.join(_tmp, "teste.db"),
    "ADMIN_EMAIL": "admin@teste.com",
    "ADMIN_SENHA": "senha-admin-123",
    "ADMIN_NOME": "Admin Teste",
    "CORS_ORIGINS": "",
    "FRONTEND_DIST": "",
})

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        for tabela in reversed(Base.metadata.sorted_tables):
            conn.exec_driver_sql(f'DROP TABLE IF EXISTS "{tabela.name}"')
        conn.commit()
    with TestClient(app) as c:  # o lifespan recria as tabelas e o admin
        yield c


def entrar(client, email, senha):
    r = client.post("/api/auth/login", data={"username": email, "password": senha})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def admin(client):
    return entrar(client, "admin@teste.com", "senha-admin-123")
