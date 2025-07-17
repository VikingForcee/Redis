#!/usr/bin/env python3
"""
bench.py - benchmark custom Redis-like server

Measures latency + throughput across multiple threads issuing
mixed GET/SET/DEL commands over persistent TCP connections
using the server's binary protocol:

[4-byte total_len]
  [4-byte nstr]
  repeat nstr * ([4-byte strlen][bytes])

Responses ignored except to read complete frame; optional decode off for speed.
"""

import argparse
import socket
import struct
import threading
import time
import random
import statistics
from typing import List, Tuple

# ---- protocol encode helpers ------------------------------------------------

def pack_command(parts: List[str]) -> bytes:
    body = struct.pack("<I", len(parts))
    for p in parts:
        b = p.encode()
        body += struct.pack("<I", len(b)) + b
    return struct.pack("<I", len(body)) + body


def send_and_wait(sock: socket.socket, parts: List[str]) -> None:
    """Send one command; read and discard response payload."""
    pkt = pack_command(parts)
    sock.sendall(pkt)
    hdr = _recv_exact(sock, 4)
    (length,) = struct.unpack("<I", hdr)
    _ = _recv_exact(sock, length)  # discard payload for speed


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    data = bytearray()
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("socket closed during recv")
        data.extend(chunk)
    return bytes(data)


# ---- latency histogram ------------------------------------------------------

# Bucket edges in microseconds
# 0-100us,200us,500us,1ms,2ms,5ms,10ms,20ms,50ms,100ms,200ms,500ms,1s,>1s
BUCKET_EDGES_US = [
    100, 200, 500,
    1000, 2000, 5000,
    10000, 20000, 50000,
    100000, 200000, 500000,
    1000000,
]

def build_hist(lat_us: List[int]) -> List[int]:
    counts = [0]*(len(BUCKET_EDGES_US)+1)
    for v in lat_us:
        placed = False
        for i, edge in enumerate(BUCKET_EDGES_US):
            if v <= edge:
                counts[i] += 1
                placed = True
                break
        if not placed:
            counts[-1] += 1
    return counts

def format_hist(counts: List[int], total: int) -> str:
    lines = []
    prev = 0
    for i, edge in enumerate(BUCKET_EDGES_US):
        c = counts[i]
        pct = (c/total*100.0) if total else 0.0
        label = f"{prev/1000:.3f}ms - {edge/1000:.3f}ms"
        lines.append(f"{label:>22}: {c:>8}  {pct:6.2f}%")
        prev = edge
    # tail
    c = counts[-1]
    pct = (c/total*100.0) if total else 0.0
    label = f">{BUCKET_EDGES_US[-1]/1000:.3f}ms"
    lines.append(f"{label:>22}: {c:>8}  {pct:6.2f}%")
    return "\n".join(lines)


# ---- worker -----------------------------------------------------------------

