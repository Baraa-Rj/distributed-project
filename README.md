# COMP438 Phase 1 — P2P Chat with Central Directory Server

Two-person project. This README is the **working agreement**: how we learn, how
we split the deliverable, and the protocol contract both halves must obey.

> Language: Python 3 (stdlib only). See `CLAUDE.md` for the tutor rules and the
> GIL caveats that affect the concurrency work.

---

## 1. Learning first — both partners do ALL drills

The 7 concept drills in `CLAUDE.md` are **not** split. Each of us implements
every one. Reason: the drills build specific muscles, and whoever skips a drill
is whoever writes the bug it was meant to prevent. The person who never did
Drill #4 (concurrent registry) is the one who ships the racy directory server.

| # | Drill | Person A done | Person B done |
|---|-------|:-------------:|:-------------:|
| 1 | Echo server | ☐ | ☐ |
| 2 | Stream framing (newline + length-prefix) | ☐ | ☐ |
| 3 | Thread-per-connection + deliberate race | ☐ | ☐ |
| 4 | Concurrency-safe registry | ☐ | ☐ |
| 5 | Heartbeat + soft-state TTL sweep | ☐ | ☐ |
| 6 | Bidirectional peer link | ☐ | ☐ |
| 7 | Graceful shutdown | ☐ | ☐ |

Only after both columns are checked do we start the deliverable.

---

## 2. Deliverable split

The natural seam in a directory-server + peer-client system:

- **Person A — Directory Server**
  - Accept registrations; maintain the live-peer registry.
  - Answer lookup/list queries.
  - Liveness: expire peers that stop sending heartbeats (soft state).
  - Concurrency: many clients at once; registry must be lock-correct.

- **Person B — Peer Client**
  - Register with the directory on startup; deregister/heartbeat over time.
  - Query the directory for other peers.
  - Open direct P2P chat links to peers (client *and* server simultaneously).
  - Per-peer reader threads; clean shutdown.

**Owner of each side fills in their name:**
- Person A = `__________`
- Person B = `__________`

### Integration risk (read this)
The classic two-person failure: each side is built against its author's private
assumptions about the wire format, both "work" alone, integration day explodes.
**Mitigation: Section 3 is authored jointly and frozen BEFORE either side is
coded.** Neither person changes it unilaterally.

---

## 3. Protocol contract — FILL THIS IN TOGETHER (do not skip)

This is the interface. Pull the actual requirements from the COMP438 Phase 1
assignment sheet — do not guess. Both partners sign off before coding.

### 3.1 Transport & framing
- Transport: TCP / UDP / both? (which for directory, which for P2P?) → `_____`
- Framing rule (pick one and justify — TCP has no message boundaries):
  - [ ] Newline-delimited
  - [ ] Length-prefixed (header bytes = `____`, byte order = `____`)
- Text encoding: `____________` (e.g. UTF-8)
- Max message size: `____________`

### 3.2 Message catalog
Fill one row per message. Be exact about field order and separators.

| Direction | Name | Wire format (exact) | Fields | Success reply | Error reply |
|-----------|------|---------------------|--------|---------------|-------------|
| client→dir |  |  |  |  |  |
| client→dir |  |  |  |  |  |
| dir→client |  |  |  |  |  |
| peer→peer  |  |  |  |  |  |
| _add rows_ |  |  |  |  |  |

### 3.3 Liveness / soft state
- Heartbeat interval: `____` s
- TTL before a peer is considered dead: `____` s
- What the directory does on expiry: `________________`

### 3.4 Error handling & edge cases
- Duplicate registration name: `________________`
- Lookup for unknown peer: `________________`
- Peer connects but never sends a valid message: `________________`
- Malformed frame: `________________`

### 3.5 Ports
- Directory server listen port: `____`
- Peer listen port assignment (fixed? OS-assigned? reported to directory?): `____`

---

## 4. Workflow

1. Both finish drills (Section 1).
2. Co-author and freeze the contract (Section 3).
3. Build independently against the frozen contract.
4. Integration test: A's server + B's client end-to-end.
5. Only change the contract by mutual agreement; re-test both sides after.

## 5. Run

```
# Directory server
python3 directory_server.py <port>

# Peer client
python3 peer_client.py <directory_host> <directory_port> <my_port>
```

(Adjust once Section 3.5 is settled.)
