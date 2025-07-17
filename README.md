# Mini Redis Server

A lightweight, high-performance, in-memory key–value store inspired by Redis, implemented in C++. It supports a subset of Redis-style commands (strings, sorted sets, TTL) and is portable across Windows and Linux. Deployment options include local builds, Docker containers, and Render.

---

## Table of Contents
- [Features](#features)
- [Supported Commands](#supported-commands)
- [Quick Start](#quick-start)
  - [Windows (Visual Studio Code)](#windows-visual-studio-code)
  - [Linux Build](#linux-build)
  - [Docker](#docker)
  - [Deploy on Render](#deploy-on-render)
- [Connecting With redis-cli](#connecting-with-redis-cli)
- [Benchmarks](#benchmarks)
- [Project Structure](#project-structure)
- [Architecture Overview](#architecture-overview)
- [Configuration Notes](#configuration-notes)
- [Limitations and Future Work](#limitations-and-future-work)
- [Contributing](#contributing)
- [License](#license)

---

## Features
- Key–Value string storage.
- Sorted sets backed by an AVL tree for efficient score-ordered lookups and range-style queries.
- TTL support (PEXPIRE, PTTL) with automatic expiration.
- Background thread pool used for asynchronous clean-up of large data structures.
- Cross-platform networking layer: builds on Windows (MSVC / Visual Studio Code) and Linux (g++).
- Event-driven I/O uses `select()` for multiplexing multiple client connections.

---

## Supported Commands
| Command | Description | Example |
|---------|-------------|---------|
| `SET key value` | Set string value. | `SET foo bar` |
| `GET key` | Get string value. | `GET foo` |
| `DEL key` | Delete key. | `DEL foo` |
| `PEXPIRE key ms` | Set TTL in milliseconds. | `PEXPIRE foo 5000` |
| `PTTL key` | Return remaining TTL in ms. | `PTTL foo` |
| `KEYS pattern` | Return keys matching glob-like pattern (`*`, `?`). | `KEYS *` |
| `ZADD zset score member` | Add/update sorted-set member. | `ZADD ranks 1.0 alice` |
| `ZREM zset member` | Remove member from sorted set. | `ZREM ranks alice` |
| `ZSCORE zset member` | Get score of member. | `ZSCORE ranks alice` |
| `ZQUERY zset min max` | Range query by score (inclusive). | `ZQUERY ranks 0 100` |

> Notes:  
> - Command grammar is simplified; multi-bulk protocol coverage is limited.  
> - Numeric ranges in `ZQUERY` are parsed as doubles.  

---

## Quick Start

### Windows (Visual Studio Code)
```bash
git clone https://github.com/VikingForcee/Redis.git
cd Redis/RedisMain
mkdir build
cd build
cmake ..
cmake --build . --config Release
```

## Run the Server
server.exe
By default the server listens on localhost:1234.

## Docker
A Dockerfile is provided in RedisMain/

```bash
cd Redis/RedisMain
docker build -t mini-redis-server .
docker run --rm -p 1234:1234 mini-redis-server
```

## Connecting with Redis CLI

```bash
redis-cli -h <host> -p 1234
```

Examples:
SET key value
GET key
ZADD zset 1.0 member
ZSCORE zset member


## Benchmarks

Benchmarks were run on Windows using testing/bench.py unless noted. Times include network overhead on localhost.

Summary Metrics
``` bash
Scenario	Operations	Threads	Total Time (s)	Throughput (ops/s)	Avg Latency (ms)	P50	P95	P99	P99.9	Max (ms)
Default	100,000 SET	1	3.044	32,846.70	0.290	0.254	0.602	0.857	1.320	8.409
High Load	1,000,000 SET	50	36.744	27,215.01	1.822	1.561	4.250	6.075	8.865	68.679
Mixed (80% GET, 15% SET, 5% DEL)	100,000 ops	multi	3.123	32,019.48	0.300	0.269	0.598	0.813	1.155	7.680
Large Values (512B)	100,000 SET	1	3.213	31,123.64	0.306	0.270	0.638	0.890	1.274	8.684
Latency Sample (sample every 5 ops)	100,000 SET	1	2.865	34,898.79	0.277	0.247	0.569	0.787	1.163	6.382
```

Raw benchmark scripts live in testing/bench.py and testing/bench2.py.

## Project Structure

```bash
Redis/
├── RedisMain/
│   ├── avl.cpp
│   ├── avl.h
│   ├── common.h
│   ├── hashtable.cpp
│   ├── hashtable.h
│   ├── heap.cpp
│   ├── heap.h
│   ├── list.h
│   ├── server.cpp
│   ├── thread_pool.cpp
│   ├── thread_pool.h
│   ├── zset.cpp
│   ├── zset.h
│   ├── CMakeLists.txt
│   ├── Dockerfile
│
├── testing/
│   ├── bench.py
│   ├── bench2.py
│
└── README.md

```

## Architecture Overview

### Networking / Event Loop
Uses select() to multiplex client sockets.
Simple line-based or space-delimited command parsing (see server.cpp).

### Data Structures
String keys stored in a hash table (hashtable.*).
TTL metadata tracked via a min-heap (heap.*) keyed by expiration timestamps; expired keys lazily removed.
Sorted sets implemented using an AVL tree (avl.* + zset.*) keyed by score; supports score lookups and score-range scans.

### TTL & Expiration Flow
PEXPIRE registers expiration time in the heap.
Periodic or on-access checks clear expired keys.
Large deletions may be delegated to the thread pool.

### Thread Pool
C++11 std::thread based.
Tasks queued for background cleanup/non-blocking operations.
Size configurable at compile time or via a constant (see thread_pool.*).

## Configuration Notes
Default listen port is 1234. Update in source or through a command-line flag if implemented (check server.cpp).

Ensure port 1234 is open in local firewall, container runtime, and cloud security groups.

For large-scale deployments, consider replacing select() with:

epoll (Linux)

IOCP (Windows)

Persistence is not implemented; all data is in-memory and lost on restart.

Authentication and ACLs are not implemented; run behind trusted network boundaries.

## Limitations and Future Work
Full Redis protocol (RESP) parsing is partial; multiline values and binary-safe payloads need work.

select() scales poorly to thousands of concurrent sockets; move to epoll/kqueue/IOCP for higher concurrency.

No replication, clustering, or persistence (AOF/RDB-style snapshots).

Metrics / monitoring endpoints would be helpful.

Add CI builds for Windows + Linux.

Add fuzz + stress tests for parser and data structures.

Expand ZSET API: ZRANGE, ZRANGEBYSCORE, ZCARD, etc.

## Contributing
Contributions are welcome. Please:

Fork the repository.

Create a feature branch.

Follow existing coding style (see headers/sources).

Add tests (benchmark or unit) when possible.

Open a pull request describing the change and performance impact.

Bug reports are also welcome—open an issue with reproducible steps, environment details, and expected vs. actual behavior.

## Acknowledgments
Inspired by Redis data structures and semantics. Not a drop-in replacement.
The project could'nt have been possible without Build Your Own X : Mini Redis Server (Book)