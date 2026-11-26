from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from . import models as m


class Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _opcao(valor: str, opcoes, campo: str, vazio_ok: bool = True) -> str:
    valor = (valor or "").strip()
    if valor == "" and vazio_ok:
        return ""
    if valor not in opcoes:
        raise ValueError(f"{campo}: opção inválida '{valor}'")
    return valor


class Ref(Base):
    id: int
    nome: str


# ---------------------------------------------------------------- auth / usuários

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: "UsuarioOut"


class UsuarioOut(Base):
    id: int
    email: str
    nome: str
    perfil: str
    ativo: bool
    coordenador_id: int | None = None
    coordenador: Ref | None = None
    ultimo_acesso: datetime | None = None


class UsuarioIn(BaseModel):
    email: EmailStr
    nome: str = Field(min_length=2, max_length=150)
    perfil: str
    ativo: bool = True
    coordenador_id: int | None = None
    senha: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("perfil")
    @classmethod
    def _perfil(cls, v):
        return _opcao(v, m.PERFIS, "perfil", vazio_ok=False)

    @field_validator("senha", mode="before")
    @classmethod
    def _senha_vazia(cls, v):
        return v or None

    @model_validator(mode="after")
    def _coord(self):
        if self.perfil == "coordenador" and not self.coordenador_id:
            raise ValueError("Escolha qual coordenador técnico este login representa")
        if self.perfil != "coordenador":
            self.coordenador_id = None
        return self


class TrocarSenhaIn(BaseModel):
    senha_atual: str
    senha_nova: str = Field(min_length=8, max_length=128)


# ---------------------------------------------------------------- cadastros

