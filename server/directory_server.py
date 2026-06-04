"""Main Directory server implementation."""

from __future__ import annotations

import socket
import threading
import time
from typing import Any, Dict, Optional, Tuple

try:
    from .client_registry import ClientRegistry
    from .config import ALIVE_TIMEOUT_SECONDS, CLIENT_LIST_INTERVAL_SECONDS, DEFAULT_HOST, DEFAULT_PORT
    from .protocol import MessageReader, close_socket, make_message, parse_chat_port, send_message
except ImportError:
    from client_registry import ClientRegistry
    from config import ALIVE_TIMEOUT_SECONDS, CLIENT_LIST_INTERVAL_SECONDS, DEFAULT_HOST, DEFAULT_PORT
    from protocol import MessageReader, close_socket, make_message, parse_chat_port, send_message


class DirectoryServer:
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        alive_timeout: float = ALIVE_TIMEOUT_SECONDS,
        list_interval: float = CLIENT_LIST_INTERVAL_SECONDS,
    ) -> None:
        self.host = host
        self.port = port
        self.alive_timeout = alive_timeout
        self.list_interval = list_interval
        self.registry = ClientRegistry(alive_timeout)
        self.running = threading.Event()
        self.running.set()
        self.server_socket: Optional[socket.socket] = None

    def start(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen()
        self.server_socket = server

        print(f"Directory server listening on {self.host}:{self.port}", flush=True)

        threading.Thread(target=self.broadcast_client_lists, daemon=True).start()
        threading.Thread(target=self.cleanup_inactive_clients, daemon=True).start()

        try:
            while self.running.is_set():
                try:
                    client_socket, address = server.accept()
                except OSError:
                    break

                threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address),
                    daemon=True,
                ).start()
        except KeyboardInterrupt:
            print("\nDirectory server shutting down.", flush=True)
        finally:
            self.stop()

    def stop(self) -> None:
        self.running.clear()
        if self.server_socket is not None:
            close_socket(self.server_socket)

        for record in self.registry.clear():
            close_socket(record.directory_socket)

    def handle_client(self, client_socket: socket.socket, address: Tuple[str, int]) -> None:
        reader = MessageReader(client_socket)
        registered_name: Optional[str] = None
        peer_address = f"{address[0]}:{address[1]}"
        print(f"Connection received from {peer_address}", flush=True)

        try:
            while self.running.is_set():
                try:
                    message = reader.receive()
                except OSError:
                    break

                if message is None:
                    break

                message_type = str(message.get("type", "")).upper()
                sender = str(message.get("sender", "")).strip()
                payload = message.get("payload", {})
                if not isinstance(payload, dict):
                    payload = {}

                if message_type == "INVALID_JSON":
                    self.send_error(client_socket, registered_name, "Invalid JSON message")
                    continue

                if not sender:
                    self.send_error(client_socket, registered_name, "Missing sender name")
                    continue

                if registered_name is not None and sender != registered_name:
                    self.send_error(
                        client_socket,
                        registered_name,
                        "Sender name cannot change after registration",
                    )
                    continue

                if message_type == "REGISTER":
                    success, error = self.register_or_refresh_client(sender, payload, client_socket, address)
                    if not success:
                        self.send_error(client_socket, registered_name, error, target=sender)
                        break

                    registered_name = sender
                    self.send_to_registered(
                        registered_name,
                        make_message(
                            "REGISTERED",
                            {"message": f"Registered as {registered_name}"},
                        ),
                    )
                    print(
                        f"Registered {registered_name} at {address[0]}:{payload.get('chat_port')}",
                        flush=True,
                    )

                elif message_type == "ALIVE":
                    success, error = self.register_or_refresh_client(sender, payload, client_socket, address)
                    if not success:
                        self.send_error(client_socket, registered_name, error, target=sender)
                        break
                    registered_name = sender

                elif message_type == "GET_PEER":
                    if registered_name is None:
                        self.send_error(client_socket, registered_name, "Register before requesting peers")
                        continue

                    target = str(payload.get("target", "")).strip()
                    self.handle_peer_lookup(registered_name, target)

                else:
                    self.send_error(
                        client_socket,
                        registered_name,
                        f"Unsupported message type: {message_type or 'UNKNOWN'}",
                    )

        finally:
            if registered_name is not None:
                self.remove_client(registered_name, client_socket)
                print(f"Removed {registered_name}", flush=True)
            close_socket(client_socket)

    def register_or_refresh_client(
        self,
        name: str,
        payload: Dict[str, Any],
        client_socket: socket.socket,
        address: Tuple[str, int],
    ) -> Tuple[bool, str]:
        chat_port, error = parse_chat_port(payload)
        if chat_port is None:
            return False, error

        success, error, stale_socket = self.registry.register_or_refresh(
            name=name,
            ip=address[0],
            chat_port=chat_port,
            directory_socket=client_socket,
        )

        if stale_socket is not None:
            close_socket(stale_socket)
        return success, error

    def handle_peer_lookup(self, requester: str, target: str) -> None:
        if not target:
            self.send_to_registered(
                requester,
                make_message(
                    "ERROR",
                    {
                        "message": "Missing target client",
                        "target": target,
                        "request": "GET_PEER",
                    },
                ),
            )
            return

        requester_send, peer_payload = self.registry.get_peer_lookup(requester, target)
        if requester_send is None:
            return

        requester_socket, requester_lock = requester_send
        if peer_payload is None:
            send_message(
                requester_socket,
                make_message(
                    "ERROR",
                    {
                        "message": "Client not found",
                        "target": target,
                        "request": "GET_PEER",
                    },
                ),
                requester_lock,
            )
            return

        send_message(requester_socket, make_message("PEER_INFO", peer_payload), requester_lock)

    def broadcast_client_lists(self) -> None:
        while self.running.is_set():
            time.sleep(self.list_interval)
            self.broadcast_client_list_once()

    def broadcast_client_list_once(self) -> None:
        client_names, records = self.registry.active_names_and_records()
        message = make_message("CLIENT_LIST", {"clients": client_names})
        failed_clients = []

        for record in records:
            try:
                send_message(record.directory_socket, message, record.write_lock)
            except OSError:
                failed_clients.append((record.name, record.directory_socket))

        for name, failed_socket in failed_clients:
            self.remove_client(name, failed_socket)

    def cleanup_inactive_clients(self) -> None:
        while self.running.is_set():
            time.sleep(0.5)
            expired = self.registry.remove_expired()

            for record in expired:
                print(f"Timed out {record.name}", flush=True)
                close_socket(record.directory_socket)

    def remove_client(self, name: str, expected_socket: socket.socket) -> None:
        record = self.registry.remove_if_socket(name, expected_socket)
        if record is not None:
            close_socket(record.directory_socket)

    def send_to_registered(self, name: str, message: Dict[str, Any]) -> None:
        record_send = self.registry.get_record_for_send(name)
        if record_send is None:
            return

        sock, write_lock = record_send
        send_message(sock, message, write_lock)

    def send_error(
        self,
        sock: socket.socket,
        registered_name: Optional[str],
        message: str,
        target: Optional[str] = None,
    ) -> None:
        payload: Dict[str, Any] = {"message": message}
        if target is not None:
            payload["target"] = target

        write_lock = None
        if registered_name is not None:
            write_lock = self.registry.get_sender_lock(registered_name, sock)

        try:
            send_message(sock, make_message("ERROR", payload), write_lock)
        except OSError:
            pass
