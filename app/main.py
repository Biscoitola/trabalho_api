import logging
import os
from contextlib import asynccontextmanager

import pika
from fastapi import Depends, FastAPI, HTTPException, Response
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Campeonato
from app.rabbitmq import preparar_filas, publicar
from app.schemas import CampeonatoEntrada, CampeonatoSaida

logger = logging.getLogger("uvicorn.error")
INSTANCIA = os.getenv("INSTANCE_NAME", "api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # O lock evita que as duas APIs criem a mesma tabela simultaneamente.
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(20260920)"))
        Base.metadata.create_all(bind=connection)
    preparar_filas()
    yield
    engine.dispose()


app = FastAPI(title="API de Campeonatos", lifespan=lifespan)


@app.middleware("http")
async def identificar_instancia(request, call_next):
    response = await call_next(request)
    response.headers["X-Instancia"] = INSTANCIA
    logger.info("%s %s atendido por %s", request.method, request.url.path, INSTANCIA)
    return response


@app.get("/health", tags=["Infraestrutura"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "instancia": INSTANCIA}


def buscar_ou_404(db, campeonato_id):
    campeonato = db.get(Campeonato, campeonato_id)
    if campeonato is None:
        raise HTTPException(status_code=404, detail="Campeonato não encontrado")
    return campeonato


def enviar_evento(fila, campeonato, response):
    try:
        publicar(fila, CampeonatoSaida.model_validate(campeonato).model_dump(mode="json"))
    except (pika.exceptions.AMQPError, OSError):
        # O banco já confirmou a operação. Não informamos que o CRUD falhou.
        logger.exception("Operação salva, mas falhou a publicação em %s", fila)
        response.headers["X-Evento-Status"] = "falhou"
    else:
        response.headers["X-Evento-Status"] = "publicado"


@app.post("/campeonatos", response_model=CampeonatoSaida, status_code=201)
def criar(dados: CampeonatoEntrada, response: Response, db: Session = Depends(get_db)):
    campeonato = Campeonato(**dados.model_dump())
    db.add(campeonato)
    db.commit()
    db.refresh(campeonato)
    enviar_evento("campeonato_criado", campeonato, response)
    return campeonato


@app.get("/campeonatos", response_model=list[CampeonatoSaida])
def listar(db: Session = Depends(get_db)):
    return db.scalars(select(Campeonato).order_by(Campeonato.id)).all()


@app.get("/campeonatos/{id}", response_model=CampeonatoSaida)
def buscar(id: int, db: Session = Depends(get_db)):
    return buscar_ou_404(db, id)


@app.put("/campeonatos/{id}", response_model=CampeonatoSaida)
def atualizar(id: int, dados: CampeonatoEntrada, db: Session = Depends(get_db)):
    campeonato = buscar_ou_404(db, id)
    for campo, valor in dados.model_dump().items():
        setattr(campeonato, campo, valor)
    db.commit()
    db.refresh(campeonato)
    return campeonato


@app.delete("/campeonatos/{id}", status_code=204)
def excluir(id: int, db: Session = Depends(get_db)):
    campeonato = buscar_ou_404(db, id)
    db.delete(campeonato)
    db.commit()
    response = Response(status_code=204)
    enviar_evento("campeonato_excluido", campeonato, response)
    return response
