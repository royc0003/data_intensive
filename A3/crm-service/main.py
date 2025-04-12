import asyncio
from confluent_kafka import Consumer
import json
import os
from email.message import EmailMessage
import aiosmtplib
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

KAFKA_BROKERS = "3.129.102.184:9092,18.118.230.221:9093,3.130.6.49:9094"
TOPIC_NAME = "royceang.customer.evt"

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

consumer_conf = {
    'bootstrap.servers': KAFKA_BROKERS,
    'group.id': 'crm-consumer',
    'auto.offset.reset': 'earliest'
}
consumer = Consumer(consumer_conf)
consumer.subscribe([TOPIC_NAME])

async def send_email(data):
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = data["userId"]
    msg["Subject"] = "Activate your book store account"
    msg.set_content(f"""Dear {data['name']},

Welcome to the Book store created by yourandrewid.
Exceptionally this time we won’t ask you to click a link to activate your account.""")

    await aiosmtplib.send(msg, hostname=SMTP_HOST, port=SMTP_PORT, start_tls=True, username=SMTP_USER, password=SMTP_PASS)

async def consume_loop():
    while True:
        msg = consumer.poll(1.0)
        if msg is None or msg.error():
            await asyncio.sleep(1)
            continue
        try:
            logger.info(f"Processing message: {msg.value()}")
            data = json.loads(msg.value())
            logger.info(f"Sending email to: {data['userId']}")
            await send_email(data)
            consumer.commit(msg)
        except Exception as e:
            logger.error(f"Failed to process message: {e}")

if __name__ == "__main__":
    asyncio.run(consume_loop())
