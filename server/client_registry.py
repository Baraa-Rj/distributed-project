"""Thread-safe active-client registry for the Directory server."""

from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ClientRecord:
    name: str
    ip: str
    chat_port: int
    directory_socket: socket.socket
    last_seen: float
    write_lock: threading.Lock = field(default_factory=threading.Lock)


class ClientRegistry:
    def __init__(self, alive_timeout: float) -> None:
        self.alive_timeout = alive_timeout
        self.clients: Dict[str, ClientRecord] = {}
        self.lock = threading.Lock()

    def register_or_refresh(
        self,
        name: str,
        ip: str,
        chat_port: int,
        directory_socket: socket.socket,
    ) -> Tuple[bool, str, Optional[socket.socket]]:
        timestamp = time.time()
        stale_socket: Optional[socket.socket] = None

        with self.lock:
            existing = self.clients.get(name)
            if existing is not None and existing.directory_socket is directory_socket:
                existing.ip = ip
                existing.chat_port = chat_port
                existing.last_seen = timestamp
                return True, "", None

            if existing is not None:
                is_stale = timestamp - existing.last_seen > self.alive_timeout
                if not is_stale:
                    return False, "Username already active", None
                stale_socket = existing.directory_socket

            self.clients[name] = ClientRecord(
                name=name,
                ip=ip,
                chat_port=chat_port,
                directory_socket=directory_socket,
                last_seen=timestamp,
            )

        return True, "", stale_socket

    def remove_if_socket(self, name: str, expected_socket: socket.socket) -> Optional[ClientRecord]:
        with self.lock:
            existing = self.clients.get(name)
            if existing is None or existing.directory_socket is not expected_socket:
                return None
            return self.clients.pop(name)

    def remove_expired(self) -> List[ClientRecord]:
        timestamp = time.time()
        expired: List[ClientRecord] = []

        with self.lock:
            for name, record in list(self.clients.items()):
                if timestamp - record.last_seen > self.alive_timeout:
                    expired.append(record)
                    del self.clients[name]

        return expired

    def clear(self) -> List[ClientRecord]:
        with self.lock:
            records = list(self.clients.values())
            self.clients.clear()
            return records

    def active_names_and_records(self) -> Tuple[List[str], List[ClientRecord]]:
        with self.lock:
            return sorted(self.clients.keys()), list(self.clients.values())

    def get_sender_lock(self, name: str, sock: socket.socket) -> Optional[threading.Lock]:
        with self.lock:
            record = self.clients.get(name)
            if record is None or record.directory_socket is not sock:
                return None
            return record.write_lock

    def get_record_for_send(self, name: str) -> Optional[Tuple[socket.socket, threading.Lock]]:
        with self.lock:
            record = self.clients.get(name)
            if record is None:
                return None
            return record.directory_socket, record.write_lock

    def get_peer_lookup(
        self,
        requester: str,
        target: str,
    ) -> Tuple[Optional[Tuple[socket.socket, threading.Lock]], Optional[dict]]:
        timestamp = time.time()

        with self.lock:
            requester_record = self.clients.get(requester)
            target_record = self.clients.get(target)

            if requester_record is None:
                requester_send = None
            else:
                requester_send = requester_record.directory_socket, requester_record.write_lock

            if target_record is None or timestamp - target_record.last_seen > self.alive_timeout:
                peer_payload = None
            else:
                peer_payload = {
                    "target": target_record.name,
                    "ip": target_record.ip,
                    "chat_port": target_record.chat_port,
                }

        return requester_send, peer_payload
