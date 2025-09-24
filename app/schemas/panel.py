from pydantic import BaseModel
from typing import Optional
from datetime import datetime, time, date


class FAQCreate(BaseModel):
    pergunta: str
    resposta: str
    categoria: Optional[str] = None
    palavras_chave: Optional[str] = None
    ativo: Optional[bool] = True


class FAQUpdate(BaseModel):
    pergunta: Optional[str] = None
    resposta: Optional[str] = None
    categoria: Optional[str] = None
    palavras_chave: Optional[str] = None
    ativo: Optional[bool] = None


class ProfissionalCreate(BaseModel):
    nome: str
    especialidade: Optional[str] = None
    crm: Optional[str] = None
    ativo: Optional[bool] = True


class ProfissionalUpdate(BaseModel):
    nome: Optional[str] = None
    especialidade: Optional[str] = None
    crm: Optional[str] = None
    ativo: Optional[bool] = None


class ServicoCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    valor: Optional[float] = None
    categoria: Optional[str] = None
    palavras_chave: Optional[str] = None
    observacoes: Optional[str] = None
    preparo_necessario: Optional[str] = None
    anestesia_tipo: Optional[str] = None
    local_realizacao: Optional[str] = None
    ativo: Optional[bool] = True


class ServicoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    valor: Optional[float] = None
    categoria: Optional[str] = None
    palavras_chave: Optional[str] = None
    observacoes: Optional[str] = None
    preparo_necessario: Optional[str] = None
    anestesia_tipo: Optional[str] = None
    local_realizacao: Optional[str] = None
    ativo: Optional[bool] = None


class HorarioCreate(BaseModel):
    profissional_id: Optional[int] = None
    dia_semana: str
    manha_inicio: Optional[time] = None
    manha_fim: Optional[time] = None
    tarde_inicio: Optional[time] = None
    tarde_fim: Optional[time] = None
    intervalo_minutos: Optional[int] = None
    ativo: Optional[bool] = True


class HorarioUpdate(BaseModel):
    profissional_id: Optional[int] = None
    dia_semana: Optional[str] = None
    manha_inicio: Optional[time] = None
    manha_fim: Optional[time] = None
    tarde_inicio: Optional[time] = None
    tarde_fim: Optional[time] = None
    intervalo_minutos: Optional[int] = None
    ativo: Optional[bool] = None


class ConvenioCreate(BaseModel):
    nome: str
    registro_ans: Optional[str] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = True


class ConvenioUpdate(BaseModel):
    nome: Optional[str] = None
    registro_ans: Optional[str] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None


class FormaPagamentoCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    max_parcelas: Optional[int] = 1
    ativo: Optional[bool] = True


class FormaPagamentoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    max_parcelas: Optional[int] = None
    ativo: Optional[bool] = None


class ParceiroCreate(BaseModel):
    nome: str
    tipo: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    ativo: Optional[bool] = True


class ParceiroUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    ativo: Optional[bool] = None


class ExcecaoAgendaCreate(BaseModel):
    data: date
    tipo: str
    descricao: Optional[str] = None
    ativo: Optional[bool] = True


class ExcecaoAgendaUpdate(BaseModel):
    data: Optional[date] = None
    tipo: Optional[str] = None
    descricao: Optional[str] = None
    ativo: Optional[bool] = None
