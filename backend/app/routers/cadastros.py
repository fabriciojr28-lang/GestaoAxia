"""Coordenadores, ativos, contratadas e colaboradores."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..schemas import (
    AtivoIn, AtivoOut, ColaboradorIn, ColaboradorOut, ContratadaIn, ContratadaOut,
    CoordenadorIn, CoordenadorOut, MovimentacaoOut,
)
from ..security import equipe_interna, pode_editar, somente_admin, usuario_atual
from ..servicos import aplicar_nome, salvar
from ..texto import chave_busca
from .movimentacoes import serializar as serializar_mov

router = APIRouter(prefix="/api", tags=["cadastros"])


def _buscar(db: Session, modelo, obj_id: int, nome: str):
    obj = db.get(modelo, obj_id)
    if not obj:
        raise HTTPException(404, f"{nome} não encontrado(a).")
    return obj


def _excluir(db: Session, obj):
    db.delete(obj)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(409, "Este cadastro está em uso em outros lançamentos e não pode ser excluído. "
                                 "Desative-o ou mescle com outro.")


# ---------------------------------------------------------------- coordenadores

@router.get("/coordenadores", response_model=list[CoordenadorOut])
def listar_coordenadores(_=Depends(usuario_atual), db: Session = Depends(get_db)):
    return db.scalars(select(m.Coordenador).order_by(m.Coordenador.nome)).all()


@router.post("/coordenadores", response_model=CoordenadorOut, status_code=201)
def criar_coordenador(dados: CoordenadorIn, u=Depends(pode_editar), db: Session = Depends(get_db)):
    obj = m.Coordenador(apelido=dados.apelido.strip().upper(), em_atividade=dados.em_atividade)
    aplicar_nome(obj, dados.nome)
    return salvar(db, obj, u, novo=True)


@router.put("/coordenadores/{obj_id}", response_model=CoordenadorOut)
def atualizar_coordenador(obj_id: int, dados: CoordenadorIn, u=Depends(pode_editar), db: Session = Depends(get_db)):
    obj = _buscar(db, m.Coordenador, obj_id, "Coordenador")
    aplicar_nome(obj, dados.nome)
    obj.apelido, obj.em_atividade = dados.apelido.strip().upper(), dados.em_atividade
    return salvar(db, obj, u, novo=False)


@router.delete("/coordenadores/{obj_id}", status_code=204)
def excluir_coordenador(obj_id: int, _=Depends(somente_admin), db: Session = Depends(get_db)):
    _excluir(db, _buscar(db, m.Coordenador, obj_id, "Coordenador"))


# ---------------------------------------------------------------- ativos

@router.get("/ativos", response_model=list[AtivoOut])
def listar_ativos(_=Depends(usuario_atual), db: Session = Depends(get_db)):
    return db.scalars(select(m.Ativo).order_by(m.Ativo.nome)).all()


def _preencher_ativo(obj: m.Ativo, dados: AtivoIn):
    aplicar_nome(obj, dados.nome)
    obj.numero = dados.numero.strip()
    obj.tipo_engenharia, obj.uf = dados.tipo_engenharia, dados.uf
    obj.municipio = " ".join(dados.municipio.split()).upper()
    obj.coordenador_id, obj.em_uso = dados.coordenador_id, dados.em_uso


@router.post("/ativos", response_model=AtivoOut, status_code=201)
def criar_ativo(dados: AtivoIn, u=Depends(pode_editar), db: Session = Depends(get_db)):
    obj = m.Ativo()
    _preencher_ativo(obj, dados)
    return salvar(db, obj, u, novo=True)


@router.put("/ativos/{obj_id}", response_model=AtivoOut)
def atualizar_ativo(obj_id: int, dados: AtivoIn, u=Depends(pode_editar), db: Session = Depends(get_db)):
    obj = _buscar(db, m.Ativo, obj_id, "Ativo")
    _preencher_ativo(obj, dados)
    return salvar(db, obj, u, novo=False)


@router.delete("/ativos/{obj_id}", status_code=204)
def excluir_ativo(obj_id: int, _=Depends(somente_admin), db: Session = Depends(get_db)):
    _excluir(db, _buscar(db, m.Ativo, obj_id, "Ativo"))


@router.post("/ativos/{origem_id}/mesclar/{destino_id}", response_model=AtivoOut)
def mesclar_ativos(origem_id: int, destino_id: int, _=Depends(somente_admin), db: Session = Depends(get_db)):
    """Junta dois cadastros do mesmo ativo (ex.: 'BOM NOME' e 'SE BOM NOME'):
    tudo que apontava para a origem passa a apontar para o destino e a origem é removida."""
    if origem_id == destino_id:
        raise HTTPException(400, "Escolha dois ativos diferentes.")
    origem = _buscar(db, m.Ativo, origem_id, "Ativo de origem")
    destino = _buscar(db, m.Ativo, destino_id, "Ativo de destino")
    db.execute(update(m.Colaborador).where(m.Colaborador.ativo_atual_id == origem.id).values(ativo_atual_id=destino.id))
    db.execute(update(m.Movimentacao).where(m.Movimentacao.ativo_id == origem.id).values(ativo_id=destino.id))
    db.execute(update(m.FechamentoMensal).where(m.FechamentoMensal.ativo_id == origem.id).values(ativo_id=destino.id))
    db.execute(update(m.RegistroPRO).where(m.RegistroPRO.ativo_id == origem.id).values(ativo_id=destino.id))
    for campo in ("numero", "tipo_engenharia", "uf", "municipio", "coordenador_id"):
        if not getattr(destino, campo) and getattr(origem, campo):
            setattr(destino, campo, getattr(origem, campo))
    db.delete(origem)
    db.commit()
    db.refresh(destino)
    return destino


# ---------------------------------------------------------------- contratadas

@router.get("/contratadas", response_model=list[ContratadaOut])
def listar_contratadas(_=Depends(equipe_interna), db: Session = Depends(get_db)):
    return db.scalars(select(m.Contratada).order_by(m.Contratada.nome)).all()


@router.post("/contratadas", response_model=ContratadaOut, status_code=201)
def criar_contratada(dados: ContratadaIn, u=Depends(pode_editar), db: Session = Depends(get_db)):
    obj = m.Contratada()
    aplicar_nome(obj, dados.nome)
    return salvar(db, obj, u, novo=True)


@router.put("/contratadas/{obj_id}", response_model=ContratadaOut)
def atualizar_contratada(obj_id: int, dados: ContratadaIn, u=Depends(pode_editar), db: Session = Depends(get_db)):
    obj = _buscar(db, m.Contratada, obj_id, "Contratada")
    aplicar_nome(obj, dados.nome)
    return salvar(db, obj, u, novo=False)


@router.delete("/contratadas/{obj_id}", status_code=204)
def excluir_contratada(obj_id: int, _=Depends(somente_admin), db: Session = Depends(get_db)):
    _excluir(db, _buscar(db, m.Contratada, obj_id, "Contratada"))


# ---------------------------------------------------------------- colaboradores

@router.get("/colaboradores", response_model=list[ColaboradorOut])
def listar_colaboradores(
    q: str = "", situacao: str = "", coordenador_id: int | None = None, ativo_id: int | None = None,
    tipo_engenharia: str = "", pendentes: bool = False,
    u: m.Usuario = Depends(usuario_atual), db: Session = Depends(get_db),
):
    consulta = select(m.Colaborador).order_by(m.Colaborador.nome)
    if u.eh_coordenador:
        consulta = consulta.where(m.Colaborador.coordenador_id == u.coordenador_id)
    if q:
        termo = f"%{chave_busca(q)}%"
        consulta = consulta.where(or_(m.Colaborador.chave.like(termo), m.Colaborador.matricula.like(f"%{q}%"),
                                      m.Colaborador.cpf.like(f"%{q}%")))
    if situacao:
        consulta = consulta.where(m.Colaborador.situacao == situacao)
    if coordenador_id:
        consulta = consulta.where(m.Colaborador.coordenador_id == coordenador_id)
    if ativo_id:
        consulta = consulta.where(m.Colaborador.ativo_atual_id == ativo_id)
    if tipo_engenharia:
        consulta = consulta.where(m.Colaborador.tipo_engenharia == tipo_engenharia)
    resultado = db.scalars(consulta).all()
    if pendentes:
        resultado = [c for c in resultado if c.pendencias_cadastro]
    return resultado


def _colaborador_visivel(db: Session, obj_id: int, u: m.Usuario) -> m.Colaborador:
    obj = _buscar(db, m.Colaborador, obj_id, "Colaborador")
    if u.eh_coordenador and obj.coordenador_id != u.coordenador_id:
        raise HTTPException(404, "Colaborador não encontrado.")
    return obj


@router.get("/colaboradores/{obj_id}", response_model=ColaboradorOut)
def obter_colaborador(obj_id: int, u: m.Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return _colaborador_visivel(db, obj_id, u)


@router.get("/colaboradores/{obj_id}/movimentacoes", response_model=list[MovimentacaoOut])
def historico_colaborador(obj_id: int, u: m.Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    _colaborador_visivel(db, obj_id, u)
    movs = db.scalars(select(m.Movimentacao).where(m.Movimentacao.colaborador_id == obj_id)
                      .order_by(m.Movimentacao.data_inicio.desc(), m.Movimentacao.id.desc())).all()
    return [serializar_mov(db, x) for x in movs]


def _preencher_colaborador(obj: m.Colaborador, dados: ColaboradorIn):
    aplicar_nome(obj, dados.nome)
    for campo, valor in dados.model_dump(exclude={"nome"}).items():
        if isinstance(valor, str):
            valor = valor.strip()
            if campo in ("funcao", "uf_origem", "cidade_origem", "matricula"):
                valor = " ".join(valor.split()).upper()
            if campo.startswith("email"):
                valor = valor.lower()
        setattr(obj, campo, valor)


@router.post("/colaboradores", response_model=ColaboradorOut, status_code=201)
def criar_colaborador(dados: ColaboradorIn, u=Depends(pode_editar), db: Session = Depends(get_db)):
    obj = m.Colaborador()
    _preencher_colaborador(obj, dados)
    return salvar(db, obj, u, novo=True)


@router.put("/colaboradores/{obj_id}", response_model=ColaboradorOut)
def atualizar_colaborador(obj_id: int, dados: ColaboradorIn, u=Depends(pode_editar), db: Session = Depends(get_db)):
    obj = _buscar(db, m.Colaborador, obj_id, "Colaborador")
    _preencher_colaborador(obj, dados)
    return salvar(db, obj, u, novo=False)


@router.delete("/colaboradores/{obj_id}", status_code=204)
def excluir_colaborador(obj_id: int, _=Depends(somente_admin), db: Session = Depends(get_db)):
    obj = _buscar(db, m.Colaborador, obj_id, "Colaborador")
    usos = db.scalar(select(func.count()).select_from(m.Movimentacao).where(m.Movimentacao.colaborador_id == obj_id))
    if usos:
        raise HTTPException(409, f"Colaborador tem {usos} movimentação(ões). Use a situação 'Desmobilizado' em vez de excluir.")
    _excluir(db, obj)
