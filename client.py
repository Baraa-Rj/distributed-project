#!/usr/bin/env python3
import json
import socket
import sys
import threading
import time

HEARTBEAT_INTERVAL = 1.0
MAX_FRAME = 64 * 1024  # cap an unterminated frame to bound memory use


def send_json(sock, lock, obj):
    data = (json.dumps(obj) + "\n").encode("utf-8")
    try:
        with lock:
            sock.sendall(data)
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
        if len(buf) > MAX_FRAME:
            # No delimiter within the cap: peer is misbehaving, drop it.
            return


class Client:
    def __init__(self, my_id, dir_host, dir_port):
        self.my_id = my_id
        self.dir_host = dir_host
        self.dir_port = dir_port

        self.dir_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dir_lock = threading.Lock()

        self.peer_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.peer_srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.peer_srv.bind(("0.0.0.0", 0))
        self.peer_srv.listen()
        self.peer_port = self.peer_srv.getsockname()[1]

        self.peers = {}
        self.peers_lock = threading.Lock()

        self.pending = set()
        self.active_peer = None
        self.last_list = []
        self.running = True

    def start(self):
        self.dir_sock.connect((self.dir_host, self.dir_port))
        print(f"[client] '{self.my_id}' control->{self.dir_host}:"
              f"{self.dir_port}  peer-listen port={self.peer_port}")

        threading.Thread(target=self._heartbeat, daemon=True).start()
        threading.Thread(target=self._dir_listener, daemon=True).start()
        threading.Thread(target=self._peer_acceptor, daemon=True).start()
        self._input_loop()

    def _heartbeat(self):
        while self.running:
            ok = send_json(self.dir_sock, self.dir_lock, {
                "type": "ALIVE",
                "src": self.my_id,
                "peer_port": self.peer_port,
            })
            if not ok:
                print("[client] lost Directory connection")
                self.running = False
                return
            time.sleep(HEARTBEAT_INTERVAL)

    def _dir_listener(self):
        for line in line_reader(self.dir_sock):
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            mtype = msg.get("type")

            if mtype == "LIST":
                self.last_list = msg.get("clients", [])

            elif mtype == "PEER_INFO":
                dst = msg.get("dst")
                ip = msg.get("ip")
                port = msg.get("port")
                self._connect_to_peer(dst, ip, port)

            elif mtype == "ERROR":
                print(f"\n[directory error] {msg.get('reason')}")
        self.running = False

    def _peer_acceptor(self):
        while self.running:
            try:
                sock, _ = self.peer_srv.accept()
            except OSError:
                return
            threading.Thread(target=self._handle_incoming_peer,
                             args=(sock,), daemon=True).start()

    def _handle_incoming_peer(self, sock):
        reader = line_reader(sock)
        peer_id = None
        for line in reader:
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "HELLO":
                peer_id = msg.get("src")
                break
        if not peer_id:
            sock.close()
            return
        _, is_new = self._register_peer(peer_id, sock)
        if not is_new:
            # Already connected to this peer (outbound race); drop this socket.
            sock.close()
            return
        print(f"\n[connected] '{peer_id}' connected to you")
        self._peer_reader(peer_id, sock, reader)

    def _register_peer(self, peer_id, sock):
        """Register sock for peer_id. Returns (entry, is_new); on collision the
        existing entry is returned and is_new is False so the caller can close
        its now-redundant socket."""
        with self.peers_lock:
            existing = self.peers.get(peer_id)
            if existing:
                return existing, False
            entry = {"sock": sock, "lock": threading.Lock()}
            self.peers[peer_id] = entry
            return entry, True

    def _connect_to_peer(self, peer_id, ip, port):
        with self.peers_lock:
            if peer_id in self.peers:
                if peer_id in self.pending:
                    self.active_peer = peer_id
                    self.pending.discard(peer_id)
                    print(f"\n[chat] focus set to '{peer_id}'")
                return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, port))
        except OSError as e:
            print(f"\n[client] could not reach '{peer_id}' ({ip}:{port}): {e}")
            self.pending.discard(peer_id)
            return
        entry, is_new = self._register_peer(peer_id, sock)
        if not is_new:
            # An inbound connection from this peer won the race while we were
            # connecting; close our redundant socket and don't start a reader.
            sock.close()
            if peer_id in self.pending:
                self.active_peer = peer_id
                self.pending.discard(peer_id)
            return
        send_json(sock, entry["lock"], {"type": "HELLO", "src": self.my_id})
        if peer_id in self.pending:
            self.active_peer = peer_id
            self.pending.discard(peer_id)
        print(f"\n[connected] now chatting with '{peer_id}'")
        threading.Thread(target=self._peer_reader,
                         args=(peer_id, sock, line_reader(sock)),
                         daemon=True).start()

    def _peer_reader(self, peer_id, sock, reader):
        for line in reader:
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "CHAT":
                print(f"\n[{peer_id}] {msg.get('text', '')}")
                sys.stdout.write("> ")
                sys.stdout.flush()
        with self.peers_lock:
            self.peers.pop(peer_id, None)
            if self.active_peer == peer_id:
                self.active_peer = None
        print(f"\n[disconnected] '{peer_id}' left the chat")

    def _send_chat(self, peer_id, text):
        with self.peers_lock:
            entry = self.peers.get(peer_id)
        if not entry:
            print(f"[client] not connected to '{peer_id}'. Use /chat {peer_id}")
            return
        send_json(entry["sock"], entry["lock"], {
            "type": "CHAT",
            "src": self.my_id,
            "ts": time.time(),
            "text": text,
        })

    def _input_loop(self):
        print("Commands: /list  /chat <id>  /msg <id> <text>  /peers  /quit")
        while self.running:
            try:
                line = input("> ")
            except (EOFError, KeyboardInterrupt):
                break
            line = line.strip()
            if not line:
                continue

            if line == "/quit":
                break
            elif line == "/list":
                print("Active clients:", ", ".join(self.last_list) or "(none)")
            elif line == "/peers":
                with self.peers_lock:
                    print("Connected peers:",
                          ", ".join(self.peers.keys()) or "(none)")
            elif line.startswith("/chat "):
                target = line.split(None, 1)[1].strip()
                if target == self.my_id:
                    print("[client] cannot chat with yourself")
                    continue
                self.pending.add(target)
                send_json(self.dir_sock, self.dir_lock,
                          {"type": "CONNECT_REQ", "src": self.my_id,
                           "dst": target})
            elif line.startswith("/msg "):
                parts = line.split(None, 2)
                if len(parts) < 3:
                    print("usage: /msg <id> <text>")
                    continue
                self._send_chat(parts[1], parts[2])
            else:
                if self.active_peer:
                    self._send_chat(self.active_peer, line)
                else:
                    print("[client] no active chat. Use /chat <id> first.")

        self.running = False
        try:
            self.dir_sock.close()
        except OSError:
            pass
        print("[client] bye")


def main():
    if len(sys.argv) < 2:
        print("usage: python3 client.py <my_id> [dir_host] [dir_port]")
        sys.exit(1)
    my_id = sys.argv[1]
    dir_host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    dir_port = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
    Client(my_id, dir_host, dir_port).start()


if __name__ == "__main__":
    main()