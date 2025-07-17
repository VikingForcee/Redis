#pragma once

struct DList {
    DList *next = nullptr;
    DList *prev = nullptr;
};

// Initialize an empty list (head node)
inline void dlist_init(DList *list) {
    list->next = list;
    list->prev = list;
}

// Insert node before the given list node
inline void dlist_insert_before(DList *list, DList *node) {
    node->next = list;
    node->prev = list->prev;
    list->prev->next = node;
    list->prev = node;
}

// Detach a node from the list
inline void dlist_detach(DList *node) {
    node->prev->next = node->next;
    node->next->prev = node->prev;
    node->next = nullptr;
    node->prev = nullptr;
}

// Check if the list is empty
inline bool dlist_empty(DList *list) {
    return list->next == list;
}