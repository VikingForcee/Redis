cmake_minimum_required(VERSION 3.10)
project(RedisServer)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Windows-specific settings
if (WIN32)
    add_definitions(-D_WIN32_WINNT=0x0601)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /W4")
    link_libraries(ws2_32)
else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra")
endif()

add_executable(redis_server
    server.cpp
    avl.cpp
    hashtable.cpp
    heap.cpp
    thread_pool.cpp
    zset.cpp
)

target_include_directories(redis_server PRIVATE .)