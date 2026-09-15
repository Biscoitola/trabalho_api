import json
import os

import pika

FILAS = ("campeonato_criado", "campeonato_excluido")


def conectar():
    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host="rabbitmq",
            credentials=pika.PlainCredentials(
                os.getenv("RABBITMQ_USER", "estudante"),
                os.getenv("RABBITMQ_PASSWORD", "estudante123"),
            ),
            connection_attempts=3,
            retry_delay=1,
            socket_timeout=5,
            blocked_connection_timeout=5,
        )
    )


def preparar_filas():
    with conectar() as connection:
        channel = connection.channel()
        for fila in FILAS:
            channel.queue_declare(queue=fila, durable=True)


def publicar(fila, campeonato):
    with conectar() as connection:
        channel = connection.channel()
        channel.queue_declare(queue=fila, durable=True)
        channel.confirm_delivery()
        channel.basic_publish(
            exchange="",
            routing_key=fila,
            body=json.dumps(campeonato, ensure_ascii=False).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json", delivery_mode=2
            ),
            mandatory=True,
        )
