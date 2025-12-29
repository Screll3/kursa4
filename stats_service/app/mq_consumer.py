import json
import logging
import os
import time

import pika

from .db import SessionLocal
from .models import EventLog

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")
EXCHANGE = "events"
QUEUE = "stats_events"
BIND_KEY = "collection.*"


def _handle_message(ch, method, properties, body: bytes):
    """Callback для pika: сохраняет событие в таблицу event_logs и ack'ает сообщение."""
    try:
        data = json.loads(body.decode("utf-8"))
        event_type = method.routing_key

        raw_uid = data.get("user_id")
        if raw_uid is None:
            raise ValueError("Missing user_id in event")

        user_id = int(raw_uid)
        if user_id <= 0:
            raise ValueError("Invalid user_id in event")

        db = SessionLocal()
        try:
            db.add(
                EventLog(
                    event_type=event_type,
                    user_id=user_id,
                    payload_json=json.dumps(data, ensure_ascii=False),
                )
            )
            db.commit()
        finally:
            db.close()

        logging.info("Consumed %s", event_type)
    except Exception:
        logging.exception("Failed to process message")
    finally:
        # Ack в любом случае, чтобы очередь не «залипла» на плохом сообщении.
        ch.basic_ack(delivery_tag=method.delivery_tag)


def run_consumer_forever():
    """Бесконечно читает события из RabbitMQ и пишет их в БД.

    При падении соединения/канала — делает паузу и переподключается.
    """
    while True:
        conn = None
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            conn = pika.BlockingConnection(params)
            ch = conn.channel()

            ch.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
            ch.queue_declare(queue=QUEUE, durable=True)
            ch.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=BIND_KEY)

            ch.basic_qos(prefetch_count=10)
            ch.basic_consume(queue=QUEUE, on_message_callback=_handle_message)

            logging.info("Stats consumer started. Waiting for messages...")
            ch.start_consuming()
        except Exception:
            logging.exception("Consumer crashed, retry in 3s...")
            time.sleep(3)
        finally:
            # Важно закрывать соединение, иначе при множественных рестартах будут утечки.
            try:
                if conn and conn.is_open:
                    conn.close()
            except Exception:
                logging.exception("Failed to close RabbitMQ connection")
