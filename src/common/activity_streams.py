from typing import Optional


def get_as_id(as_obj: dict) -> Optional[str]:
    if "id" in as_obj:
        return str(as_obj["id"])
    if "uri" in as_obj:
        return str(as_obj["uri"])
    return None
