#pragma once

#include <stddef.h>
#include <stdint.h>
#include "hashtable.h"
#include "avl.h"

struct ZNode {
    HNode hnode; // for hashtable
    AVLNode anode; // for AVL tree
    double score;
    char *name;
    size_t len;
};

struct ZSet {
    HMap hmap;
    AVLNode *root = nullptr;
};

bool zset_insert(ZSet *zset, const char *name, size_t len, double score);
void zset_delete(ZSet *zset, ZNode *znode);
ZNode *zset_lookup(ZSet *zset, const char *name, size_t len);
ZNode *zset_seekge(ZSet *zset, double score, const char *name, size_t len);
ZNode *znode_offset(ZNode *znode, int64_t offset);
void zset_clear(ZSet *zset);