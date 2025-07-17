#include <cassert>
#include "thread_pool.h"

static void worker(ThreadPool *tp) {
    while (true) {
        Work w;
        {
            std::unique_lock<std::mutex> lock(tp->mu);
            tp->not_empty.wait(lock, [tp] { return !tp->queue.empty(); });
            w = tp->queue.front();
            tp->queue.pop_front();
        }
        w.f(w.arg);
    }
}

void thread_pool_init(ThreadPool *tp, size_t num_threads) {
    assert(num_threads > 0);
    tp->threads.reserve(num_threads);
    for (size_t i = 0; i < num_threads; ++i) {
        tp->threads.emplace_back(worker, tp);
    }
}

void thread_pool_queue(ThreadPool *tp, void (*f)(void *), void *arg) {
    {
        std::unique_lock<std::mutex> lock(tp->mu);
        tp->queue.push_back(Work{f, arg});
    }
    tp->not_empty.notify_one();
}