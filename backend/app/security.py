from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import get_config
from .db import get_db
from .models import Usuario

ALGORITMO = "HS256"
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def gerar_hash(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def conferir_senha(senha: str, hash_: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), hash_.encode("utf-8"))
    except ValueError:
        return False


def criar_token(usuario: Usuario) -> str:
    cfg = get_config()
    expira = datetime.now(timezone.utc) + timedelta(minutes=cfg.token_expira_minutos)
    # "ver" muda quando a senha muda, invalidando tokens antigos
    payload = {"sub": str(usuario.id), "exp": expira, "ver": usuario.senha_hash[-12:]}
    return jwt.encode(payload, cfg.secret_key, algorithm=ALGORITMO)


def usuario_atual(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> Usuario:
    erro = HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada. Entre novamente.",
                         headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, get_config().secret_key, algorithms=[ALGORITMO])
        usuario = db.get(Usuario, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise erro
    if not usuario or not usuario.ativo or payload.get("ver") != usuario.senha_hash[-12:]:
        raise erro
    return usuario


def equipe_interna(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    """Admin, editor e leitura: enxergam todas as áreas. Coordenador não."""
    if usuario.perfil not in ("admin", "editor", "leitura"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Seu perfil tem acesso apenas às movimentações da sua equipe.")
    return usuario


def pode_editar(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    """Admin e editor alimentam todas as áreas."""
    if usuario.perfil not in ("admin", "editor"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Seu perfil não pode alterar esta área.")
    return usuario


def pode_lancar_movimentacao(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    """Admin, editor e coordenador (este só para a própria equipe — conferido na rota)."""
    if usuario.perfil not in ("admin", "editor", "coordenador"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Seu perfil é somente leitura.")
    if usuario.perfil == "coordenador" and not usuario.coordenador_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Seu login de coordenador não está vinculado a um coordenador técnico. Fale com o administrador.")
    return usuario


def somente_admin(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    if usuario.perfil != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Apenas administradores podem fazer isso.")
    return usuario
