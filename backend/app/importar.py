"""Importa as planilhas originais para o banco.

Uso (dentro de backend/):
    python -m app.importar --pasta ..            # importa se o banco estiver vazio
    python -m app.importar --pasta .. --substituir   # apaga os dados (não os usuários) e reimporta

Arquivos esperados na pasta:
    EFETIVO SST BV*.xlsx                     -> colaboradores, coordenadores, ativos
    Faturamento Movimentacao Mensal*.xlsx    -> movimentações e fechamento do mês
    Controle Evidencias PRO*.xlsx            -> contratadas e registros de PRO
"""
import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from . import models as m
from .db import Base, SessionLocal, engine
from .texto import chave_busca, limpar_nome

ORIGEM = "[importado da planilha]"


# ---------------------------------------------------------------- leitura

def _achar(pasta: Path, prefixo: str) -> Path:
    candidatos = sorted(p for p in pasta.glob("*.xlsx") if chave_busca(p.stem).startswith(chave_busca(prefixo)))
    if not candidatos:
        raise SystemExit(f"Planilha '{prefixo}*.xlsx' não encontrada em {pasta.resolve()}")
    return candidatos[0]


def _linhas(ws, linha_cabecalho: int, coluna_obrigatoria: str):
    """Lê a aba como dicionários usando a chave normalizada do cabeçalho."""
    cab = [chave_busca(c.value) if c.value is not None else "" for c in ws[linha_cabecalho]]
    obrig = chave_busca(coluna_obrigatoria)
    for numero, valores in enumerate(ws.iter_rows(min_row=linha_cabecalho + 1, values_only=True),
                                     start=linha_cabecalho + 1):
        registro = {cab[i]: v for i, v in enumerate(valores) if i < len(cab) and cab[i]}
        if registro.get(obrig) not in (None, ""):
            registro["_linha"] = numero
            yield registro


