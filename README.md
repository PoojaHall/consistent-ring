# Consistent Ring

Consistent Ring provides a small, deterministic consistent-hashing ring with virtual nodes. It maps keys to physical nodes with stable distribution, so adding or removing a node changes only a fraction of assignments.

```python
from consistent_ring import ConsistentRing

ring = ConsistentRing(["cache-1", "cache-2", "cache-3"], virtual_nodes_per_node=150)
node = ring.get_node("user:42")
print(node)  # e.g. "cache-2"
```

## Why this exists

Naive hashing (`hash(key) % len(nodes)`) reassigns nearly every key when the node count changes. Consistent hashing instead places nodes on a ring and walks clockwise from a key's hash to find its owner, so only keys near a changed node move. Virtual nodes (multiple points per physical node) reduce load imbalance between nodes with different hash positions.

This implementation chooses SHA-256 as the only hash function. That makes the mapping stable across Python processes and avoids the need for a pluggable hash abstraction. It also uses an immutable ring: nodes are fixed at construction time. If you need to add or remove nodes, build a new `ConsistentRing`. That keeps the implementation small and avoids a class of bugs from partially updated state.

## Awkward edge

Keys and nodes can be strings or arbitrary hashable objects. Non-string values are hashed via their `repr`, so two different objects with the same `repr` will map identically. That is a deliberate trade-off for deterministic behaviour; do not use objects whose `repr` is not a faithful identifier.

## API

### `ConsistentRing(nodes, virtual_nodes_per_node=150)`

Create a ring from an iterable of unique physical nodes. `virtual_nodes_per_node` must be a positive integer. Duplicate nodes are ignored, and the ring must contain at least one unique node.

### `ring.get_node(key)`

Return the physical node responsible for `key`.

### `ring.nodes`

Tuple of unique physical nodes in insertion order.

### `ring.virtual_nodes_per_node`

The configured number of virtual points per physical node.

### `len(ring)`

The number of virtual points on the ring.

### `iter(ring)`

Yields `(hash, node)` pairs in ascending ring order.

### `node in ring`

Return `True` if `node` is one of the physical nodes in the ring.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

## Limitations

Values are coerced to floats, so very large integers lose precision. If you need
exact integer aggregates over a window, this is the wrong tool.

