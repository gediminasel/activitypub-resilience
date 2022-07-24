import time
from datetime import datetime
from typing import Optional

from tools.activitypub.user import User


def create_note_activity(sender: User, content: str, reply_to: Optional[str] = None):
    title = str(int(time.time() * 1000))
    obj = {
        "id": f"{sender.uri()}/note/{title}",
        "type": "Note",
        "published": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "attributedTo": sender.uri(),
        "content": content,
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
    }
    if sender.followers() is not None:
        obj["cc"] = [sender.followers()]
    if reply_to is not None:
        obj["inReplyTo"] = reply_to

    return {
        "@context": ["https://www.w3.org/ns/activitystreams"],
        "id": f"{sender.uri()}/create_note/{title}",
        "type": "Create",
        "actor": sender.uri(),
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "object": obj,
    }
