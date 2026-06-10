#!/usr/bin/env python3
import json
import socket
import sys
import threading
import time

HOST = "0.0.0.0"
DEFAULT_PORT = 5000

ALIVE_TTL = 3.0
LIST_INTERVAL = 1.0
REAP_INTERVAL = 1.0

presence = {}
conns = {}
state_lock = threading.Lock()


def send_json(entry, obj):
    data = (json.dumps(obj) + "\n").encode("utf-8")
    try:
        with entry["lock"]:
            entry["sock"].sendall(data)
        return True
    except OSError:
        return False


def line_reader(sock):
    buf = b""
    while True:
        try:
            chunk = sock.recv(4096)
        except OSError:
            return
        if not chunk:
            return
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            if line.strip():
                yield line.decode("utf-8", errors="replace")


def handle_client(sock, addr):
    client_ip = addr[0]
    client_id = None
    entry = {"sock": sock, "lock": threading.Lock()}

    try:
        for line in line_reader(sock):
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            mtype = msg.get("type")

            if mtype == "ALIVE":
                cid = msg.get("src")
                peer_port = msg.get("peer_port")
                if not cid or not isinstance(peer_port, int):
                    continue
                first_time = False
                with state_lock:
                    if cid not in conns:
                        conns[cid] = entry
                        first_time = True
                    presence[cid] = {
                        "ip": client_ip,
                        "peer_port": peer_port,
                        "last_seen": time.time(),
                    }
                client_id = cid
                if first_time:
                    print(f"[directory] registered '{cid}' at "
                          f"{client_ip}:{peer_port}")

            elif mtype == "CONNECT_REQ":
                dst = msg.get("dst")
                with state_lock:
                    target = presence.get(dst)
                if target:
                    send_json(entry, {
                        "type": "PEER_INFO",
                        "dst": dst,
                        "ip": target["ip"],
                        "port": target["peer_port"],
                    })
                    print(f"[directory] {client_id} -> connect info for {dst}")
                else:
                    send_json(entry, {
                        "type": "ERROR",
                        "reason": f"unknown or inactive client '{dst}'",
                    })

    finally:
        if client_id:
            with state_lock:
                conns.pop(client_id, None)
                presence.pop(client_id, None)
            print(f"[directory] '{client_id}' disconnected")
        try:
            sock.close()
        except OSError:
            pass

def list_broadcaster():
    while True:
        time.sleep(LIST_INTERVAL)
        with state_lock:
            active = sorted(presence.keys())
            targets = list(conns.items())
        payload = {"type": "LIST", "clients": active}
        dead = [cid for cid, entry in targets if not send_json(entry, payload)]
        if dead:
            with state_lock:
                for cid in dead:
                    conns.pop(cid, None)
                    presence.pop(cid, None)


def reaper():
    while True:
        time.sleep(REAP_INTERVAL)
        now = time.time()
        with state_lock:
            stale = [cid for cid, p in presence.items()
                     if now - p["last_seen"] > ALIVE_TTL]
            for cid in stale:
                presence.pop(cid, None)
                conns.pop(cid, None)
        for cid in stale:
            print(f"[directory] reaped stale client '{cid}'")

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT

    threading.Thread(target=list_broadcaster, daemon=True).start()
    threading.Thread(target=reaper, daemon=True).start()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, port))
    srv.listen()
    print(f"[directory] listening on {HOST}:{port}")

    try:
        while True:
            sock, addr = srv.accept()
            threading.Thread(target=handle_client, args=(sock, addr),
                             daemon=True).start()
    except KeyboardInterrupt:
        print("\n[directory] shutting down")
    finally:
        srv.close()


if __name__ == "__main__":
    main()