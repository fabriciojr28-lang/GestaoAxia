"""Fechamento mensal (faturamento, veículos e hospedagem)."""
from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..schemas import FechamentoIn, FechamentoOut
from ..security import equipe_interna, pode_editar, somente_admin
from ..servicos import exigir_mes_aberto, gerar_fechamento, mes_esta_fechado, primeiro_dia, salvar

router = APIRouter(prefix="/api/fechamento", tags=["fechamento"])


def _linhas(db: Session, mes: date) -> list[m.FechamentoMensal]:
    return db.scalars(
        select(m.FechamentoMensal).join(m.FechamentoMensal.colaborador)
        .where(m.FechamentoMensal.mes == primeiro_dia(mes)).order_by(m.Colaborador.nome)
    ).all()


def _serializar(linha: m.FechamentoMensal) -> FechamentoOut:
    out = FechamentoOut.model_validate(linha)
    if linha.ativo:
        out.uf, out.municipio, out.ativo_numero = linha.ativo.uf, linha.ativo.municipio, linha.ativo.numero
    return out


@router.get("")
def listar(mes: date, _=Depends(equipe_interna), db: Session = Depends(get_db)):
    linhas = _linhas(db, mes)
    return {
        "mes": primeiro_dia(mes).isoformat(),
        "fechado": mes_esta_fechado(db, mes),
        "linhas": [_serializar(x) for x in linhas],
    }


@router.post("/gerar")
def gerar(mes: date, u: m.Usuario = Depends(pode_editar), db: Session = Depends(get_db)):
    exigir_mes_aberto(db, mes, u)
    return gerar_fechamento(db, mes, u)


@router.put("/{linha_id}", response_model=FechamentoOut)
def atualizar(linha_id: int, dados: FechamentoIn, u: m.Usuario = Depends(pode_editar), db: Session = Depends(get_db)):
    linha = db.get(m.FechamentoMensal, linha_id)
    if not linha:
        raise HTTPException(404, "Linha do fechamento não encontrada.")
    exigir_mes_aberto(db, linha.mes, u)
    for campo, valor in dados.model_dump().items():
        setattr(linha, campo, valor)
    salvar(db, linha, u, novo=False)
    return _serializar(linha)


@router.delete("/{linha_id}", status_code=204)
def excluir(linha_id: int, u: m.Usuario = Depends(pode_editar), db: Session = Depends(get_db)):
    linha = db.get(m.FechamentoMensal, linha_id)
    if not linha:
        raise HTTPException(404, "Linha do fechamento não encontrada.")
    exigir_mes_aberto(db, linha.mes, u)
    db.delete(linha)
    db.commit()


@router.post("/fechar", status_code=204)
def fechar_mes(mes: date, u: m.Usuario = Depends(somente_admin), db: Session = Depends(get_db)):
    if not mes_esta_fechado(db, mes):
        db.add(m.MesFechado(mes=primeiro_dia(mes), fechado_por_id=u.id))
        db.commit()


@router.post("/reabrir", status_code=204)
def reabrir_mes(mes: date, _=Depends(somente_admin), db: Session = Depends(get_db)):
    registro = db.get(m.MesFechado, primeiro_dia(mes))
    if registro:
        db.delete(registro)
        db.commit()


@router.get("/exportar")
def exportar(mes: date, _=Depends(equipe_interna), db: Session = Depends(get_db)):
    """Planilha no mesmo formato da aba FECHAMENTO MENSAL + resumo de veículos e hospedagem."""
    linhas = _linhas(db, mes)
    wb = Workbook()
    ws = wb.active
    ws.title = "FECHAMENTO MENSAL"
    cab = ["Nº ATIVO", "TIPO DE ENGENHARIA", "ATIVO", "ESTADO (UF)", "MUNICÍPIO", "COORD. TÉC", "PROFISSIONAL",
           "STATUS", "INÍCIO", "FIM", "TIPO DE VEÍCULO", "HOSPEDAGEM", "DIAS FOLGA", "DIAS FÉRIAS",
           "DIAS AFASTADO", "OBSERVAÇÃO"]
    ws.append(cab)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3A5F")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for x in linhas:
        a = x.ativo
        ws.append([
            a.numero if a else "", m.TIPOS_ENGENHARIA.get(a.tipo_engenharia, "") if a else "",
            a.nome if a else "", a.uf if a else "", a.municipio if a else "",
            x.coordenador.nome if x.coordenador else "", x.colaborador.nome,
            m.STATUS_FECHAMENTO.get(x.status, x.status), x.inicio, x.fim,
            m.VEICULOS.get(x.veiculo, ""), m.HOSPEDAGENS.get(x.hospedagem, ""),
            x.dias_folga, x.dias_ferias, x.dias_afastado, x.observacao,
        ])
    for linha in ws.iter_rows(min_row=2, min_col=9, max_col=10):
        for c in linha:
            c.number_format = "DD/MM/YYYY"
    larguras = [9, 22, 30, 8, 22, 32, 38, 20, 12, 12, 26, 28, 10, 10, 12, 50]
    for i, w in enumerate(larguras, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    resumo = wb.create_sheet("VEÍCULOS E HOSPEDAGEM")
    resumo.append(["TIPO DE VEÍCULO", "TOTAL", "", "HOSPEDAGEM", "TOTAL"])
    veic = [(r, sum(1 for x in linhas if x.veiculo == k)) for k, r in m.VEICULOS.items()]
    hosp = [(r, sum(1 for x in linhas if x.hospedagem == k)) for k, r in m.HOSPEDAGENS.items()]
    veic.append(("Sem tipo de veículo", sum(1 for x in linhas if not x.veiculo)))
    hosp.append(("Sem hospedagem", sum(1 for x in linhas if not x.hospedagem)))
    for i in range(max(len(veic), len(hosp))):
        v = veic[i] if i < len(veic) else ("", "")
        h = hosp[i] if i < len(hosp) else ("", "")
        resumo.append([v[0], v[1], "", h[0], h[1]])
    for c in resumo[1]:
        c.font = Font(bold=True)
    for col, w in zip("ABCDE", [28, 8, 3, 30, 8]):
        resumo.column_dimensions[col].width = w

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    nome = f"fechamento_{mes:%Y_%m}.xlsx"
    return StreamingResponse(
        buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
