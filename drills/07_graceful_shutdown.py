"""
Drill #7 — Graceful shutdown

Goal: cleanly stop a server whose threads are PARKED in blocking calls
(accept(), recv()) without leaking sockets / file descriptors.

A thread blocked in accept() will not notice a flag flip — it's asleep in the
kernel. You must do something that actually wakes it.

Implement and compare at least two techniques:
  - settimeout() + a shutdown Event the loop re-checks after each timeout.
  - close()/shutdown() the listening socket from another thread to force accept()
    to raise (OSError) — the abrupt unblock.
  - (Optional) a self-pipe / loopback "wakeup" connection.

Then join() all worker threads and confirm no sockets leak.

Answer when you submit:
  1. Why doesn't a bare `while not stop_flag: accept()` ever stop on its own?
  2. settimeout-poll vs. close-to-unblock: latency vs. cleanliness tradeoff?
  3. daemon=True threads die with the process — why is that NOT graceful, and
     what can leak (half-open connections, unflushed sends, OS resources)?
  4. What does closing the listening socket do to already-accepted connections?
"""
