"""
Drill #6 — Bidirectional peer link  (THE core of your Peer Client deliverable)

Goal: one node that is simultaneously a SERVER (accepts inbound peer links) and a
CLIENT (dials outbound to peers). Per-peer reader thread; sending happens from
the main/other threads.

Build a node that:
  - Runs an accept loop in its own thread (inbound connections).
  - Can dial out to another node's (host, port).
  - For every established link (inbound or outbound), spawns a reader thread that
    blocks on recv and prints/handles incoming frames.
  - Lets you type a line and send it to a connected peer.

Run two instances; have them talk both directions over the SAME link.

Answer when you submit:
  1. Enumerate every thread in one running node and what each blocks on.
  2. One TCP connection is full-duplex — do you need two sockets between two
     peers, or one? Justify.
  3. Who owns sending on a socket? Can two threads sendall() on the same socket
     concurrently — what breaks (interleaving / framing)?
  4. If A dials B and B also dials A, you get two links. How do you dedupe?
"""
