"""Short-term conversation memory in Redis (Phase D).

The CopilotKit/AG-UI chat already replays a thread's turns to the agent in-session.
This gives the REST /agent/ask endpoint the same short-term memory, server-side and
durable: the last few turns of a (user, thread) are kept in a Redis list with a TTL
and reloaded into the agent's message history on the next request.
"""
import json

import redis.asyncio as redis
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

MAX_TURNS = 12                  # keep the last N user/assistant turns
TTL_SECONDS = 60 * 60 * 24      # forget a conversation after a day of silence


def _key(user_id: str, thread_id: str) -> str:
    return f"conv:{user_id}:{thread_id}"


async def load_history(rds: redis.Redis, user_id: str, thread_id: str) -> list[ModelMessage]:
    """Rebuild the agent's message history from stored turns."""
    raw = await rds.lrange(_key(user_id, thread_id), 0, -1)
    history: list[ModelMessage] = []
    for item in raw:
        turn = json.loads(item)
        if turn["role"] == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=turn["content"])]))
        else:
            history.append(ModelResponse(parts=[TextPart(content=turn["content"])]))
    return history


async def save_turn(
    rds: redis.Redis, user_id: str, thread_id: str, user_text: str, answer_text: str
) -> None:
    """Append a user/assistant turn, trim to the last MAX_TURNS, refresh the TTL."""
    key = _key(user_id, thread_id)
    await rds.rpush(key, json.dumps({"role": "user", "content": user_text}))
    await rds.rpush(key, json.dumps({"role": "assistant", "content": answer_text}))
    await rds.ltrim(key, -2 * MAX_TURNS, -1)
    await rds.expire(key, TTL_SECONDS)
