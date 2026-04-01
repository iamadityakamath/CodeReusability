import os

from google.cloud import pubsub_v1


def publisher_client() -> pubsub_v1.PublisherClient:
    return pubsub_v1.PublisherClient()


def subscriber_client() -> pubsub_v1.SubscriberClient:
    return pubsub_v1.SubscriberClient()


def publish_message(topic_id: str, message: str, project_id: str | None = None) -> str:
    project = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT is required")
    client = publisher_client()
    topic_path = client.topic_path(project, topic_id)
    future = client.publish(topic_path, message.encode("utf-8"))
    return future.result()


def pull_one(subscription_id: str, project_id: str | None = None) -> list[str]:
    project = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT is required")
    client = subscriber_client()
    sub_path = client.subscription_path(project, subscription_id)
    response = client.pull(request={"subscription": sub_path, "max_messages": 1})
    messages: list[str] = []
    ack_ids: list[str] = []
    for received in response.received_messages:
        messages.append(received.message.data.decode("utf-8"))
        ack_ids.append(received.ack_id)
    if ack_ids:
        client.acknowledge(request={"subscription": sub_path, "ack_ids": ack_ids})
    return messages
