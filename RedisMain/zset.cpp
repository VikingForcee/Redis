#include <cassert>
#include <cstdlib>
#include <cstring>
#include "zset.h"
#include "common.h"

static bool znode_eq(HNode *node, HNode *key) {
    ZNode *znode = CONTAINER_OF(node, ZNode, hnode);
    ZNode *keynode = CONTAINER_OF(key, ZNode, hnode);
    return znode->len == keynode->len && memcmp(znode->name, keynode->name, znode->len) == 0;
}

static int znode_cmp(ZNode *a, ZNode *b) {
    if (a->score != b->score) {
        return a->score < b->score ? -1 : 1;
    }
    return memcmp(a->name, b->name, a->len < b->len ? a->len : b->len);
}

bool zset_insert(ZSet *zset, const char *name, size_t len, double score) {
    ZNode key;
    key.hnode.hcode = str_hash((const uint8_t *)name, len);
    key.name = (char *)name;
    key.len = len;

    HNode *hnode = hm_lookup(&zset->hmap, &key.hnode, &znode_eq);
    if (hnode) {
        ZNode *znode = CONTAINER_OF(hnode, ZNode, hnode);
        if (znode->score == score) {
            return false;
        }
        zset->root = avl_del(&znode->anode);
        znode->score = score;
        zset->root = avl_fix(&znode->anode);
        return false;
    }

    ZNode *znode = new ZNode();
    znode->hnode.hcode = key.hnode.hcode;
    znode->score = score;
    znode->len = len;
    znode->name = (char *)malloc(len);
    memcpy(znode->name, name, len);
    avl_init(&znode->anode);
    hm_insert(&zset->hmap, &znode->hnode);
    zset->root = avl_fix(&znode->anode);
    return true;
}

void zset_delete(ZSet *zset, ZNode *znode) {
    zset->root = avl_del(&znode->anode);
    hm_delete(&zset->hmap, &znode->hnode, &znode_eq);
    free(znode->name);
    delete znode;
}

ZNode *zset_lookup(ZSet *zset, const char *name, size_t len) {
    ZNode key;
    key.hnode.hcode = str_hash((const uint8_t *)name, len);
    key.name = (char *)name;
    key.len = len;
    HNode *hnode = hm_lookup(&zset->hmap, &key.hnode, &znode_eq);
    return hnode ? CONTAINER_OF(hnode, ZNode, hnode) : nullptr;
}

ZNode *zset_seekge(ZSet *zset, double score, const char *name, size_t len) {
    ZNode *cur = zset->root ? CONTAINER_OF(zset->root, ZNode, anode) : nullptr;
    ZNode *best = nullptr;
    while (cur) {
        ZNode tmp;
        tmp.score = score;
        tmp.name = (char *)name;
        tmp.len = len;
        int cmp = znode_cmp(cur, &tmp);
        if (cmp == 0) {
            return cur;
        }
        if (cmp < 0) {
            cur = cur->anode.right ? CONTAINER_OF(cur->anode.right, ZNode, anode) : nullptr;
        } else {
            best = cur;
            cur = cur->anode.left ? CONTAINER_OF(cur->anode.left, ZNode, anode) : nullptr;
        }
    }
    return best;
}

ZNode *znode_offset(ZNode *znode, int64_t offset) {
    return znode ? CONTAINER_OF(avl_offset(&znode->anode, offset), ZNode, anode) : nullptr;
}

void zset_clear(ZSet *zset) {
    while (zset->root) {
        ZNode *znode = CONTAINER_OF(zset->root, ZNode, anode);
        zset->root = avl_del(&znode->anode);
        hm_delete(&zset->hmap, &znode->hnode, &znode_eq);
        free(znode->name);
        delete znode;
    }
    hm_clear(&zset->hmap);
}./server.exe