def _txt(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return " ".join(str(valor).split())


def _data(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = _txt(valor)
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            pass
    return None


def _tipo_engenharia(valor) -> str:
    k = chave_busca(valor)
    if "TRANSMISS" in k:
        return "TRANSMISSAO"
    if "GERA" in k:
        return "GERACAO"
    if "PROJ" in k:
        return "PROJETOS"
    return ""


def _codigo(valor, opcoes) -> str:
    """'V1 - LEVE(MOB E KWID)' -> 'V1'."""
    k = _txt(valor).upper()[:2]
    return k if k in opcoes else ""


def _uf(valor) -> str:
    k = _txt(valor).upper()
    return k if k in m.UFS else ""


def _situacao_doc(valor) -> str:
    k = chave_busca(valor)
    return {"OK": "OK", "PENDENTE": "PENDENTE", "A VALIDAR": "A_VALIDAR", "N A": "NA", "NA": "NA"}.get(k, "PENDENTE")


TIPO_MOV = {
    "MOBILIZADO": "MOBILIZADO", "MOBILIZADO NA OBRA": "MOBILIZADO_OBRA", "TRANSFERIDO": "TRANSFERIDO",
    "FOLGA": "FOLGA", "RETORNO DE FOLGA": "RETORNO_FOLGA", "FERIAS": "FERIAS", "AFASTADO": "AFASTADO",
    "DESMOBILIZADO": "DESMOBILIZADO", "PENDENTE": "PENDENTE",
}


# ---------------------------------------------------------------- resolução de nomes

class Resolvedor:
    """Encontra ou cria cadastros, casando grafias diferentes do mesmo nome."""

    def __init__(self, db: Session, relatorio: list[str]):
        self.db = db
        self.rel = relatorio
        self.coord: dict[str, m.Coordenador] = {}
        self.ativos: dict[str, m.Ativo] = {}
        self.contratadas: dict[str, m.Contratada] = {}
        self.colabs: dict[str, m.Colaborador] = {}
        self.avisados: set[str] = set()

    def _aviso(self, texto: str):
        if texto not in self.avisados:
            self.avisados.add(texto)
            self.rel.append(texto)

    @staticmethod
    def _parecido(curto: str, completo: str) -> bool:
        """'RAFAEL BITU' ~ 'RAFAEL COSTA LEANDRO BITU'; 'CARLOS EDUARDO' ~ 'CARLOS EDUARDO DOS SANTOS'."""
        a, b = curto.split(), completo.split()
        if not a or not b or a[0] != b[0] or len(a) >= len(b):
            return False
        it = iter(b)
        return all(tok in it for tok in a)

    def _casar(self, chave: str, dicionario: dict):
        if chave in dicionario:
            return dicionario[chave]
        candidatos = {id(v): v for k, v in dicionario.items() if self._parecido(chave, k)}
        return next(iter(candidatos.values())) if len(candidatos) == 1 else None

    def coordenador(self, nome) -> m.Coordenador | None:
        chave = chave_busca(nome)
        if not chave:
            return None
        obj = self._casar(chave, self.coord)
        if obj:
            if chave != obj.chave:
                self.coord[chave] = obj
                if not obj.apelido:
                    obj.apelido = limpar_nome(nome)
            return obj
        obj = m.Coordenador(nome=limpar_nome(nome), chave=chave, apelido="")
        self.db.add(obj)
        self.coord[chave] = obj
        return obj

    def ativo(self, nome) -> m.Ativo | None:
        chave = chave_busca(nome)
        if not chave:
            return None
        if chave in self.ativos:
            return self.ativos[chave]
        # 'BOM NOME' x 'SE BOM NOME': mesma coisa quando só muda o prefixo SE
        sem_se = chave.removeprefix("SE ")
        for k, obj in self.ativos.items():
            if k.removeprefix("SE ") == sem_se:
                self.ativos[chave] = obj
                self._aviso(f"Ativo '{limpar_nome(nome)}' foi unificado com '{obj.nome}'.")
                return obj
        obj = m.Ativo(nome=limpar_nome(nome), chave=chave)
        self.db.add(obj)
        self.ativos[chave] = obj
        return obj

    def contratada(self, nome) -> m.Contratada | None:
        chave = chave_busca(nome)
        if not chave:
            return None
        if chave not in self.contratadas:
            obj = m.Contratada(nome=limpar_nome(nome), chave=chave)
            self.db.add(obj)
            self.contratadas[chave] = obj
        return self.contratadas[chave]

    def colaborador(self, nome, origem: str) -> m.Colaborador:
        chave = chave_busca(nome)
        obj = self._casar(chave, self.colabs)
        if obj:
            if chave != obj.chave:
                self.colabs[chave] = obj
                self._aviso(f"'{limpar_nome(nome)}' ({origem}) foi associado(a) a '{obj.nome}' do efetivo.")
            return obj
        obj = m.Colaborador(nome=limpar_nome(nome), chave=chave, situacao="MOBILIZADO")
        self.db.add(obj)
        self.colabs[chave] = obj
        self._aviso(f"'{limpar_nome(nome)}' aparece em {origem} mas não está no EFETIVO — "
                    "cadastrado(a) com dados mínimos, conferir.")
        return obj


# ---------------------------------------------------------------- importação

def _completar(obj, **valores):
    for campo, valor in valores.items():
        if valor not in (None, "") and not getattr(obj, campo):
            setattr(obj, campo, valor)


def importar(pasta: Path, substituir: bool = False) -> list[str]:
    Base.metadata.create_all(engine)
    rel: list[str] = []
    with SessionLocal() as db:
        existentes = db.scalar(select(func.count()).select_from(m.Colaborador))
        if existentes and not substituir:
            raise SystemExit(f"O banco já tem {existentes} colaboradores. Use --substituir para apagar e reimportar.")
        if substituir:
            for tabela in (m.RegistroPRO, m.FechamentoMensal, m.MesFechado, m.Movimentacao, m.Colaborador,
                           m.Contratada, m.Ativo, m.Coordenador):
                db.execute(delete(tabela))
            db.commit()

        r = Resolvedor(db, rel)
        arq_efetivo = _achar(pasta, "EFETIVO SST BV")
        arq_fat = _achar(pasta, "Faturamento Movimentacao Mensal")
        arq_pro = _achar(pasta, "Controle Evidencias PRO")

        # 1) EFETIVO — fonte principal das pessoas e dos coordenadores (nomes completos)
        wb = load_workbook(arq_efetivo, data_only=True, read_only=True)
        n_colab = 0
        for x in _linhas(wb.worksheets[0], 1, "COLABORADORES"):
            coord = r.coordenador(x.get("COORD TEC"))
            ativo = r.ativo(x.get("IDENTIFICACAO DO ATIVO"))
            tipo = _tipo_engenharia(x.get("TIPO DE ENGENHARIA"))
            if ativo:
                _completar(ativo, tipo_engenharia=tipo, coordenador=coord)
            nome = limpar_nome(x["COLABORADORES"])
            if chave_busca(nome) in r.colabs:
                rel.append(f"EFETIVO linha {x['_linha']}: '{nome}' repetido — mantida a primeira ocorrência.")
                continue
            status = chave_busca(x.get("STATUS"))
            c = m.Colaborador(
                nome=nome, chave=chave_busca(nome),
                cpf=_txt(x.get("CPF")), matricula=_txt(x.get("MATRICULA")),
                funcao=limpar_nome(x.get("FUNCAO")), tipo_engenharia=tipo,
                coordenador=coord, ativo_atual=ativo,
                situacao="DESMOBILIZADO" if status == "DESMOBILIZADO" else "MOBILIZADO",
                data_admissao=_data(x.get("DATA DE ADMISSAO")), data_demissao=_data(x.get("DATA DE DEMISSAO")),
                uf_origem=limpar_nome(x.get("ESTADO REGIAO NORDESTE")),
                cidade_origem=limpar_nome(x.get("CIDADE DE ORIGEM RESIDENCIA")),
                telefone_corporativo=_txt(x.get("TELEFONE CORPORATIVO")),
                telefone_pessoal=_txt(x.get("TELEFONE PESSOAL")),
                email_corporativo=_txt(x.get("E MAIL CORPORATIVO")).lower(),
                email_pessoal=_txt(x.get("E MAIL PESSOAL")).lower(),
            )
            db.add(c)
            r.colabs[c.chave] = c
            n_colab += 1
            if not coord:
                rel.append(f"EFETIVO linha {x['_linha']}: '{nome}' sem coordenador técnico.")
        wb.close()
        db.flush()

        # 2) FATURAMENTO — fechamento do mês e movimentações
        wb = load_workbook(arq_fat, data_only=True, read_only=True)
        abas = {chave_busca(ws.title): ws for ws in wb.worksheets}
        mes_ref = None
        dash = abas.get("DASHBOARD GERENCIAL")
        if dash is not None:
            mes_ref = _data(next(dash.iter_rows(min_row=4, max_row=4, min_col=3, max_col=3, values_only=True))[0])
        mes_ref = (mes_ref or date.today()).replace(day=1)

        n_fech = 0
        fechamento_por_colab: dict[int, m.FechamentoMensal] = {}
        for x in _linhas(abas["FECHAMENTO MENSAL"], 1, "PROFISSIONAL"):
            c = r.colaborador(x["PROFISSIONAL"], "FECHAMENTO MENSAL")
            coord = r.coordenador(x.get("COORD TEC"))
            ativo = r.ativo(x.get("ATIVO"))
            if ativo:
                _completar(ativo, numero=_txt(x.get("N ATIVO")), uf=_uf(x.get("ESTADO UF")),
                           municipio=limpar_nome(x.get("MUNICIPIO")),
                           tipo_engenharia=_tipo_engenharia(x.get("TIPO DE ENGENHARIA")), coordenador=coord)
            veiculo, hosp = _codigo(x.get("TIPO DE VEICULO"), m.VEICULOS), _codigo(x.get("HOSPEDAGEM"), m.HOSPEDAGENS)
            _completar(c, veiculo=veiculo, hospedagem=hosp, coordenador=coord, ativo_atual=ativo,
                       tipo_engenharia=_tipo_engenharia(x.get("TIPO DE ENGENHARIA")))
            status = TIPO_MOV.get(chave_busca(x.get("STATUS")), "PENDENTE")
            if status not in m.STATUS_FECHAMENTO:
                status = "MOBILIZADO_OBRA" if status in ("MOBILIZADO", "RETORNO_FOLGA") else "PENDENTE"
            inicio, fim = _data(x.get("INICIO")), _data(x.get("FIM"))
            obs = _txt(x.get("OBSERVACAO"))
            if inicio and fim and fim < inicio:
                rel.append(f"FECHAMENTO linha {x['_linha']} ({c.nome}): fim {fim:%d/%m/%Y} antes do início "
                           f"{inicio:%d/%m/%Y} — data fim removida, conferir.")
                obs = f"{obs} {ORIGEM} fim original {fim:%d/%m/%Y} anterior ao início.".strip()
                fim = None
            anterior = fechamento_por_colab.get(id(c))
            if anterior is not None:
                # mesma pessoa em duas linhas (ex.: transferida no mês): fica a linha mais recente
                antiga = (f"{ORIGEM} linha anterior: {anterior.ativo.nome if anterior.ativo else '-'} "
                          f"{m.STATUS_FECHAMENTO[anterior.status]}"
                          + (f" desde {anterior.inicio:%d/%m/%Y}" if anterior.inicio else ""))
                if (inicio or date.min) >= (anterior.inicio or date.min):
                    anterior.ativo, anterior.coordenador, anterior.status = ativo, coord, status
                    anterior.inicio, anterior.fim = inicio, fim
                    anterior.veiculo = veiculo or anterior.veiculo
                    anterior.hospedagem = hosp or anterior.hospedagem
                    anterior.observacao = " ".join(p for p in (obs, antiga) if p)
                else:
                    anterior.observacao = " ".join(p for p in (anterior.observacao, f"{ORIGEM} outra linha: "
                                                   f"{ativo.nome if ativo else '-'}") if p)
                rel.append(f"FECHAMENTO linha {x['_linha']}: '{c.nome}' aparece em mais de uma linha — "
                           "mantida a mais recente; a outra ficou na observação.")
                continue
            linha_f = m.FechamentoMensal(mes=mes_ref, colaborador=c, ativo=ativo, coordenador=coord, status=status,
                                         inicio=inicio, fim=fim, veiculo=veiculo, hospedagem=hosp, observacao=obs)
            db.add(linha_f)
            fechamento_por_colab[id(c)] = linha_f
            n_fech += 1
        db.flush()

        n_mov = 0
        aba_mov = next(ws for k, ws in abas.items() if k.startswith("MOVIMENTACAO"))
        for x in _linhas(aba_mov, 1, "COLABORADOR"):
            c = r.colaborador(x["COLABORADOR"], "MOVIMENTAÇÃO")
            tipo = TIPO_MOV.get(chave_busca(x.get("SITUACAO MOVIMENTACAO")))
            if not tipo:
                rel.append(f"MOVIMENTAÇÃO linha {x['_linha']} ({c.nome}): situação "
                           f"'{_txt(x.get('SITUACAO MOVIMENTACAO'))}' desconhecida — ignorada.")
                continue
            coord = r.coordenador(x.get("COORDENADOR RESPONSAVEL"))
            ativo = r.ativo(x.get("ATIVO OBRA"))
            if ativo:
                _completar(ativo, uf=_uf(x.get("ESTADO UF")), municipio=limpar_nome(x.get("MUNICIPIO")),
                           tipo_engenharia=_tipo_engenharia(x.get("TIPO DE ENGENHARIA")))
            inicio, fim = _data(x.get("DATA INICIO")), _data(x.get("DATA FIM"))
            obs = _txt(x.get("OBSERVACOES"))
            avisos = []
            if not inicio:
                if not fim:
                    rel.append(f"MOVIMENTAÇÃO linha {x['_linha']} ({c.nome}): sem datas — ignorada.")
                    continue
                inicio = fim
                avisos.append("data início ausente na planilha (usada a data fim)")
            if fim and fim < inicio:
                avisos.append(f"data fim original {fim:%d/%m/%Y} anterior ao início")
                fim = None
            if avisos:
                obs = f"{obs} {ORIGEM} {'; '.join(avisos)} — conferir.".strip()
                rel.append(f"MOVIMENTAÇÃO linha {x['_linha']} ({c.nome}): {'; '.join(avisos)}.")
            db.add(m.Movimentacao(colaborador=c, tipo=tipo, ativo=ativo, coordenador=coord,
                                  data_inicio=inicio, data_fim=fim, observacoes=obs))
            n_mov += 1
        wb.close()
        db.flush()

        # 3) PRO — contratadas e evidências
        wb = load_workbook(arq_pro, data_only=True, read_only=True)
        ws = next(w for w in wb.worksheets if chave_busca(w.title) == "CONTROLE PRO")
        n_pro = 0
        for x in _linhas(ws, 5, "ATIVO"):
            data_reg = _data(x.get("DATA"))
            if not data_reg:
                rel.append(f"PRO linha {x['_linha']}: sem data válida — usada a data de hoje, conferir.")
                data_reg = date.today()
            ativo = r.ativo(x["ATIVO"])
            coord = r.coordenador(x.get("COORDENADOR TECNICO"))
            _completar(ativo, coordenador=coord)
            link = _txt(x.get("LINK DA EVIDENCIA"))
            db.add(m.RegistroPRO(
                contratada=r.contratada(x.get("CONTRATADA") or "NÃO INFORMADA"), ativo=ativo, coordenador=coord,
                data=data_reg, atividade=_txt(x.get("ATIVIDADE")) or "(sem descrição)",
                apr=_situacao_doc(x.get("APR")), pex=_situacao_doc(x.get("PEX")), cr=_situacao_doc(x.get("CR")),
                lista_forum=_situacao_doc(x.get("LISTA DE FORUM DE APROVACAO")),
                lista_rpac=_situacao_doc(x.get("LISTA RPAC")),
                forum_aprovacao=_situacao_doc(x.get("FORUM DE APROVACAO")),
                observacao=_txt(x.get("OBSERVACAO ORIGINAL")),
                responsavel_acao=_txt(x.get("RESPONSAVEL PELA ACAO")),
                proxima_acao=_txt(x.get("PROXIMA ACAO")),
                link_evidencia=link if link.lower().startswith(("http://", "https://")) else "",
                prazo=_data(x.get("PRAZO")),
            ))
            n_pro += 1
        wb.close()
        db.commit()

        sem_ativo = db.scalar(select(func.count()).select_from(m.Colaborador)
                              .where(m.Colaborador.ativo_atual_id.is_(None), m.Colaborador.situacao != "DESMOBILIZADO"))
        resumo = [
            f"Colaboradores do efetivo: {n_colab} (total no sistema: {len({id(v) for v in r.colabs.values()})})",
            f"Coordenadores: {len({id(v) for v in r.coord.values()})}",
            f"Ativos / obras: {len({id(v) for v in r.ativos.values()})}",
            f"Contratadas: {len(r.contratadas)}",
            f"Movimentações: {n_mov}",
            f"Fechamento {mes_ref:%m/%Y}: {n_fech} linhas",
            f"Registros de PRO: {n_pro}",
            f"Colaboradores em campo sem ativo definido: {sem_ativo}",
        ]
    return resumo + ["", "Pontos para conferir:"] + (rel or ["nenhum"])


def main():
    parser = argparse.ArgumentParser(description="Importa as planilhas do GestaoAxia")
    parser.add_argument("--pasta", default="..", help="pasta onde estão os .xlsx")
    parser.add_argument("--substituir", action="store_true", help="apaga os dados atuais (exceto usuários) e reimporta")
    args = parser.parse_args()
    linhas = importar(Path(args.pasta), substituir=args.substituir)
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
