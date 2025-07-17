import socket
import struct
import threading
import time

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 1234

def build_request(args):
    buf = struct.pack('<I', len(args))
    for arg in args:
        arg_bytes = arg.encode()
        buf += struct.pack('<I', len(arg_bytes)) + arg_bytes
    return struct.pack('<I', len(buf)) + buf

def send_request(sock, args):
    req = build_request(args)
    sock.sendall(req)
    header = sock.recv(4)
    if not header:
        return None
    length = struct.unpack('<I', header)[0]
    return sock.recv(length)

def worker(n_ops):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_HOST, SERVER_PORT))
    for i in range(n_ops):
        send_request(s, ["set", f"key{i}", "value"])
    s.close()

def benchmark(total_ops=100000, threads=10):
    ops_per_thread = total_ops // threads
    start = time.time()
    t_list = []
    for _ in range(threads):
        t = threading.Thread(target=worker, args=(ops_per_thread,))
        t.start()
        t_list.append(t)
    for t in t_list:
        t.join()
    duration = time.time() - start
    print(f"Completed {total_ops} operations in {duration:.2f}s")
    print(f"Throughput: {total_ops/duration:.2f} ops/sec")

if __name__ == "__main__":
    benchmark()
