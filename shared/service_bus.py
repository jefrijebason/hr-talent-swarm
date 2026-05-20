from azure.servicebus import ServiceBusClient, ServiceBusMessage
from shared.config import config
import json

def publish_human_gate(queue: str, candidate_id: str, data: dict = {}):
    """
    Send a message to Service Bus.
    Only used for human gate boundaries.
    AI to AI communication happens directly.
    """
    payload = json.dumps({
        "candidate_id": candidate_id,
        "data": data
    })

    with ServiceBusClient.from_connection_string(
        config.SERVICE_BUS_CONNECTION
    ) as client:
        with client.get_queue_sender(queue) as sender:
            sender.send_messages(ServiceBusMessage(payload))

    print(f"[BUS] Message sent to queue: {queue}")

def receive_messages(queue: str, max_messages: int = 1) -> list:
    """
    Receive messages from a Service Bus queue.
    """
    messages = []

    with ServiceBusClient.from_connection_string(
        config.SERVICE_BUS_CONNECTION
    ) as client:
        with client.get_queue_receiver(
            queue, max_wait_time=5
        ) as receiver:
            for msg in receiver:
                data = json.loads(str(msg))
                messages.append(data)
                receiver.complete_message(msg)
                if len(messages) >= max_messages:
                    break

    return messages