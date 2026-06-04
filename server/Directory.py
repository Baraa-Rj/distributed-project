#!/usr/bin/env python3
"""
Entry point for the Directory server.

Run from the project root:
    python server/Directory.py
"""

from __future__ import annotations

import argparse

try:
    from .config import DEFAULT_HOST, DEFAULT_PORT
    from .directory_server import DirectoryServer
except ImportError:
    from config import DEFAULT_HOST, DEFAULT_PORT
    from directory_server import DirectoryServer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Directory server for the P2P chat application.")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host/IP to bind. Default: {DEFAULT_HOST}")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"TCP port to bind. Default: {DEFAULT_PORT}")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = DirectoryServer(host=args.host, port=args.port)
    server.start()


if __name__ == "__main__":
    main()
