"""Lançamento diário de movimentações (mobilização, transferência, folga, férias...).

Equivale à aba MOVIMENTAÇÃO(FATURAMENTO). Admin/editor lançam para qualquer pessoa;
cada coordenador lança apenas para os colaboradores da própria equipe.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..schemas import MovimentacaoIn, MovimentacaoOut
from ..security import pode_lancar_movimentacao, usuario_atual
from ..servicos import aplicar_movimentacao_no_colaborador, exigir_mes_aberto, limites_mes, salvar
from ..texto import chave_busca

router = APIRouter(prefix="/api/movimentacoes", tags=["movimentações"])


def serializar(db: Session, mov: m.Movimentacao) -> MovimentacaoOut:
    out = MovimentacaoOut.model_validate(mov)
    if mov.criado_por_id:
        autor = db.get(m.Usuario, mov.criado_por_id)
        out.criado_por_nome = autor.nome if autor else None
    return out


def filtro_da_equipe(usuario: m.Usuario):
    """Para coordenador: movimentações de quem é da equipe dele, ou que ele mesmo lançou/é responsável."""
    return or_(
        m.Colaborador.coordenador_id == usuario.coordenador_id,
        m.Movimentacao.coordenador_id == usuario.coordenador_id,
        m.Movimentacao.criado_por_id == usuario.id,
    )


def _pode_mexer(usuario: m.Usuario, mov: m.Movimentacao) -> bool:
    if not usuario.eh_coordenador:
        return True
    return (mov.coordenador_id == usuario.coordenador_id or mov.criado_por_id == usuario.id
            or mov.colaborador.coordenador_id == usuario.coordenador_id)


@router.get("", response_model=list[MovimentacaoOut])
def listar(
    mes: date | None = None, colaborador_id: int | None = None, tipo: str = "",
    coordenador_id: int | None = None, ativo_id: int | None = None, q: str = "",
    u: m.Usuario = Depends(usuario_atual), db: Session = Depends(get_db),
):
    consulta = (select(m.Movimentacao).join(m.Movimentacao.colaborador)
                .order_by(m.Movimentacao.data_inicio.desc(), m.Movimentacao.id.desc()))
    if u.eh_coordenador:
        consulta = consulta.where(filtro_da_equipe(u))
    if mes:
        ini, fim = limites_mes(mes)
        consulta = consulta.where(m.Movimentacao.data_inicio <= fim).where(
            or_(m.Movimentacao.data_fim.is_(None), m.Movimentacao.data_fim >= ini))
    if colaborador_id:
        consulta = consulta.where(m.Movimentacao.colaborador_id == colaborador_id)
    if tipo:
        consulta = consulta.where(m.Movimentacao.tipo == tipo)
    if coordenador_id:
        consulta = consulta.where(m.Movimentacao.coordenador_id == coordenador_id)
    if ativo_id:
        consulta = consulta.where(m.Movimentacao.ativo_id == ativo_id)
    if q:
        consulta = consulta.where(m.Colaborador.chave.like(f"%{chave_busca(q)}%"))
    autores = {x.id: x.nome for x in db.scalars(select(m.Usuario))}
    saida = []
    for mov in db.scalars(consulta.limit(1000)):
        out = MovimentacaoOut.model_validate(mov)
        out.criado_por_nome = autores.get(mov.criado_por_id)
        saida.append(out)
    return saida


def _validar(db: Session, dados: MovimentacaoIn, u: m.Usuario, checar_equipe: bool = True) -> m.Colaborador:
    colab = db.get(m.Colaborador, dados.colaborador_id)
    if not colab:
        raise HTTPException(422, "Colaborador não encontrado.")
    if dados.ativo_id and not db.get(m.Ativo, dados.ativo_id):
        raise HTTPException(422, "Ativo não encontrado.")
    if dados.coordenador_id and not db.get(m.Coordenador, dados.coordenador_id):
        raise HTTPException(422, "Coordenador não encontrado.")
    if checar_equipe and u.eh_coordenador and colab.coordenador_id != u.coordenador_id:
        raise HTTPException(403, f"{colab.nome} não faz parte da sua equipe. "
                                 "Peça ao coordenador dele(a) ou ao administrador.")
    return colab


@router.post("", response_model=MovimentacaoOut, status_code=201)
def criar(dados: MovimentacaoIn, u: m.Usuario = Depends(pode_lancar_movimentacao), db: Session = Depends(get_db)):
    colab = _validar(db, dados, u)
    exigir_mes_aberto(db, dados.data_inicio, u)
    mov = m.Movimentacao(**dados.model_dump())
    if u.eh_coordenador:
        mov.coordenador_id = u.coordenador_id  # o responsável é sempre quem lançou
    elif not mov.coordenador_id:
        mov.coordenador_id = colab.coordenador_id
    db.add(mov)
    db.flush()
    aplicar_movimentacao_no_colaborador(db, mov)
    salvar(db, mov, u, novo=True)
    return serializar(db, mov)


@router.put("/{mov_id}", response_model=MovimentacaoOut)
def atualizar(mov_id: int, dados: MovimentacaoIn, u: m.Usuario = Depends(pode_lancar_movimentacao),
              db: Session = Depends(get_db)):
    mov = db.get(m.Movimentacao, mov_id)
    if not mov or not _pode_mexer(u, mov):
        raise HTTPException(404, "Movimentação não encontrada.")
    # Se o próprio lançamento transferiu a pessoa para outra equipe, o coordenador ainda pode corrigi-lo;
    # mas não pode trocar o colaborador por alguém de fora da equipe.
    _validar(db, dados, u, checar_equipe=dados.colaborador_id != mov.colaborador_id)
    exigir_mes_aberto(db, mov.data_inicio, u)
    exigir_mes_aberto(db, dados.data_inicio, u)
    valores = dados.model_dump()
    if u.eh_coordenador:
        valores["coordenador_id"] = mov.coordenador_id or u.coordenador_id
    for campo, valor in valores.items():
        setattr(mov, campo, valor)
    db.flush()
    db.refresh(mov)
    aplicar_movimentacao_no_colaborador(db, mov)
    salvar(db, mov, u, novo=False)
    return serializar(db, mov)


@router.delete("/{mov_id}", status_code=204)
def excluir(mov_id: int, u: m.Usuario = Depends(pode_lancar_movimentacao), db: Session = Depends(get_db)):
    mov = db.get(m.Movimentacao, mov_id)
    if not mov or not _pode_mexer(u, mov):
        raise HTTPException(404, "Movimentação não encontrada.")
    exigir_mes_aberto(db, mov.data_inicio, u)
    db.delete(mov)
    db.commit()
