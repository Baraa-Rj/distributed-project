"""Application-layer protocol helpers for newline-delimited JSON over TCP."""

from __future__ import annotations

import json
import socket
import threading
import time
from typing import Any, Dict, Optional, Tuple

try:
    from .config import BUFFER_SIZE, DIRECTORY_SENDER
except ImportError:
    from config import BUFFER_SIZE, DIRECTORY_SENDER


def make_message(message_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "type": message_type,
        "sender": DIRECTORY_SENDER,
        "timestamp": time.time(),
        "payload": payload or {},
    }


def send_message(
    sock: socket.socket,
    message: Dict[str, Any],
    write_lock: Optional[threading.Lock] = None,
) -> None:
    data = (json.dumps(message, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")
    if write_lock is None:
        sock.sendall(data)
        return

    with write_lock:
        sock.sendall(data)


class MessageReader:
    """Reads newline-delimited JSON messages from a TCP stream."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buffer = b""

    def receive(self) -> Optional[Dict[str, Any]]:
        while True:
            while b"\n" not in self.buffer:
                chunk = self.sock.recv(BUFFER_SIZE)
                if not chunk:
                    return None
                self.buffer += chunk

            line, self.buffer = self.buffer.split(b"\n", 1)
            line = line.strip()
            if not line:
                continue

            try:
                message = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {"type": "INVALID_JSON", "sender": "", "payload": {}}

            if not isinstance(message, dict):
                return {"type": "INVALID_JSON", "sender": "", "payload": {}}
            return message


def parse_chat_port(payload: Dict[str, Any]) -> Tuple[Optional[int], str]:
    raw_port = payload.get("chat_port")
    try:
        chat_port = int(raw_port)
    except (TypeError, ValueError):
        return None, "chat_port must be an integer"

    if chat_port < 1 or chat_port > 65535:
        return None, "chat_port must be between 1 and 65535"
    return chat_port, ""


def close_socket(sock: socket.socket) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass
