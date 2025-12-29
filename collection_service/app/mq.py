import json
import logging
import os

import pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")

EXCHANGE = "events"
EXCHANGE_TYPE = "topic"


def publish_event(routing_key: str, payload: dict) -> None:
    """Публикует событие в RabbitMQ.

    Важно: любые ошибки отправки не должны «ронять» HTTP-обработчик.
    Поэтому исключения здесь логируются, но наружу не пробрасываются.
    """
    connection = None
    try:
        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        channel.exchange_declare(exchange=EXCHANGE, exchange_type=EXCHANGE_TYPE, durable=True)

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key=routing_key,
            body=body,
            properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
        )

        logging.info("Published event %s", routing_key)
    except Exception:
        logging.exception("Failed to publish event %s", routing_key)
        # Не бросаем исключение дальше
    finally:
        # Гарантируем закрытие соединения, даже если что-то упало посередине.
        try:
            if connection and connection.is_open:
                connection.close()
        except Exception:
            logging.exception("Failed to close RabbitMQ connection")
