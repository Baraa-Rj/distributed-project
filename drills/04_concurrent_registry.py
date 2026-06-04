"""
Drill #4 — Concurrency-safe registry

Goal: reader/writer contention between a broadcast thread and handler threads
over a shared registry (the directory-server core).

Build a registry: handlers add/remove/update entries; a separate broadcast (or
"list all") thread iterates the whole registry concurrently.

GIL caveat: relying on GIL atomicity is NOT a design. Use a plain dict guarded
by threading.Lock (Python's analogue to Java synchronized). Note where Java
would reach for ConcurrentHashMap and why CPython usually doesn't need it.

The trap: iterating a dict while another thread mutates it raises
"RuntimeError: dictionary changed size during iteration". Reproduce it, then fix
(snapshot under lock, or hold the lock across iteration — know the tradeoff:
lock-hold time vs. staleness).

Answer when you submit:
  1. Snapshot-then-iterate vs. iterate-under-lock: latency/consistency tradeoff?
  2. Where is the reader/writer contention, and does a plain Lock starve readers?
  3. What's the smallest critical section that's still correct?
"""
