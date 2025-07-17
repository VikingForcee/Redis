#!/usr/bin/env python3
import argparse
import time
import random
import socket
import threading
import statistics
import json
import csv
import struct
import sys
from typing import List

# -----------------------------
# Optional Matplotlib import
# -----------------------------
try:
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except ImportError:
    HAVE_MPL = False


# ============================================================
# Protocol helpers (your server's binary format)
# ============================================================

def build_packet(parts: List[str]) -> bytes:
    """
    Encode a command for your server:
      [4-byte total_len]
        [4-byte nstr]
        repeat: [4-byte strlen][bytes]
    Little-endian (<).
    """
    body = struct.pack("<I", len(parts))
    for p in parts:
        b = p.encode()
        body += struct.pack("<I", len(b)) + b
    return struct.pack("<I", len(body)) + body


def recv_exact(sock: socket.socket, n: int) -> bytes:
    """Read exactly n bytes."""
    data = bytearray()
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("socket closed during recv_exact")
        data.extend(chunk)
    return bytes(data)


def send_cmd(sock: socket.socket, *parts: str) -> None:
    """Send one command; read & discard server response."""
    pkt = build_packet(list(parts))
    sock.sendall(pkt)
    hdr = recv_exact(sock, 4)
    (plen,) = struct.unpack("<I", hdr)
    _ = recv_exact(sock, plen)  # discard payload


# ============================================================
# Warm-up
# ============================================================

def warmup(host: str, port: int, n: int = 1000, value: str = "hello") -> None:
    """Populate server so benchmark doesn't start cold."""
    print(f"[warmup] {n} SET ops...")
    try:
        s = socket.create_connection((host, port), timeout=5)
    except Exception as e:
        print(f"[warmup] connect failed ({host}:{port}): {e}")
        return
    try:
        for i in range(n):
            send_cmd(s, "set", f"warm{i}", value)
    finally:
        s.close()


# ============================================================
# Worker thread
# ============================================================

class Worker(threading.Thread):
    def __init__(self, wid: int, host: str, port: int, n_ops: int,
                 keyspace: int, p_get: float, p_set: float, p_del: float,
                 value_len: int, latencies: List[float], lock: threading.Lock,
                 errors_ref: List[int]):
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
        self.latencies = latencies
        self.lock = lock
        self.errors_ref = errors_ref  # single-element list used as mutable int

    def run(self):
        try:
            s = socket.create_connection((self.host, self.port))
        except Exception as e:
            with self.lock:
                self.errors_ref[0] += self.n_ops
            print(f"[worker {self.wid}] connect failed: {e}")
            return

        rnd = random.Random(self.wid ^ int(time.time() * 1e6))
        value = "x" * self.value_len

        for _ in range(self.n_ops):
            r = rnd.random()
            if r < self.p_get:
                parts = ("get", f"k{rnd.randrange(self.keyspace)}")
            else:
                r -= self.p_get
                if r < self.p_set:
                    parts = ("set", f"k{rnd.randrange(self.keyspace)}", value)
                else:
                    parts = ("del", f"k{rnd.randrange(self.keyspace)}")

            t0 = time.perf_counter_ns()
            try:
                send_cmd(s, *parts)
            except Exception:
                with self.lock:
                    self.errors_ref[0] += 1
                break
            t1 = time.perf_counter_ns()

            lat_us = (t1 - t0) // 1000
            with self.lock:
                self.latencies.append(lat_us)

        s.close()


# ============================================================
# Results / stats helpers
# ============================================================

def pct_lat(lat_sorted: List[float], pct: float) -> float:
    if not lat_sorted:
        return 0.0
    idx = min(int(len(lat_sorted) * pct), len(lat_sorted) - 1)
    return lat_sorted[idx]


def write_csv(path: str, lat_sorted: List[float]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["op", "latency_us"])
        for i, v in enumerate(lat_sorted, 1):
            w.writerow([i, f"{v:.2f}"])
    print(f"✅ Latency data exported to {path}")


def write_json(path: str, summary: dict) -> None:
    with open(path, "w") as f:
        json.dump(summary, f, indent=4)
    print(f"✅ Summary exported to {path}")


def plot_latency(lat_sorted: List[float]) -> None:
    if not HAVE_MPL:
        print("⚠ Matplotlib not installed; skipping plots.")
        return

    # convert to ms
    lat_ms = [v / 1000.0 for v in lat_sorted]

    # Histogram (log x for tail clarity)
    import matplotlib.ticker as mtick
    plt.figure(figsize=(10, 5))
    plt.hist(lat_ms, bins=60, alpha=0.7)
    plt.xscale("log")
    plt.title("Latency Histogram (log scale)")
    plt.xlabel("Latency (ms, log scale)")
    plt.ylabel("Count")
    plt.grid(True, which="both", ls=":")
    plt.savefig("latency_hist.png")
    plt.close()

    # CDF
    n = len(lat_ms)
    cdf_y = [i / n for i in range(n)]
    plt.figure(figsize=(10, 5))
    plt.plot(lat_ms, cdf_y, linewidth=1.5)
    plt.xscale("log")
    plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    plt.title("Latency CDF")
    plt.xlabel("Latency (ms, log scale)")
    plt.ylabel("Percentile")
    plt.grid(True, which="both", ls=":")
    plt.savefig("latency_cdf.png")
    plt.close()

    print("✅ Plots saved: latency_hist.png, latency_cdf.png")


