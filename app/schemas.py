from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CampeonatoEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    nome: str = Field(min_length=1, max_length=120)
    jogo: str = Field(min_length=1, max_length=80)
    data: date
    premiacao: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    status: Literal["aberto", "em_andamento", "encerrado"]


class CampeonatoSaida(CampeonatoEntrada):
    model_config = ConfigDict(from_attributes=True)
    id: int
