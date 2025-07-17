#include <stddef.h>
#include <cstdint>

// Generic implementation of container_of for C++
template <typename T, typename M>
inline T* container_of_func(M* ptr, size_t offset) {
    return reinterpret_cast<T*>(reinterpret_cast<char*>(ptr) - offset);
}

// Macro to simplify usage
#define CONTAINER_OF(ptr, type, member) \
    container_of_func<type>(ptr, offsetof(type, member))

// FNV hash function
inline uint64_t str_hash(const uint8_t *data, size_t len) {
    uint32_t h = 0x811C9DC5;
    for (size_t i = 0; i < len; i++) {
        h = (h + data[i]) * 0x01000193;
    }
    return h;
}
