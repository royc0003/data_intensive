from confluent_kafka import Producer
import json
import os

KAFKA_BROKERS = "3.129.102.184:9092,18.118.230.221:9093,3.130.6.49:9094"
TOPIC_NAME = "yourandrewid.customer.evt"

producer_conf = {
    'bootstrap.servers': KAFKA_BROKERS
}
producer = Producer(producer_conf)

def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

def send_customer_event(customer_data: dict):
    producer.produce(
        topic=TOPIC_NAME,
        value=json.dumps(customer_data),
        callback=delivery_report
    )
    producer.flush()
