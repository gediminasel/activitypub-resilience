import json
import traceback
from typing import List, TypedDict

from common.signatures import Verifier
from lookup import logger
from lookup.database.database import Database
from lookup.logging import event_counter


class SignatureDict(TypedDict):
    uri: str
    signature: str
    signature_time: int


async def add_signatures(
    verifier: Verifier,
    database: Database,
    signer: dict,
    signatures: List[SignatureDict],
) -> None:
    try:
        for signature in signatures:
            if not isinstance(signature, dict):
                continue
            actor = await database.objects.get_as_object(signature["uri"])
            if actor is None:
                continue
            actor_json = json.loads(actor["json"])
            actor_aux = json.loads(actor["aux"])
            if await verifier.verify(
                actor_json,
                actor_aux,
                signer["key_pem"],
                signature["signature"],
                signature["signature_time"],
            ):
                event_counter.on_event(event_counter.ACTOR_SIGNED)
                await database.signatures.insert(
                    signer["id"],
                    actor["num"],
                    signature["signature"],
                    signature["signature_time"],
                )
            else:
                event_counter.on_event(event_counter.ACTOR_SIGN_FAILED)
    except Exception as e:
        # something went very bad
        traceback.print_exc()
        logger.exception(e)
