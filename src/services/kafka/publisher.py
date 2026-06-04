import json
from typing import Any


def open_kafka_producer(bootstrap_servers: str):
    try:
        from kafka import KafkaProducer
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "kafka-python is required to publish flight generator payloads. "
            "Install it with `pip install kafka-python`."
        ) from error

    return KafkaProducer(
        bootstrap_servers=bootstrap_servers.split(","),
        value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
    )


def publish_messages(
    producer: Any,
    topic: str,
    messages: dict[str, object] | list[dict[str, object]],
) -> list[dict[str, object]]:
    payloads = messages if isinstance(messages, list) else [messages]

    for payload in payloads:
        producer.send(topic, payload)

    producer.flush()
    return payloads


def close_kafka_producer(producer: Any) -> None:
    producer.close()
