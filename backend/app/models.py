"""Tabelas do sistema.

Um cadastro único (coordenadores, ativos, contratadas, colaboradores) alimenta
os três controles que antes eram planilhas separadas:
  - Movimentações (o lançamento diário)
  - Fechamento mensal (faturamento, veículos e hospedagem)
  - Registros de PRO (evidências documentais)
"""
from calendar import monthrange
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# ---------------------------------------------------------------- opções (listas)
# código gravado no banco -> rótulo exibido na tela

PERFIS = {
    "admin": "Administrador",
    "editor": "Editor (alimenta tudo)",
    "coordenador": "Coordenador (só movimentações da sua equipe)",
    "leitura": "Somente leitura",
}
PERFIS_INTERNOS = {"admin", "editor", "leitura"}  # veem todas as áreas

TIPOS_ENGENHARIA = {
    "TRANSMISSAO": "Transmissão",
    "GERACAO": "Geração",
    "PROJETOS": "Projetos Estratégicos",
}

UFS = ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE", "AC", "AM", "AP", "DF", "ES",
       "GO", "MG", "MS", "MT", "PA", "PR", "RJ", "RO", "RR", "RS", "SC", "SP", "TO"]

VEICULOS = {
    "V0": "V0 - Não tem",
    "V1": "V1 - Leve (Mob e Kwid)",
    "V2": "V2 - 4x4",
    "V3": "V3 - SUV",
    "V4": "V4 - Sedan (Argo/Onix)",
}

HOSPEDAGENS = {
    "H0": "H0 - Local",
    "H1": "H1 - Hotel eventualmente",
    "H2": "H2 - Hotel permanente",
}

SITUACOES_COLABORADOR = {
    "MOBILIZADO": "Mobilizado",
    "FOLGA": "Em folga",
    "FERIAS": "Em férias",
    "AFASTADO": "Afastado",
    "DESMOBILIZADO": "Desmobilizado",
}

TIPOS_MOVIMENTACAO = {
    "MOBILIZADO": "Mobilização",
    "MOBILIZADO_OBRA": "Mobilizado na obra",
    "TRANSFERIDO": "Transferência",
    "FOLGA": "Folga",
    "RETORNO_FOLGA": "Retorno de folga",
    "FERIAS": "Férias",
    "AFASTADO": "Afastamento",
    "DESMOBILIZADO": "Desmobilização",
    "PENDENTE": "Pendente",
}
TIPOS_COM_PERIODO = {"FOLGA", "FERIAS", "AFASTADO"}          # exigem data fim e contam dias
TIPOS_COM_DESTINO = {"MOBILIZADO", "MOBILIZADO_OBRA", "TRANSFERIDO"}  # exigem ativo de destino

STATUS_FECHAMENTO = {
    "MOBILIZADO_OBRA": "Mobilizado na obra",
    "FOLGA": "Folga",
    "FERIAS": "Férias",
    "AFASTADO": "Afastado",
    "TRANSFERIDO": "Transferido",
    "DESMOBILIZADO": "Desmobilizado",
    "PENDENTE": "Pendente",
}

SITUACOES_DOC = {"OK": "OK", "PENDENTE": "Pendente", "A_VALIDAR": "A validar", "NA": "N/A"}

DOCUMENTOS_PRO = {
    "apr": "APR",
    "pex": "PEX",
    "cr": "CR",
    "lista_forum": "Lista do fórum",
    "lista_rpac": "Lista RPAC",
    "forum_aprovacao": "Fórum de aprovação",
}


def agora():
    return datetime.now(timezone.utc)


class Auditoria:
    """Quem criou/alterou cada registro — importante com vários usuários."""

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora, onupdate=agora)
    criado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    atualizado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))


# ---------------------------------------------------------------- usuários

