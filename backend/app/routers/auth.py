from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..schemas import Token, TrocarSenhaIn, UsuarioIn, UsuarioOut
from ..security import conferir_senha, criar_token, gerar_hash, somente_admin, usuario_atual

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form.username.strip().lower()
    usuario = db.scalar(select(m.Usuario).where(m.Usuario.email == email))
    if not usuario or not conferir_senha(form.password, usuario.senha_hash):
        raise HTTPException(401, "E-mail ou senha incorretos.")
    if not usuario.ativo:
        raise HTTPException(403, "Usuário desativado. Fale com um administrador.")
    usuario.ultimo_acesso = m.agora()
    db.commit()
    return Token(access_token=criar_token(usuario), usuario=UsuarioOut.model_validate(usuario))


@router.get("/auth/eu", response_model=UsuarioOut)
def eu(usuario: m.Usuario = Depends(usuario_atual)):
    return usuario


@router.post("/auth/senha", status_code=204)
def trocar_senha(dados: TrocarSenhaIn, usuario: m.Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    if not conferir_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(400, "Senha atual incorreta.")
    usuario.senha_hash = gerar_hash(dados.senha_nova)
    db.commit()


# ---------------------------------------------------------------- gestão de usuários (admin)

def _validar_coordenador(db: Session, dados: UsuarioIn, usuario_id: int | None = None):
    if not dados.coordenador_id:
        return
    if not db.get(m.Coordenador, dados.coordenador_id):
        raise HTTPException(422, "Coordenador técnico não encontrado.")
    consulta = select(m.Usuario).where(m.Usuario.coordenador_id == dados.coordenador_id,
                                       m.Usuario.perfil == "coordenador")
    if usuario_id:
        consulta = consulta.where(m.Usuario.id != usuario_id)
    outro = db.scalar(consulta)
    if outro:
        raise HTTPException(409, f"Esse coordenador já tem o login {outro.email}.")


@router.get("/usuarios", response_model=list[UsuarioOut])
def listar_usuarios(_: m.Usuario = Depends(somente_admin), db: Session = Depends(get_db)):
    return db.scalars(select(m.Usuario).order_by(m.Usuario.nome)).all()


@router.post("/usuarios", response_model=UsuarioOut, status_code=201)
def criar_usuario(dados: UsuarioIn, _: m.Usuario = Depends(somente_admin), db: Session = Depends(get_db)):
    if not dados.senha:
        raise HTTPException(422, "Informe uma senha inicial (mínimo 8 caracteres).")
    email = dados.email.lower()
    if db.scalar(select(m.Usuario).where(m.Usuario.email == email)):
        raise HTTPException(409, "Já existe um usuário com esse e-mail.")
    _validar_coordenador(db, dados)
    usuario = m.Usuario(email=email, nome=dados.nome.strip(), perfil=dados.perfil, ativo=dados.ativo,
                        coordenador_id=dados.coordenador_id, senha_hash=gerar_hash(dados.senha))
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.put("/usuarios/{usuario_id}", response_model=UsuarioOut)
def atualizar_usuario(usuario_id: int, dados: UsuarioIn, admin: m.Usuario = Depends(somente_admin),
                      db: Session = Depends(get_db)):
    usuario = db.get(m.Usuario, usuario_id)
    if not usuario:
        raise HTTPException(404, "Usuário não encontrado.")
    if usuario.id == admin.id and (dados.perfil != "admin" or not dados.ativo):
        raise HTTPException(400, "Você não pode remover seu próprio acesso de administrador.")
    email = dados.email.lower()
    outro = db.scalar(select(m.Usuario).where(m.Usuario.email == email, m.Usuario.id != usuario_id))
    if outro:
        raise HTTPException(409, "Já existe um usuário com esse e-mail.")
    _validar_coordenador(db, dados, usuario_id)
    usuario.email, usuario.nome = email, dados.nome.strip()
    usuario.perfil, usuario.ativo = dados.perfil, dados.ativo
    usuario.coordenador_id = dados.coordenador_id
    if dados.senha:
        usuario.senha_hash = gerar_hash(dados.senha)
    db.commit()
    db.refresh(usuario)
    return usuario
