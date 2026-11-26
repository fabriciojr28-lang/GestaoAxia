"""Indicadores do painel e listas de opções para os formulários."""
from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..security import equipe_interna, usuario_atual
from ..servicos import mes_esta_fechado, movimentacoes_do_mes, primeiro_dia

router = APIRouter(prefix="/api", tags=["painel"])


@router.get("/opcoes")
def opcoes(_=Depends(usuario_atual)):
    return {
        "perfis": m.PERFIS,
        "tipos_engenharia": m.TIPOS_ENGENHARIA,
        "ufs": m.UFS,
        "veiculos": m.VEICULOS,
        "hospedagens": m.HOSPEDAGENS,
        "situacoes_colaborador": m.SITUACOES_COLABORADOR,
        "tipos_movimentacao": m.TIPOS_MOVIMENTACAO,
        "tipos_com_periodo": sorted(m.TIPOS_COM_PERIODO),
        "tipos_com_destino": sorted(m.TIPOS_COM_DESTINO),
        "status_fechamento": m.STATUS_FECHAMENTO,
        "situacoes_doc": m.SITUACOES_DOC,
        "documentos_pro": m.DOCUMENTOS_PRO,
    }


@router.get("/painel")
def painel(mes: date | None = None, _=Depends(equipe_interna), db: Session = Depends(get_db)):
    mes = primeiro_dia(mes or date.today())
    colaboradores = db.scalars(select(m.Colaborador)).all()
    ativos_em_campo = [c for c in colaboradores if c.situacao != "DESMOBILIZADO"]

    movs = movimentacoes_do_mes(db, mes)
    movs_iniciadas = [x for x in movs if x.data_inicio >= mes]
    dias = Counter()
    em_folga_ferias = set()
    for x in movs:
        d = x.dias_no_mes(mes.year, mes.month)
        if d:
            dias[x.tipo] += d
            if x.tipo in ("FOLGA", "FERIAS"):
                em_folga_ferias.add(x.colaborador_id)

    # quem está fora hoje, pelas movimentações de período que cobrem a data de hoje
    hoje = date.today()
    fora_hoje: dict[str, set[int]] = {"FOLGA": set(), "FERIAS": set(), "AFASTADO": set()}
    for x in movimentacoes_do_mes(db, primeiro_dia(hoje)):
        if x.tipo in fora_hoje and x.data_inicio <= hoje <= (x.data_fim or x.data_inicio):
            fora_hoje[x.tipo].add(x.colaborador_id)

    pro = db.scalars(select(m.RegistroPRO)).all()
    status_pro = Counter(r.status_documental for r in pro)
    docs_em_aberto = Counter()
    docs_a_validar = Counter()
    for r in pro:
        for campo, rotulo in m.DOCUMENTOS_PRO.items():
            valor = getattr(r, campo)
            if valor == "PENDENTE":
                docs_em_aberto[rotulo] += 1
            elif valor == "A_VALIDAR":
                docs_a_validar[rotulo] += 1

    fechamento = db.scalars(select(m.FechamentoMensal).where(m.FechamentoMensal.mes == mes)).all()

    por_coord = Counter(c.coordenador.nome if c.coordenador else "Sem coordenador" for c in ativos_em_campo)
    por_ativo_pro: dict[str, dict] = {}
    for r in pro:
        item = por_ativo_pro.setdefault(r.ativo.nome, {"ativo": r.ativo.nome, "registros": 0, "completos": 0,
                                                        "docs_em_aberto": 0, "ok": 0, "aplicaveis": 0})
        item["registros"] += 1
        item["completos"] += r.status_documental == "Completo"
        item["docs_em_aberto"] += len(r.documentos_em_aberto)
        item["ok"] += r.qtd_ok
        item["aplicaveis"] += r.qtd_aplicaveis
    for item in por_ativo_pro.values():
        item["aderencia"] = round(item["ok"] / item["aplicaveis"], 4) if item["aplicaveis"] else None

    return {
        "mes": mes.isoformat(),
        "mes_fechado": mes_esta_fechado(db, mes),
        "efetivo": {
            "total": len(colaboradores),
            "em_campo": len(ativos_em_campo),
            "por_situacao": {k: sum(1 for c in colaboradores if c.situacao == k) for k in m.SITUACOES_COLABORADOR},
            "por_tipo_engenharia": dict(Counter(m.TIPOS_ENGENHARIA.get(c.tipo_engenharia, "Não informado")
                                                for c in ativos_em_campo)),
            "por_coordenador": dict(por_coord.most_common()),
            "cadastros_incompletos": sum(1 for c in colaboradores if c.pendencias_cadastro),
            "fora_hoje": {
                "total": len(set().union(*fora_hoje.values())),
                "folga": len(fora_hoje["FOLGA"]), "ferias": len(fora_hoje["FERIAS"]),
                "afastado": len(fora_hoje["AFASTADO"]),
            },
        },
        "movimentacoes": {
            "no_mes": len(movs_iniciadas),
            "pessoas_movimentadas": len({x.colaborador_id for x in movs_iniciadas}),
            "por_tipo": {m.TIPOS_MOVIMENTACAO[k]: v for k, v in Counter(x.tipo for x in movs_iniciadas).items()},
            "pessoas_folga_ferias": len(em_folga_ferias),
            "dias_folga": dias["FOLGA"],
            "dias_ferias": dias["FERIAS"],
            "dias_afastado": dias["AFASTADO"],
            "ultimas": [
                {"id": x.id, "colaborador": x.colaborador.nome, "tipo": m.TIPOS_MOVIMENTACAO[x.tipo],
                 "ativo": x.ativo.nome if x.ativo else "", "data_inicio": x.data_inicio.isoformat(),
                 "data_fim": x.data_fim.isoformat() if x.data_fim else None}
                for x in sorted(movs_iniciadas, key=lambda x: (x.data_inicio, x.id), reverse=True)[:8]
            ],
        },
        "pro": {
            "registros": len(pro),
            "completos": status_pro.get("Completo", 0),
            "incompletos": status_pro.get("Incompleto", 0),
            "sem_evidencia": status_pro.get("Sem evidência", 0),
            "completude": round(status_pro.get("Completo", 0) / len(pro), 4) if pro else None,
            "ativos": len({r.ativo_id for r in pro}),
            "docs_em_aberto": {rotulo: docs_em_aberto.get(rotulo, 0) for rotulo in m.DOCUMENTOS_PRO.values()},
            "docs_a_validar": {rotulo: docs_a_validar.get(rotulo, 0) for rotulo in m.DOCUMENTOS_PRO.values()},
            "prazos_vencidos": sum(1 for r in pro if r.prazo_vencido),
            "por_ativo": sorted(por_ativo_pro.values(), key=lambda i: (-i["docs_em_aberto"], i["ativo"])),
        },
        "fechamento": {
            "linhas": len(fechamento),
            "veiculos": {rot: sum(1 for f in fechamento if f.veiculo == k) for k, rot in m.VEICULOS.items()}
            | {"Sem tipo": sum(1 for f in fechamento if not f.veiculo)},
            "hospedagens": {rot: sum(1 for f in fechamento if f.hospedagem == k) for k, rot in m.HOSPEDAGENS.items()}
            | {"Sem hospedagem": sum(1 for f in fechamento if not f.hospedagem)},
        },
    }