class CoordenadorIn(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    apelido: str = ""
    em_atividade: bool = True


class CoordenadorOut(Base):
    id: int
    nome: str
    apelido: str
    em_atividade: bool


class AtivoIn(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    numero: str = ""
    tipo_engenharia: str = ""
    uf: str = ""
    municipio: str = ""
    coordenador_id: int | None = None
    em_uso: bool = True

    @field_validator("tipo_engenharia")
    @classmethod
    def _tipo(cls, v):
        return _opcao(v, m.TIPOS_ENGENHARIA, "tipo de engenharia")

    @field_validator("uf")
    @classmethod
    def _uf(cls, v):
        return _opcao((v or "").upper(), m.UFS, "UF")


class AtivoOut(Base):
    id: int
    nome: str
    numero: str
    tipo_engenharia: str
    uf: str
    municipio: str
    coordenador_id: int | None
    coordenador: Ref | None = None
    em_uso: bool


class ContratadaIn(BaseModel):
    nome: str = Field(min_length=2, max_length=150)


class ContratadaOut(Base):
    id: int
    nome: str


class ColaboradorIn(BaseModel):
    nome: str = Field(min_length=3, max_length=150)
    cpf: str = ""
    matricula: str = ""
    funcao: str = ""
    tipo_engenharia: str = ""
    coordenador_id: int | None = None
    ativo_atual_id: int | None = None
    situacao: str = "MOBILIZADO"
    data_admissao: date | None = None
    data_demissao: date | None = None
    uf_origem: str = ""
    cidade_origem: str = ""
    telefone_corporativo: str = ""
    telefone_pessoal: str = ""
    email_corporativo: str = ""
    email_pessoal: str = ""
    veiculo: str = ""
    hospedagem: str = ""

    @field_validator("tipo_engenharia")
    @classmethod
    def _tipo(cls, v):
        return _opcao(v, m.TIPOS_ENGENHARIA, "tipo de engenharia")

    @field_validator("situacao")
    @classmethod
    def _situacao(cls, v):
        return _opcao(v, m.SITUACOES_COLABORADOR, "situação", vazio_ok=False)

    @field_validator("veiculo")
    @classmethod
    def _veiculo(cls, v):
        return _opcao(v, m.VEICULOS, "veículo")

    @field_validator("hospedagem")
    @classmethod
    def _hospedagem(cls, v):
        return _opcao(v, m.HOSPEDAGENS, "hospedagem")

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v):
        digitos = "".join(c for c in (v or "") if c.isdigit())
        if not digitos:
            return ""
        if len(digitos) != 11:
            raise ValueError("CPF deve ter 11 dígitos")
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"

    @model_validator(mode="after")
    def _datas(self):
        if self.data_admissao and self.data_demissao and self.data_demissao < self.data_admissao:
            raise ValueError("A data de demissão não pode ser anterior à admissão")
        return self


class ColaboradorOut(ColaboradorIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    coordenador: Ref | None = None
    ativo_atual: Ref | None = None
    pendencias_cadastro: list[str] = []
    atualizado_em: datetime | None = None


# ---------------------------------------------------------------- movimentações

class MovimentacaoIn(BaseModel):
    colaborador_id: int
    tipo: str
    ativo_id: int | None = None
    coordenador_id: int | None = None
    data_inicio: date
    data_fim: date | None = None
    observacoes: str = ""

    @field_validator("tipo")
    @classmethod
    def _tipo(cls, v):
        return _opcao(v, m.TIPOS_MOVIMENTACAO, "tipo", vazio_ok=False)

    @model_validator(mode="after")
    def _regras(self):
        if self.data_fim and self.data_fim < self.data_inicio:
            raise ValueError("A data fim não pode ser anterior à data início")
        if self.tipo in m.TIPOS_COM_DESTINO and not self.ativo_id:
            raise ValueError("Informe o ativo / obra de destino")
        if self.tipo in m.TIPOS_COM_PERIODO and not self.data_fim:
            raise ValueError("Informe até quando vai a folga / férias / afastamento (data fim)")
        return self


class MovimentacaoOut(Base):
    id: int
    colaborador_id: int
    colaborador: Ref
    tipo: str
    ativo_id: int | None
    ativo: Ref | None = None
    coordenador_id: int | None
    coordenador: Ref | None = None
    data_inicio: date
    data_fim: date | None
    observacoes: str
    criado_em: datetime | None = None
    criado_por_nome: str | None = None


# ---------------------------------------------------------------- fechamento

class FechamentoIn(BaseModel):
    ativo_id: int | None = None
    coordenador_id: int | None = None
    status: str
    inicio: date | None = None
    fim: date | None = None
    veiculo: str = ""
    hospedagem: str = ""
    dias_folga: int = Field(default=0, ge=0, le=31)
    dias_ferias: int = Field(default=0, ge=0, le=31)
    dias_afastado: int = Field(default=0, ge=0, le=31)
    observacao: str = ""

    @field_validator("status")
    @classmethod
    def _status(cls, v):
        return _opcao(v, m.STATUS_FECHAMENTO, "status", vazio_ok=False)

    @field_validator("veiculo")
    @classmethod
    def _veiculo(cls, v):
        return _opcao(v, m.VEICULOS, "veículo")

    @field_validator("hospedagem")
    @classmethod
    def _hospedagem(cls, v):
        return _opcao(v, m.HOSPEDAGENS, "hospedagem")

    @model_validator(mode="after")
    def _datas(self):
        if self.inicio and self.fim and self.fim < self.inicio:
            raise ValueError("A data fim não pode ser anterior ao início")
        return self


class FechamentoOut(FechamentoIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mes: date
    colaborador_id: int
    colaborador: Ref
    ativo: Ref | None = None
    coordenador: Ref | None = None
    uf: str = ""
    municipio: str = ""
    ativo_numero: str = ""


# ---------------------------------------------------------------- PRO

class RegistroPROIn(BaseModel):
    contratada_id: int
    ativo_id: int
    coordenador_id: int | None = None
    data: date
    atividade: str = Field(min_length=3)
    apr: str = "PENDENTE"
    pex: str = "PENDENTE"
    cr: str = "PENDENTE"
    lista_forum: str = "PENDENTE"
    lista_rpac: str = "PENDENTE"
    forum_aprovacao: str = "PENDENTE"
    observacao: str = ""
    responsavel_acao: str = ""
    proxima_acao: str = ""
    link_evidencia: str = ""
    prazo: date | None = None

    @field_validator("apr", "pex", "cr", "lista_forum", "lista_rpac", "forum_aprovacao")
    @classmethod
    def _doc(cls, v):
        return _opcao(v, m.SITUACOES_DOC, "situação do documento", vazio_ok=False)

    @field_validator("link_evidencia")
    @classmethod
    def _link(cls, v):
        v = (v or "").strip()
        if v and not v.lower().startswith(("http://", "https://")):
            raise ValueError("O link da evidência deve começar com http:// ou https://")
        return v


class RegistroPROOut(RegistroPROIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contratada: Ref
    ativo: Ref
    coordenador: Ref | None = None
    status_documental: str
    aderencia: float | None
    documentos_em_aberto: list[str]
    prazo_vencido: bool


Token.model_rebuild()
