"""Controle de evidências do PRO (Planejamento de Risco Operacional)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..schemas import RegistroPROIn, RegistroPROOut
from ..security import equipe_interna, pode_editar
from ..servicos import salvar

router = APIRouter(prefix="/api/pro", tags=["PRO"])


@router.get("", response_model=list[RegistroPROOut])
def listar(
    ativo_id: int | None = None, coordenador_id: int | None = None, contratada_id: int | None = None,
    status: str = "", q: str = "", somente_em_aberto: bool = False,
    _=Depends(equipe_interna), db: Session = Depends(get_db),
):
    consulta = select(m.RegistroPRO).order_by(m.RegistroPRO.data.desc(), m.RegistroPRO.id.desc())
    if ativo_id:
        consulta = consulta.where(m.RegistroPRO.ativo_id == ativo_id)
    if coordenador_id:
        consulta = consulta.where(m.RegistroPRO.coordenador_id == coordenador_id)
    if contratada_id:
        consulta = consulta.where(m.RegistroPRO.contratada_id == contratada_id)
    if q:
        consulta = consulta.where(m.RegistroPRO.atividade.ilike(f"%{q}%"))
    registros = db.scalars(consulta).all()
    if status:
        registros = [r for r in registros if r.status_documental == status]
    if somente_em_aberto:
        registros = [r for r in registros if r.documentos_em_aberto]
    return registros


def _validar(db: Session, dados: RegistroPROIn):
    if not db.get(m.Contratada, dados.contratada_id):
        raise HTTPException(422, "Contratada não encontrada.")
    if not db.get(m.Ativo, dados.ativo_id):
        raise HTTPException(422, "Ativo não encontrado.")
    if dados.coordenador_id and not db.get(m.Coordenador, dados.coordenador_id):
        raise HTTPException(422, "Coordenador não encontrado.")


@router.get("/{reg_id}", response_model=RegistroPROOut)
def obter(reg_id: int, _=Depends(equipe_interna), db: Session = Depends(get_db)):
    reg = db.get(m.RegistroPRO, reg_id)
    if not reg:
        raise HTTPException(404, "Registro não encontrado.")
    return reg


@router.post("", response_model=RegistroPROOut, status_code=201)
def criar(dados: RegistroPROIn, u=Depends(pode_editar), db: Session = Depends(get_db)):
    _validar(db, dados)
    reg = m.RegistroPRO(**dados.model_dump())
    if not reg.coordenador_id:
        reg.coordenador_id = db.get(m.Ativo, dados.ativo_id).coordenador_id
    return salvar(db, reg, u, novo=True)


@router.put("/{reg_id}", response_model=RegistroPROOut)
def atualizar(reg_id: int, dados: RegistroPROIn, u=Depends(pode_editar), db: Session = Depends(get_db)):
    reg = db.get(m.RegistroPRO, reg_id)
    if not reg:
        raise HTTPException(404, "Registro não encontrado.")
    _validar(db, dados)
    for campo, valor in dados.model_dump().items():
        setattr(reg, campo, valor)
    salvar(db, reg, u, novo=False)
    db.refresh(reg)
    return reg


@router.delete("/{reg_id}", status_code=204)
def excluir(reg_id: int, _=Depends(pode_editar), db: Session = Depends(get_db)):
    reg = db.get(m.RegistroPRO, reg_id)
    if not reg:
        raise HTTPException(404, "Registro não encontrado.")
    db.delete(reg)
    db.commit()
