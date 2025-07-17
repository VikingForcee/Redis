#pragma once

#include <stddef.h>
#include <thread>
#include <vector>
#include <deque>
#include <mutex>
#include <condition_variable>

struct Work {
    void (*f)(void *) = nullptr;
    void *arg = nullptr;
};

struct ThreadPool {
    std::vector<std::thread> threads;
    std::deque<Work> queue;
    std::mutex mu;
    std::condition_variable not_empty;
};

void thread_pool_init(ThreadPool *tp, size_t num_threads);
void thread_pool_queue(ThreadPool *tp, void (*f)(void *), void *arg);