# ============================================================
# Main benchmark driver
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Benchmark custom Redis-like server.")
    parser.add_argument("--ops", type=int, default=100000, help="Total operations.")
    parser.add_argument("--threads", type=int, default=10, help="Worker threads.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host.")
    parser.add_argument("--port", type=int, default=1234, help="Server port (default 1234).")
    parser.add_argument("--value-len", type=int, default=16, help="Value length for SET.")
    parser.add_argument("--keyspace", type=int, default=10000, help="Distinct keys.")
    parser.add_argument("--read-ratio", type=float, default=0.5, help="GET percentage.")
    parser.add_argument("--write-ratio", type=float, default=0.4, help="SET percentage.")
    parser.add_argument("--del-ratio", type=float, default=0.1, help="DEL percentage.")
    parser.add_argument("--no-warmup", action="store_true", help="Skip warm-up phase.")
    parser.add_argument("--warmup-ops", type=int, default=1000, help="# warm-up SET ops.")
    parser.add_argument("--export", type=str, help="Export per-op latencies to CSV.")
    parser.add_argument("--export-json", type=str, help="Export summary stats to JSON.")
    parser.add_argument("--plot", action="store_true", help="Generate latency plots.")
    args = parser.parse_args()

    # Validate ratios
    total_ratio = args.read_ratio + args.write_ratio + args.del_ratio
    if total_ratio <= 0:
        print("ERROR: ratios must sum > 0")
        return 1
    p_get = args.read_ratio / total_ratio
    p_set = args.write_ratio / total_ratio
    p_del = args.del_ratio / total_ratio

    # Warm-up
    if not args.no_warmup:
        warmup(args.host, args.port, n=args.warmup_ops, value="warmval")

    # Work distribution
    ops_per_thread = args.ops // args.threads
    leftover = args.ops % args.threads

    latencies: List[float] = []
    lock = threading.Lock()
    errors_ref = [0]  # boxed int

    workers = []
    for i in range(args.threads):
        n_ops = ops_per_thread + (1 if i < leftover else 0)
        w = Worker(
            wid=i,
            host=args.host,
            port=args.port,
            n_ops=n_ops,
            keyspace=args.keyspace,
            p_get=p_get,
            p_set=p_set,
            p_del=p_del,
            value_len=args.value_len,
            latencies=latencies,
            lock=lock,
            errors_ref=errors_ref,
        )
        workers.append(w)

    # Run benchmark
    print("\n===== Benchmark Running =====")
    t0 = time.perf_counter()
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    t1 = time.perf_counter()

    dur = t1 - t0
    total_done = len(latencies)
    total_errs = errors_ref[0]
    tput = total_done / dur if dur > 0 else 0.0

    # Stats
    if total_done == 0:
        print("No successful operations recorded.")
        return 1

    lat_sorted = sorted(latencies)
    avg = statistics.mean(lat_sorted)
    p50 = pct_lat(lat_sorted, 0.50)
    p95 = pct_lat(lat_sorted, 0.95)
    p99 = pct_lat(lat_sorted, 0.99)
    p999 = pct_lat(lat_sorted, 0.999)
    max_lat = lat_sorted[-1]

    print("\n===== Benchmark Results =====")
    print(f"Total ops attempted : {args.ops}")
    print(f"Total ops completed : {total_done}")
    print(f"Errors              : {total_errs}")
    print(f"Total time (s)      : {dur:.3f}")
    print(f"Throughput (ops/s)  : {tput:,.2f}")
    print("\nLatency (microseconds):")
    print(f"  avg   : {avg:.1f} us  ({avg/1000:.3f} ms)")
    print(f"  p50   : {p50:.0f} us     ({p50/1000:.3f} ms)")
    print(f"  p95   : {p95:.0f} us     ({p95/1000:.3f} ms)")
    print(f"  p99   : {p99:.0f} us     ({p99/1000:.3f} ms)")
    print(f"  p99.9 : {p999:.0f} us    ({p999/1000:.3f} ms)")
    print(f"  max   : {max_lat:.0f} us      ({max_lat/1000:.3f} ms)")

    # Export
    if args.export:
        write_csv(args.export, lat_sorted)

    if args.export_json:
        summary = {
            "ops": args.ops,
            "threads": args.threads,
            "host": args.host,
            "port": args.port,
            "keyspace": args.keyspace,
            "ratios": {
                "get": args.read_ratio,
                "set": args.write_ratio,
                "del": args.del_ratio,
            },
            "value_len": args.value_len,
            "throughput_ops_s": tput,
            "avg_us": avg,
            "p50_us": p50,
            "p95_us": p95,
            "p99_us": p99,
            "p999_us": p999,
            "max_us": max_lat,
            "errors": total_errs,
            "duration_s": dur,
        }
        write_json(args.export_json, summary)

    if args.plot:
        plot_latency(lat_sorted)

    return 0


if __name__ == "__main__":
    sys.exit(main())
