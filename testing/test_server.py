#!/usr/bin/env python3
import argparse
import socket
import struct
import sys
from typing import List, Tuple, Any, Optional

# ----------------------------
# Protocol encode/decode utils
# ----------------------------

TAG_NIL = 0
TAG_ERR = 1
TAG_STR = 2
TAG_INT = 3
TAG_DBL = 4
TAG_ARR = 5

def pack_command(parts: List[str]) -> bytes:
    """
    Build a request packet:
    [4-byte total_len]
      [4-byte nstr]
      repeat nstr * ([4-byte strlen] [bytes])
    Little-endian (matches struct.pack '<I' usage).
    """
    chunks = []
    chunks.append(struct.pack("<I", len(parts)))  # nstr
    for p in parts:
        b = p.encode("utf-8")
        chunks.append(struct.pack("<I", len(b)))
        chunks.append(b)
    body = b"".join(chunks)
    packet = struct.pack("<I", len(body)) + body
    return packet


def _need(buf: bytes, off: int, n: int) -> None:
    if off + n > len(buf):
        raise ValueError("response truncated")


def decode_value(buf: bytes, off: int = 0) -> Tuple[Any, int]:
    """
    Decode one value starting at buf[off].
    Returns (value, new_offset).
    """
    _need(buf, off, 1)
    tag = buf[off]
    off += 1

    if tag == TAG_NIL:
        return None, off

    if tag == TAG_ERR:
        _need(buf, off, 4)
        code = struct.unpack_from("<I", buf, off)[0]
        off += 4
        _need(buf, off, 4)
        mlen = struct.unpack_from("<I", buf, off)[0]
        off += 4
        _need(buf, off, mlen)
        msg = buf[off:off+mlen].decode("utf-8", errors="replace")
        off += mlen
        return RuntimeError(f"[{code}] {msg}"), off

    if tag == TAG_STR:
        _need(buf, off, 4)
        slen = struct.unpack_from("<I", buf, off)[0]
        off += 4
        _need(buf, off, slen)
        s = buf[off:off+slen].decode("utf-8", errors="replace")
        off += slen
        return s, off

    if tag == TAG_INT:
        _need(buf, off, 8)
        val = struct.unpack_from("<q", buf, off)[0]
        off += 8
        return val, off

    if tag == TAG_DBL:
        _need(buf, off, 8)
        val = struct.unpack_from("<d", buf, off)[0]
        off += 8
        return val, off

    if tag == TAG_ARR:
        _need(buf, off, 4)
        count = struct.unpack_from("<I", buf, off)[0]
        off += 4
        arr = []
        for _ in range(count):
            v, off = decode_value(buf, off)
            arr.append(v)
        return arr, off

    raise ValueError(f"Unknown tag: {tag}")


def decode_response(payload: bytes) -> Any:
    """
    Decode entire response payload (after 4-byte length prefix).
    Returns Python object.
    """
    val, off = decode_value(payload, 0)
    if off != len(payload):
        # server may pipeline multiple top-level values, but we expect 1
        extra = len(payload) - off
        return (val, f"[warning: {extra} extra bytes]")
    return val


# ----------------------------
# Socket helpers
# ----------------------------

def recv_exact(sock: socket.socket, n: int) -> bytes:
    """Receive exactly n bytes or raise."""
    data = bytearray()
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("socket closed during recv")
        data.extend(chunk)
    return bytes(data)


def send_cmd_and_recv(sock: socket.socket, parts: List[str], debug=False) -> Any:
    pkt = pack_command(parts)
    if debug:
        print(f"> raw ({len(pkt)} bytes): {pkt!r}")
    sock.sendall(pkt)

    # read 4-byte length prefix
    hdr = recv_exact(sock, 4)
    (length,) = struct.unpack("<I", hdr)
    payload = recv_exact(sock, length)
    if debug:
        print(f"< raw ({len(payload)} bytes payload): {payload!r}")

    return decode_response(payload)


# ----------------------------
# Friendly print
# ----------------------------

def format_resp(resp: Any) -> str:
    if isinstance(resp, RuntimeError):
        return f"ERR {resp}"
    if resp is None:
        return "(nil)"
    if isinstance(resp, list):
        if not resp:
            return "(empty array)"
        lines = []
        for i, v in enumerate(resp, 1):
            lines.append(f"{i}) {format_resp(v)}")
        return "\n".join(lines)
    return str(resp)


# ----------------------------
# Interactive REPL
# ----------------------------

def repl(sock: socket.socket, debug=False):
    print("Connected. Type commands like:")
    print("  set mykey hello")
    print("  get mykey")
    print("  del mykey")
    print("  keys")
    print("  pexpire mykey 5000")
    print("  pttl mykey")
    print("  zadd myz 42 member1")
    print("Ctrl+C or empty line to quit.\n")

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            break

        # naive split on whitespace; no quoting handling
        parts = line.split()
        try:
            resp = send_cmd_and_recv(sock, parts, debug=debug)
            print(format_resp(resp))
        except Exception as e:
            print(f"(error) {e}")


# ----------------------------
# Main
# ----------------------------

def main():
    ap = argparse.ArgumentParser(description="Test client for custom Redis-like server.")
    ap.add_argument("command", nargs="*", help="Command + args (if omitted, enter interactive mode).")
    ap.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    ap.add_argument("--port", type=int, default=1234, help="Server port (default: 1234)")
    ap.add_argument("--debug", action="store_true", help="Show raw protocol bytes")
    args = ap.parse_args()

    try:
        sock = socket.create_connection((args.host, args.port))
    except Exception as e:
        print(f"Could not connect to {args.host}:{args.port}: {e}")
        return 1

    if args.command:
        # one-shot
        try:
            resp = send_cmd_and_recv(sock, args.command, debug=args.debug)
            print(format_resp(resp))
        except Exception as e:
            print(f"(error) {e}")
        finally:
            sock.close()
        return 0

    # interactive
    try:
        repl(sock, debug=args.debug)
    finally:
        sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
