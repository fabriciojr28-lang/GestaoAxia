import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from . import models as m
from .config import get_config
from .db import Base, SessionLocal, engine
from .routers import auth, cadastros, fechamento, movimentacoes, painel, pro
from .security import gerar_hash


def garantir_admin() -> None:
    """Cria o administrador definido na stack (ADMIN_EMAIL / ADMIN_SENHA) se ainda não existir."""
    cfg = get_config()
    with SessionLocal() as db:
        admin = db.scalar(select(m.Usuario).where(m.Usuario.email == cfg.admin_email))
        if admin is None:
            db.add(m.Usuario(email=cfg.admin_email, nome=cfg.admin_nome, perfil="admin", ativo=True,
                             senha_hash=gerar_hash(cfg.admin_senha)))
            db.commit()


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    Base.metadata.create_all(engine)
    garantir_admin()
    yield


cfg = get_config()
app = FastAPI(title="GestaoAxia", version="0.1.0", lifespan=ciclo_de_vida,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)

if cfg.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=cfg.cors_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(RequestValidationError)
async def erro_validacao(_: Request, exc: RequestValidationError):
    """Devolve as mensagens de validação em português e num formato simples para a tela."""
    mensagens = []
    for erro in exc.errors():
        msg = str(erro.get("msg", "")).removeprefix("Value error, ")
        campo = ".".join(str(p) for p in erro.get("loc", []) if p not in ("body", "query"))
        if erro.get("type") == "missing":
            msg = "campo obrigatório"
        mensagens.append(f"{campo}: {msg}" if campo and erro.get("type") != "value_error" else msg)
    return JSONResponse(status_code=422, content={"detail": "; ".join(mensagens)})


for r in (auth.router, cadastros.router, movimentacoes.router, fechamento.router, pro.router, painel.router):
    app.include_router(r)


@app.get("/api/saude", include_in_schema=False)
def saude():
    return {"status": "ok"}


@app.get("/config.js", include_in_schema=False)
def config_js():
    """Configuração das telas vinda da stack (API_URL), lida pelo navegador antes do React."""
    conteudo = f"window.GESTAOAXIA_API = {json.dumps(cfg.api_url)};\n"
    return Response(conteudo, media_type="application/javascript", headers={"Cache-Control": "no-store"})


# Em produção o mesmo container serve o React já compilado (FRONTEND_DIST).
if cfg.frontend_dist:
    dist = Path(cfg.frontend_dist)
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{caminho:path}", include_in_schema=False)
    def spa(caminho: str):
        if caminho.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Rota não encontrada."})
        arquivo = (dist / caminho).resolve()
        if caminho and arquivo.is_file() and dist.resolve() in arquivo.parents:
            return FileResponse(arquivo)
        return FileResponse(dist / "index.html")