class Worker(threading.Thread):
    def __init__(self, wid: int, host: str, port: int, n_ops: int,
                 keyspace: int, p_get: float, p_set: float, p_del: float,
                 value_len: int, record_latencies: bool):
        super().__init__()
        self.wid = wid
        self.host = host
        self.port = port
        self.n_ops = n_ops
        self.keyspace = keyspace
        self.p_get = p_get
        self.p_set = p_set
        self.p_del = p_del
        self.value_len = value_len
        self.record_latencies = record_latencies
        self.lat_us: List[int] = []
        self.errors = 0
        self.ops_done = 0

    def run(self):
        try:
            sock = socket.create_connection((self.host, self.port))
        except Exception as e:
            print(f"[worker {self.wid}] connect failed: {e}")
            self.errors = self.n_ops
            return

        rnd = random.Random(self.wid ^ int(time.time()*1e6))
        v_payload = "x"*self.value_len

        for _ in range(self.n_ops):
            op = self._pick_op(rnd.random())
            key = f"k{rnd.randrange(self.keyspace)}"

            if op == "get":
                parts = ["get", key]
            elif op == "set":
                parts = ["set", key, v_payload]
            else:  # del
                parts = ["del", key]

            t0 = time.perf_counter_ns()
            try:
                send_and_wait(sock, parts)
            except Exception:
                self.errors += 1
                break
            t1 = time.perf_counter_ns()

            if self.record_latencies:
                self.lat_us.append((t1 - t0)//1000)

            self.ops_done += 1

        sock.close()

    def _pick_op(self, r: float) -> str:
        if r < self.p_get:
            return "get"
        r -= self.p_get
        if r < self.p_set:
            return "set"
        return "del"


# ---- benchmark driver -------------------------------------------------------

def run_bench(host: str, port: int,
              total_ops: int, threads: int,
              keyspace: int,
              read_ratio: float, write_ratio: float, del_ratio: float,
              value_len: int,
              warmup_ops: int,
              lat_every: int) -> None:
    """
    lat_every:
      0 -> record all latencies
      N -> sample 1 op per N (approx) by controlling record flag per worker
    """
    # Normalize ratios
    total_ratio = read_ratio + write_ratio + del_ratio
    if total_ratio <= 0:
        raise ValueError("ratios must sum > 0")
    p_get = read_ratio / total_ratio
    p_set = write_ratio / total_ratio
    p_del = del_ratio / total_ratio

    # Warmup (optional)
    if warmup_ops > 0:
        _warmup(host, port, warmup_ops, keyspace, value_len)

    ops_per_thread = total_ops // threads
    leftover = total_ops % threads

    workers: List[Worker] = []
    for i in range(threads):
        n_ops = ops_per_thread + (1 if i < leftover else 0)
        # simple sampling: record latencies in all workers if lat_every ==0
        record_lat = (lat_every == 0) or (i % lat_every == 0)
        w = Worker(i, host, port, n_ops, keyspace,
                   p_get, p_set, p_del, value_len, record_lat)
        workers.append(w)

    start = time.perf_counter()
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    end = time.perf_counter()

    total_done = sum(w.ops_done for w in workers)
    total_errs = sum(w.errors for w in workers)
    dur = end - start
    tput = total_done / dur if dur > 0 else 0

    lat_samples = [lat for w in workers for lat in w.lat_us]
    _print_results(total_done, total_errs, dur, tput, lat_samples, workers)


def _warmup(host: str, port: int, warmup_ops: int, keyspace: int, value_len: int):
    """Do some SETs to populate DB, no timing."""
    print(f"[warmup] {warmup_ops} SET ops...")
    try:
        sock = socket.create_connection((host, port))
    except Exception as e:
        print(f"[warmup] connect failed: {e}")
        return
    v_payload = "x"*value_len
    rnd = random.Random(12345)
    for _ in range(warmup_ops):
        key = f"w{rnd.randrange(keyspace)}"
        try:
            send_and_wait(sock, ["set", key, v_payload])
        except Exception as e:
            print(f"[warmup] error: {e}")
            break
    sock.close()


def _print_results(total_done, total_errs, dur, tput, lat_samples, workers):
    print()
    print("===== Benchmark Results =====")
    print(f"Total ops attempted : {total_done + total_errs}")
    print(f"Total ops completed : {total_done}")
    print(f"Errors              : {total_errs}")
    print(f"Total time (s)      : {dur:.3f}")
    print(f"Throughput (ops/s)  : {tput:,.2f}")

    # per-thread (optional; uncomment if you want)
    # for w in workers:
    #     print(f"  thread {w.wid}: {w.ops_done} ops")

    if not lat_samples:
        print("\n(no latency samples recorded)")
        return

    lat_sorted = sorted(lat_samples)
    n = len(lat_sorted)

    avg = sum(lat_sorted)/n
    p50 = lat_sorted[int(n*0.50)]
    p95 = lat_sorted[int(n*0.95)]
    p99 = lat_sorted[int(n*0.99)]
    p999 = lat_sorted[int(n*0.999)] if n >= 1000 else lat_sorted[-1]
    mx = lat_sorted[-1]

    print("\nLatency (microseconds):")
    print(f"  avg   : {avg:,.1f} us  ({avg/1000:.3f} ms)")
    print(f"  p50   : {p50:,} us     ({p50/1000:.3f} ms)")
    print(f"  p95   : {p95:,} us     ({p95/1000:.3f} ms)")
    print(f"  p99   : {p99:,} us     ({p99/1000:.3f} ms)")
    print(f"  p99.9 : {p999:,} us    ({p999/1000:.3f} ms)")
    print(f"  max   : {mx:,} us      ({mx/1000:.3f} ms)")

    counts = build_hist(lat_sorted)
    print("\nLatency Histogram:")
    print(format_hist(counts, n))


# ---- arg parsing ------------------------------------------------------------

def parse_args():
    ap = argparse.ArgumentParser(
        description="Benchmark custom Redis-like server w/ latency histograms."
    )
    ap.add_argument("--host", default="127.0.0.1", help="Server host")
    ap.add_argument("--port", type=int, default=1234, help="Server port")

    ap.add_argument("--ops", type=int, default=100000, help="Total operations")
    ap.add_argument("--threads", type=int, default=10, help="Number of worker threads")
    ap.add_argument("--keyspace", type=int, default=10000, help="Number of distinct keys")

    ap.add_argument("--read-ratio", type=float, default=0.5, help="Fraction of reads (GET)")
    ap.add_argument("--write-ratio", type=float, default=0.4, help="Fraction of writes (SET)")
    ap.add_argument("--del-ratio", type=float, default=0.1, help="Fraction of deletes (DEL)")

    ap.add_argument("--value-len", type=int, default=16, help="Value length for SET")
    ap.add_argument("--warmup-ops", type=int, default=1000, help="Warmup SET ops before timed run")

    ap.add_argument(
        "--lat-every", type=int, default=0,
        help="Record latency in every Nth worker (0=all workers)."
    )

    return ap.parse_args()


# ---- main -------------------------------------------------------------------

def main():
    args = parse_args()
    run_bench(
        host=args.host,
        port=args.port,
        total_ops=args.ops,
        threads=args.threads,
        keyspace=args.keyspace,
        read_ratio=args.read_ratio,
        write_ratio=args.write_ratio,
        del_ratio=args.del_ratio,
        value_len=args.value_len,
        warmup_ops=args.warmup_ops,
        lat_every=args.lat_every,
    )

if __name__ == "__main__":
    main()
