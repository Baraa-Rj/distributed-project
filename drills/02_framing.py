"""
Drill #2 — Stream framing

Goal: internalize that TCP has NO message boundaries — it is a byte stream.
recv(n) may return FEWER than n bytes, AND may coalesce multiple sends.

Implement BOTH framing strategies and prove each handles partial/coalesced reads:
  (a) Newline-delimited: buffer bytes, split on b'\\n', keep the remainder.
  (b) Length-prefixed: fixed-size header carries the body length; read exactly
      that many bytes (loop recv until you have them all).

Write a "recv exactly N bytes" helper and a "recv one frame" reader for each.

Answer when you submit:
  1. Construct a case where ONE send becomes TWO recvs, and one where TWO sends
     become ONE recv. Show both in a test.
  2. For length-prefix: header size? byte order? what bounds the body length and
     why does an unbounded length field invite a DoS?
  3. For newline framing: what happens to bytes after the last \\n in a chunk?
"""
