"""Regras de negócio do fluxo diário, separadas das rotas para serem testáveis."""
from calendar import monthrange
from datetime import date

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models as m
from .texto import chave_busca, limpar_nome


def primeiro_dia(valor: date) -> date:
    return valor.replace(day=1)


def limites_mes(mes: date) -> tuple[date, date]:
    return date(mes.year, mes.month, 1), date(mes.year, mes.month, monthrange(mes.year, mes.month)[1])


def salvar(db: Session, obj, usuario: m.Usuario | None, novo: bool):
    """Grava com auditoria e transforma violação de unicidade em mensagem amigável."""
    if usuario is not None:
        if novo:
            obj.criado_por_id = usuario.id
        obj.atualizado_por_id = usuario.id
    if novo:
        db.add(obj)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        texto = str(exc.orig).lower()
        if "unique" in texto and "chave" in texto:
            raise HTTPException(409, "Já existe um cadastro com esse nome (ignorando acentos e espaços).")
        if "unique" in texto:
            raise HTTPException(409, "Registro duplicado.")
        if "foreign key" in texto:
            raise HTTPException(409, "Este registro está em uso por outros lançamentos e não pode ser removido.")
        raise
    db.refresh(obj)
    return obj


def aplicar_nome(obj, nome: str):
    obj.nome = limpar_nome(nome)
    obj.chave = chave_busca(nome)


def mes_esta_fechado(db: Session, mes: date) -> bool:
    return db.get(m.MesFechado, primeiro_dia(mes)) is not None


def exigir_mes_aberto(db: Session, mes: date, usuario: m.Usuario):
    if usuario.perfil != "admin" and mes_esta_fechado(db, mes):
        raise HTTPException(423, f"O mês {mes:%m/%Y} já foi fechado. Peça a um administrador para reabrir.")


# ---------------------------------------------------------------- movimentações

def aplicar_movimentacao_no_colaborador(db: Session, mov: m.Movimentacao, hoje: date | None = None):
    """Mantém a situação/ativo atual do colaborador coerente com o lançamento mais recente.

    Só altera o colaborador se o lançamento já começou (data início <= hoje). Lançamentos
    futuros ficam registrados e passam a valer quando chegar a data.
    """
    hoje = hoje or date.today()
    if mov.data_inicio > hoje:
        return
    c = mov.colaborador
    if mov.tipo in m.TIPOS_COM_DESTINO or mov.tipo == "RETORNO_FOLGA":
        c.situacao = "MOBILIZADO"
        if mov.ativo_id:
            c.ativo_atual_id = mov.ativo_id
        # a pessoa passa para a equipe do coordenador da obra de destino (se a obra tiver um)
        destino = db.get(m.Ativo, mov.ativo_id) if mov.ativo_id else None
        novo_coord = (destino.coordenador_id if destino else None) or mov.coordenador_id
        if novo_coord:
            c.coordenador_id = novo_coord
    elif mov.tipo == "DESMOBILIZADO":
        c.situacao = "DESMOBILIZADO"
        c.data_demissao = c.data_demissao or mov.data_inicio
    elif mov.tipo in m.TIPOS_COM_PERIODO and (mov.data_fim is None or mov.data_fim >= hoje):
        c.situacao = {"FOLGA": "FOLGA", "FERIAS": "FERIAS", "AFASTADO": "AFASTADO"}[mov.tipo]


def movimentacoes_do_mes(db: Session, mes: date):
    ini, fim = limites_mes(mes)
    return db.scalars(
        select(m.Movimentacao)
        .where(m.Movimentacao.data_inicio <= fim)
        .where(or_(m.Movimentacao.data_fim.is_(None), m.Movimentacao.data_fim >= ini))
        .order_by(m.Movimentacao.data_inicio)
    ).all()


# ---------------------------------------------------------------- fechamento

def gerar_fechamento(db: Session, mes: date, usuario: m.Usuario) -> dict:
    """Cria/atualiza as linhas do fechamento do mês a partir do cadastro e das movimentações.

    - Inclui todo colaborador não desmobilizado e quem teve movimentação no mês.
    - Preenche ativo, coordenador, veículo e hospedagem do cadastro.
    - Calcula dias de folga, férias e afastamento que caem no mês.
    - Linhas já existentes mantêm o que foi editado à mão (veículo, hospedagem, observação),
      só os dias são recalculados.
    """
    mes = primeiro_dia(mes)
    ini, fim = limites_mes(mes)
    movs = movimentacoes_do_mes(db, mes)
    por_colab: dict[int, list[m.Movimentacao]] = {}
    for mov in movs:
        por_colab.setdefault(mov.colaborador_id, []).append(mov)

    colaboradores = db.scalars(
        select(m.Colaborador).where(
            or_(m.Colaborador.situacao != "DESMOBILIZADO", m.Colaborador.id.in_(por_colab.keys()))
        )
    ).all()
    existentes = {
        f.colaborador_id: f
        for f in db.scalars(select(m.FechamentoMensal).where(m.FechamentoMensal.mes == mes))
    }

    criadas = atualizadas = 0
    for c in colaboradores:
        lista = por_colab.get(c.id, [])
        dias = {"FOLGA": 0, "FERIAS": 0, "AFASTADO": 0}
        for mov in lista:
            if mov.tipo in dias:
                dias[mov.tipo] += mov.dias_no_mes(mes.year, mes.month)
        ultimo = lista[-1] if lista else None

        linha = existentes.get(c.id)
        nova = linha is None
        if nova:
            linha = m.FechamentoMensal(
                mes=mes, colaborador_id=c.id,
                ativo_id=c.ativo_atual_id, coordenador_id=c.coordenador_id,
                veiculo=c.veiculo, hospedagem=c.hospedagem,
                inicio=c.data_admissao if c.data_admissao and c.data_admissao >= ini else None,
            )
        linha.dias_folga = min(dias["FOLGA"], 31)
        linha.dias_ferias = min(dias["FERIAS"], 31)
        linha.dias_afastado = min(dias["AFASTADO"], 31)

        if nova:
            if c.situacao == "DESMOBILIZADO" or (ultimo and ultimo.tipo == "DESMOBILIZADO"):
                linha.status = "DESMOBILIZADO"
                linha.fim = (ultimo.data_inicio if ultimo and ultimo.tipo == "DESMOBILIZADO" else c.data_demissao)
            elif ultimo and ultimo.tipo == "TRANSFERIDO":
                linha.status = "TRANSFERIDO"
            else:
                linha.status = "MOBILIZADO_OBRA"
            resumo = [f"{m.TIPOS_MOVIMENTACAO[x.tipo]} {x.data_inicio:%d/%m}"
                      + (f" a {x.data_fim:%d/%m}" if x.data_fim else "") for x in lista]
            linha.observacao = "; ".join(resumo)
            db.add(linha)
            if usuario:
                linha.criado_por_id = usuario.id
            criadas += 1
        else:
            atualizadas += 1
        if usuario:
            linha.atualizado_por_id = usuario.id
    db.commit()
    return {"mes": mes.isoformat(), "criadas": criadas, "atualizadas": atualizadas}