class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(150))
    senha_hash: Mapped[str] = mapped_column(String(200))
    perfil: Mapped[str] = mapped_column(String(20), default="leitura")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    # obrigatório quando perfil == "coordenador": define qual equipe ele enxerga
    coordenador_id: Mapped[int | None] = mapped_column(
        ForeignKey("coordenadores.id", ondelete="SET NULL", use_alter=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    ultimo_acesso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    coordenador: Mapped["Coordenador | None"] = relationship(foreign_keys=[coordenador_id])

    @property
    def eh_coordenador(self) -> bool:
        return self.perfil == "coordenador"


# ---------------------------------------------------------------- cadastros

class Coordenador(Auditoria, Base):
    __tablename__ = "coordenadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    chave: Mapped[str] = mapped_column(String(200), unique=True)
    apelido: Mapped[str] = mapped_column(String(80), default="")
    em_atividade: Mapped[bool] = mapped_column(Boolean, default=True)


class Ativo(Auditoria, Base):
    __tablename__ = "ativos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    chave: Mapped[str] = mapped_column(String(200), unique=True)
    numero: Mapped[str] = mapped_column(String(20), default="")
    tipo_engenharia: Mapped[str] = mapped_column(String(20), default="")
    uf: Mapped[str] = mapped_column(String(2), default="")
    municipio: Mapped[str] = mapped_column(String(100), default="")
    coordenador_id: Mapped[int | None] = mapped_column(ForeignKey("coordenadores.id", ondelete="SET NULL"))
    em_uso: Mapped[bool] = mapped_column(Boolean, default=True)

    coordenador: Mapped[Coordenador | None] = relationship()


class Contratada(Auditoria, Base):
    __tablename__ = "contratadas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    chave: Mapped[str] = mapped_column(String(200), unique=True)


class Colaborador(Auditoria, Base):
    __tablename__ = "colaboradores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    chave: Mapped[str] = mapped_column(String(200), unique=True)
    cpf: Mapped[str] = mapped_column(String(14), default="")
    matricula: Mapped[str] = mapped_column(String(20), default="")
    funcao: Mapped[str] = mapped_column(String(80), default="")
    tipo_engenharia: Mapped[str] = mapped_column(String(20), default="")
    coordenador_id: Mapped[int | None] = mapped_column(ForeignKey("coordenadores.id", ondelete="SET NULL"))
    ativo_atual_id: Mapped[int | None] = mapped_column(ForeignKey("ativos.id", ondelete="SET NULL"))
    situacao: Mapped[str] = mapped_column(String(20), default="MOBILIZADO")
    data_admissao: Mapped[date | None] = mapped_column(Date)
    data_demissao: Mapped[date | None] = mapped_column(Date)
    uf_origem: Mapped[str] = mapped_column(String(40), default="")
    cidade_origem: Mapped[str] = mapped_column(String(100), default="")
    telefone_corporativo: Mapped[str] = mapped_column(String(30), default="")
    telefone_pessoal: Mapped[str] = mapped_column(String(30), default="")
    email_corporativo: Mapped[str] = mapped_column(String(200), default="")
    email_pessoal: Mapped[str] = mapped_column(String(200), default="")
    veiculo: Mapped[str] = mapped_column(String(2), default="")
    hospedagem: Mapped[str] = mapped_column(String(2), default="")

    coordenador: Mapped[Coordenador | None] = relationship()
    ativo_atual: Mapped[Ativo | None] = relationship()

    @property
    def pendencias_cadastro(self) -> list[str]:
        faltando = []
        if not self.cpf:
            faltando.append("CPF")
        if not self.matricula:
            faltando.append("matrícula")
        if not self.funcao:
            faltando.append("função")
        if not self.ativo_atual_id and self.situacao != "DESMOBILIZADO":
            faltando.append("ativo")
        return faltando


# ---------------------------------------------------------------- fluxo diário

class Movimentacao(Auditoria, Base):
    __tablename__ = "movimentacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    colaborador_id: Mapped[int] = mapped_column(ForeignKey("colaboradores.id", ondelete="RESTRICT"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    ativo_id: Mapped[int | None] = mapped_column(ForeignKey("ativos.id", ondelete="RESTRICT"))
    coordenador_id: Mapped[int | None] = mapped_column(ForeignKey("coordenadores.id", ondelete="SET NULL"))
    data_inicio: Mapped[date] = mapped_column(Date, index=True)
    data_fim: Mapped[date | None] = mapped_column(Date, index=True)
    observacoes: Mapped[str] = mapped_column(Text, default="")

    colaborador: Mapped[Colaborador] = relationship()
    ativo: Mapped[Ativo | None] = relationship()
    coordenador: Mapped[Coordenador | None] = relationship()

    def dias_no_mes(self, ano: int, mes: int) -> int:
        """Dias do período (folga/férias/afastamento) que caem dentro do mês, inclusive."""
        if self.tipo not in TIPOS_COM_PERIODO:
            return 0
        inicio_mes = date(ano, mes, 1)
        fim_mes = date(ano, mes, monthrange(ano, mes)[1])
        ini = max(self.data_inicio, inicio_mes)
        fim = min(self.data_fim or self.data_inicio, fim_mes)
        return max((fim - ini).days + 1, 0)


class FechamentoMensal(Auditoria, Base):
    __tablename__ = "fechamento_mensal"
    __table_args__ = (UniqueConstraint("mes", "colaborador_id", name="uq_fechamento_mes_colaborador"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    mes: Mapped[date] = mapped_column(Date, index=True)  # sempre dia 1
    colaborador_id: Mapped[int] = mapped_column(ForeignKey("colaboradores.id", ondelete="RESTRICT"))
    ativo_id: Mapped[int | None] = mapped_column(ForeignKey("ativos.id", ondelete="RESTRICT"))
    coordenador_id: Mapped[int | None] = mapped_column(ForeignKey("coordenadores.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), default="MOBILIZADO_OBRA")
    inicio: Mapped[date | None] = mapped_column(Date)
    fim: Mapped[date | None] = mapped_column(Date)
    veiculo: Mapped[str] = mapped_column(String(2), default="")
    hospedagem: Mapped[str] = mapped_column(String(2), default="")
    dias_folga: Mapped[int] = mapped_column(Integer, default=0)
    dias_ferias: Mapped[int] = mapped_column(Integer, default=0)
    dias_afastado: Mapped[int] = mapped_column(Integer, default=0)
    observacao: Mapped[str] = mapped_column(Text, default="")

    colaborador: Mapped[Colaborador] = relationship()
    ativo: Mapped[Ativo | None] = relationship()
    coordenador: Mapped[Coordenador | None] = relationship()


class MesFechado(Base):
    """Quando um mês é fechado, só administradores podem alterá-lo."""

    __tablename__ = "meses_fechados"

    mes: Mapped[date] = mapped_column(Date, primary_key=True)
    fechado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    fechado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))


# ---------------------------------------------------------------- evidências PRO

class RegistroPRO(Auditoria, Base):
    __tablename__ = "registros_pro"

    id: Mapped[int] = mapped_column(primary_key=True)
    contratada_id: Mapped[int] = mapped_column(ForeignKey("contratadas.id", ondelete="RESTRICT"))
    ativo_id: Mapped[int] = mapped_column(ForeignKey("ativos.id", ondelete="RESTRICT"), index=True)
    coordenador_id: Mapped[int | None] = mapped_column(ForeignKey("coordenadores.id", ondelete="SET NULL"))
    data: Mapped[date] = mapped_column(Date, index=True)
    atividade: Mapped[str] = mapped_column(Text)
    apr: Mapped[str] = mapped_column(String(10), default="PENDENTE")
    pex: Mapped[str] = mapped_column(String(10), default="PENDENTE")
    cr: Mapped[str] = mapped_column(String(10), default="PENDENTE")
    lista_forum: Mapped[str] = mapped_column(String(10), default="PENDENTE")
    lista_rpac: Mapped[str] = mapped_column(String(10), default="PENDENTE")
    forum_aprovacao: Mapped[str] = mapped_column(String(10), default="PENDENTE")
    observacao: Mapped[str] = mapped_column(Text, default="")
    responsavel_acao: Mapped[str] = mapped_column(String(120), default="")
    proxima_acao: Mapped[str] = mapped_column(String(255), default="")
    link_evidencia: Mapped[str] = mapped_column(String(500), default="")
    prazo: Mapped[date | None] = mapped_column(Date)

    contratada: Mapped[Contratada] = relationship()
    ativo: Mapped[Ativo] = relationship()
    coordenador: Mapped[Coordenador | None] = relationship()

    def _situacoes(self) -> list[str]:
        return [getattr(self, campo) for campo in DOCUMENTOS_PRO]

    @property
    def qtd_ok(self) -> int:
        return sum(1 for s in self._situacoes() if s == "OK")

    @property
    def qtd_aplicaveis(self) -> int:
        return sum(1 for s in self._situacoes() if s != "NA")

    @property
    def documentos_em_aberto(self) -> list[str]:
        return [rotulo for campo, rotulo in DOCUMENTOS_PRO.items() if getattr(self, campo) in ("PENDENTE", "A_VALIDAR")]

    @property
    def status_documental(self) -> str:
        if self.qtd_aplicaveis == 0:
            return "Não aplicável"
        if self.qtd_ok == 0:
            return "Sem evidência"
        return "Completo" if self.qtd_ok == self.qtd_aplicaveis else "Incompleto"

    @property
    def aderencia(self) -> float | None:
        return round(self.qtd_ok / self.qtd_aplicaveis, 4) if self.qtd_aplicaveis else None

    @property
    def prazo_vencido(self) -> bool:
        return bool(self.prazo and self.prazo < date.today() and self.documentos_em_aberto)
