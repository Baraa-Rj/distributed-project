"""
Drill #3 — Thread-per-connection + a deliberate race

Goal: one server, N concurrent clients via threading.Thread. Observe a
shared-state race ON PURPOSE, then fix it.

Structure: accept loop spawns one handler thread per connection. All handlers
touch one shared piece of state (e.g. a counter or a message log).

GIL caveat (see CLAUDE.md): a single `d[k] = v` is effectively atomic, so a
plain assignment will NOT tear. Build the race around a NON-ATOMIC
read-modify-write or check-then-act (e.g. `count += 1`, or "if k not in d: d[k]=...").

Step 1: write it racy, drive concurrent clients, demonstrate the wrong result.
Step 2: fix with threading.Lock; show it's now correct.

Answer when you submit:
  1. Which exact line is the race, and which bytecodes can the GIL switch between?
  2. What threads exist at steady state? Which are daemon, which join?
  3. Why does close-over-loop-variable bite if you pass the conn via a lambda?
"""
