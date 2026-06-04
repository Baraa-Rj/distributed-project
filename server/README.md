# Server Work

This directory contains the Directory server side of the P2P chat project.

## Files

- `Directory.py`: small runnable entry point.
- `directory_server.py`: main TCP server, threads, client message handling, broadcasts, and cleanup loop.
- `client_registry.py`: thread-safe active-client table.
- `protocol.py`: JSON message creation, newline framing, socket send/receive helpers, and validation helpers.
- `config.py`: server port, timeout, interval, and buffer constants.

## Server Responsibilities

- Accept client connections.
- Handle `REGISTER`, `ALIVE`, and `GET_PEER` messages.
- Store each active client's name, IP address, chat port, and latest alive timestamp.
- Send `CLIENT_LIST` updates every one second.
- Remove inactive clients after about three seconds.
- Return `PEER_INFO` for active destination clients.
- Return `ERROR` for duplicate names, missing clients, or invalid requests.

## Run

From the project root:

```bash
python server/Directory.py
```

Optional custom host and port:

```bash
python server/Directory.py --host 0.0.0.0 --port 5000
```

## Protocol Boundary

The server does not forward chat messages. It only helps clients discover each other. Direct chat happens between clients after the Directory returns peer connection details.
