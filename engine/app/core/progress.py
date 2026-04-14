"""In-memory scan progress tracker.

Scan worker writes progress here; WebSocket endpoint reads it.
Uses asyncio.Queue per video so the WS endpoint can await new messages.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProgressState:
    pct: int = 0
    stage: str = "waiting"
    done: bool = False
    event_count: int = 0
    error: str | None = None
    # Each subscriber gets its own queue
    _queues: list[asyncio.Queue[dict[str, Any]]] = field(default_factory=list, repr=False)


_registry: dict[str, ProgressState] = {}


def get_or_create(video_id: str) -> ProgressState:
    if video_id not in _registry:
        _registry[video_id] = ProgressState()
    return _registry[video_id]


def update(video_id: str, pct: int, stage: str) -> None:
    state = get_or_create(video_id)
    state.pct = pct
    state.stage = stage
    msg = {"type": "progress", "pct": pct, "stage": stage}
    for q in state._queues:
        q.put_nowait(msg)


def complete(video_id: str, event_count: int) -> None:
    state = get_or_create(video_id)
    state.done = True
    state.pct = 100
    state.event_count = event_count
    msg = {"type": "done", "event_count": event_count}
    for q in state._queues:
        q.put_nowait(msg)


def fail(video_id: str, message: str) -> None:
    state = get_or_create(video_id)
    state.error = message
    msg = {"type": "error", "message": message}
    for q in state._queues:
        q.put_nowait(msg)


def subscribe(video_id: str) -> asyncio.Queue[dict[str, Any]]:
    state = get_or_create(video_id)
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    state._queues.append(q)
    # If already done/error, push terminal message immediately
    if state.done:
        q.put_nowait({"type": "done", "event_count": state.event_count})
    elif state.error:
        q.put_nowait({"type": "error", "message": state.error})
    elif state.pct > 0:
        q.put_nowait({"type": "progress", "pct": state.pct, "stage": state.stage})
    return q


def unsubscribe(video_id: str, q: asyncio.Queue[dict[str, Any]]) -> None:
    state = _registry.get(video_id)
    if state and q in state._queues:
        state._queues.remove(q)


def cleanup(video_id: str) -> None:
    _registry.pop(video_id, None)
