Mini Redis Server
A lightweight, in-memory key-value store inspired by Redis, implemented in C++ for high performance. This server supports basic Redis commands (SET, GET, DEL, PEXPIRE, PTTL, KEYS, ZADD, ZREM, ZSCORE, ZQUERY) and is designed to run on both Windows and Linux, with deployment options for Render and Docker.
Features

Key-Value Storage: Supports string key-value pairs.
Sorted Sets: Implements sorted sets with AVL trees for efficient range queries.
TTL Support: Time-to-live for keys with automatic expiration.
Thread Pool: Asynchronous deletion of large data structures.
Cross-Platform: Compatible with Windows (Visual Studio Code) and Linux (Docker/Render).
Event-Driven: Uses select for handling multiple client connections efficiently.

Benchmark Results
The server was benchmarked using a Python script (bench.py) on a Windows system. Below are the results for various configurations:
Default Configuration (100,000 SET operations)

Total Ops Completed: 100,000
Total Time: 3.044 seconds
Throughput: 32,846.70 ops/s
Latency:
Average: 0.290 ms
P50: 0.254 ms
P95: 0.602 ms
P99: 0.857 ms
P99.9: 1.320 ms
Max: 8.409 ms



High Load (1,000,000 SET operations, 50 threads)

Total Ops Completed: 1,000,000
Total Time: 36.744 seconds
Throughput: 27,215.01 ops/s
Latency:
Average: 1.822 ms
P50: 1.561 ms
P95: 4.250 ms
P99: 6.075 ms
P99.9: 8.865 ms
Max: 68.679 ms



Mixed Workload (80% read, 15% write, 5% delete)

Total Ops Completed: 100,000
Total Time: 3.123 seconds
Throughput: 32,019.48 ops/s
Latency:
Average: 0.300 ms
P50: 0.269 ms
P95: 0.598 ms
P99: 0.813 ms
P99.9: 1.155 ms
Max: 7.680 ms



Large Values (512-byte values)

Total Ops Completed: 100,000
Total Time: 3.213 seconds
Throughput: 31,123.64 ops/s
Latency:
Average: 0.306 ms
P50: 0.270 ms
P95: 0.638 ms
P99: 0.890 ms
P99.9: 1.274 ms
Max: 8.684 ms



Latency Sampling (every 5 operations)

Total Ops Completed: 100,000
Total Time: 2.865 seconds
Throughput: 34,898.79 ops/s
Latency:
Average: 0.277 ms
P50: 0.247 ms
P95: 0.569 ms
P99: 0.787 ms
P99.9: 1.163 ms
Max: 6.382 ms



Prerequisites

Windows Development:
Visual Studio Code
CMake (3.10 or higher)
C++ compiler (e.g., MSVC via Visual Studio Build Tools)
Git


Linux/Docker:
Docker (for containerized deployment)
CMake, g++, make (for building on Linux)


Testing:
Redis client (e.g., redis-cli)
Python (for running bench.py)



Project Structure
Redis/
|-RedisMain/
|    ├── avl.cpp
|    ├── avl.h
|    ├── common.h
|    ├── hashtable.cpp
|    ├── hashtable.h
|    ├── heap.cpp
|    ├── heap.h
|    ├── list.h
|    ├── server.cpp
|    ├── thread_pool.cpp
|    ├── thread_pool.h
|    ├── zset.cpp
|    ├── zset.h
|    ├── CMakeLists.txt
|    ├── Dockerfile
|
|── testing/
|    |── bench.py
|    |── bench2.py
|    
|── README.md

Setup Instructions (Windows with Visual Studio Code)

Clone the Repository:
git clone https://github.com/VikingForcee/Redis.git
cd Redis
cd RedisMain

Install Dependencies:

Install Visual Studio Code and the C/C++ extension by Microsoft.
Ensure Git is installed.

Run the Server:

Execute the generated server.exe in the build directory.
The server listens on localhost:1234.


Test with redis-cli:
redis-cli -h localhost -p 1234

Example commands:
SET key value
GET key
ZADD zset 1.0 member
ZSCORE zset member


Test the Server:

Connect to localhost:1234 using redis-cli.


Configure Environment:

Set the port to 1234 in the service settings.
Deploy the service.


Test the Deployment:

Use the Render-provided URL with redis-cli to test the server.

Notes

The server uses select for event handling, which is cross-platform but may not scale to thousands of connections. For production, consider replacing with epoll (Linux) or IOCP (Windows).
The zset implementation uses AVL trees for sorted sets, ensuring efficient range queries.
The thread pool uses C++11 std::thread for portability.
Ensure port 1234 is open in your firewall or cloud provider settings for deployment.

Contributing
Contributions are welcome! Please submit a pull request or open an issue for bugs, features, or improvements.