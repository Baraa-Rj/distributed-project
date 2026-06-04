"""
Drill #5 — Heartbeat + soft state (TTL sweep)

Goal: soft-state registration. Entries are kept alive by periodic heartbeats and
EXPIRE if heartbeats stop. This is how SIP registrars, Eureka, and Consul track
liveness without a reliable "I'm leaving" message.

Build:
  - A registry where each entry has a last_seen timestamp.
  - A heartbeat path that refreshes last_seen.
  - A periodic sweeper (threading.Timer or a sched-driven loop in its own thread)
    that removes entries older than TTL.

Soft state = the truth decays unless refreshed. Contrast with hard state
(explicit add/remove that must be reliable).

Answer when you submit:
  1. TTL vs. heartbeat interval — what's a safe ratio and why (missed beats)?
  2. The sweeper mutates the registry while handlers read/write it — how do you
     make that safe? (ties back to Drill #4)
  3. threading.Timer spawns a new thread per fire — what's the failure mode if
     the callback is slow or raises?
  4. Why is soft state more robust to ungraceful peer death than hard state?
"""
