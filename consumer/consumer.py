import json
import os
import time

import pika


def receber(channel, method, properties, body):
    try:
        campeonato = json.loads(body)
        nome = campeonato["nome"]
    except (ValueError, KeyError, TypeError):
        print("Mensagem inválida descartada.", flush=True)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return
    if method.routing_key == "campeonato_criado":
        print(f"[NOVO CAMPEONATO]\nCampeonato criado: {nome}", flush=True)
    else:
        print(f"[CAMPEONATO EXCLUÍDO]\nCampeonato excluído: {nome}", flush=True)
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main():
    while True:
        try:
            with pika.BlockingConnection(
                pika.ConnectionParameters(
                    host="rabbitmq",
                    credentials=pika.PlainCredentials(
                        os.getenv("RABBITMQ_USER", "estudante"),
                        os.getenv("RABBITMQ_PASSWORD", "estudante123"),
                    ),
                    socket_timeout=5,
                    blocked_connection_timeout=5,
                )
            ) as connection:
                channel = connection.channel()
                channel.basic_qos(prefetch_count=1)
                for fila in ("campeonato_criado", "campeonato_excluido"):
                    channel.queue_declare(queue=fila, durable=True)
                    channel.basic_consume(queue=fila, on_message_callback=receber)
                print("Aguardando mensagens nas duas filas...", flush=True)
                channel.start_consuming()
        except (pika.exceptions.AMQPError, OSError) as erro:
            print(f"RabbitMQ indisponível: {erro}. Nova tentativa em 5s.", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
