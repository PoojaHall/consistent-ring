"""Core implementation of consistent hashing with virtual nodes.

The implementation deliberately uses a fixed hash function (SHA-256) rather than
a pluggable one. This keeps the library small and deterministic, which matters for
tests and for users who need repeatable placements across processes. SHA-256 is in
Python's standard library and has good distribution for this purpose.
"""

from __future__ import annotations

import bisect
import hashlib
from collections.abc import Iterable, Iterator
from typing import Generic, TypeVar

Node = TypeVar("Node")


class ConsistentRing(Generic[Node]):
    """A consistent hash ring with virtual nodes.

    Nodes are hashed onto a ring. Each physical node is represented by a fixed
    number of virtual nodes to reduce load imbalance. A key is mapped to the
    first node whose hash is equal to or greater than the key's hash, wrapping
    around to the beginning if necessary.

    The ring is immutable after creation. Adding or removing nodes requires
    constructing a new ``ConsistentRing``. This avoids a class of bugs involving
    partially updated state, and the use case for this library is stable key
    distribution rather than dynamic membership.
    """

    def __init__(self, nodes: Iterable[Node], virtual_nodes_per_node: int = 150) -> None:
        """Create a consistent hash ring.

        Args:
            nodes: Iterable of physical node identifiers. Must contain at least
                one unique node. Duplicate nodes are ignored.
            virtual_nodes_per_node: Number of virtual points on the ring for
                each physical node. Must be a positive integer.

        Raises:
            ValueError: If there are no unique nodes, or if
                ``virtual_nodes_per_node`` is less than 1.
        """
        if virtual_nodes_per_node < 1:
            raise ValueError("virtual_nodes_per_node must be at least 1")

        unique_nodes = list(dict.fromkeys(nodes))
        if not unique_nodes:
            raise ValueError("nodes must contain at least one unique node")

        self._nodes = unique_nodes
        self._virtual_nodes_per_node = virtual_nodes_per_node
        self._ring: list[tuple[int, Node]] = []
        self._build_ring()

    def _build_ring(self) -> None:
        """Populate the sorted ring of (hash, node) pairs."""
        ring: list[tuple[int, Node]] = []
        for node in self._nodes:
            for virtual_index in range(self._virtual_nodes_per_node):
                ring.append((self._hash_node(node, virtual_index), node))
        ring.sort(key=lambda item: item[0])
        self._ring = ring

    @staticmethod
    def _hash_node(node: Node, virtual_index: int) -> int:
        """Return an integer hash for a virtual node.

        The node and its virtual index are encoded as UTF-8 if they are strings,
        otherwise as their repr. This guarantees a byte string for hashing.
        The virtual index is included so the same physical node appears at
        multiple distinct points.
        """
        if isinstance(node, str):
            node_bytes = node.encode("utf-8")
        else:
            node_bytes = repr(node).encode("utf-8")
        return int.from_bytes(
            hashlib.sha256(node_bytes + virtual_index.to_bytes(4, "big")).digest(),
            "big",
        )

    @staticmethod
    def _hash_key(key: object) -> int:
        """Return an integer hash for a key.

        Uses the same byte representation as ``_hash_node`` so string keys and
        string node identifiers have a consistent mapping domain.
        """
        if isinstance(key, str):
            key_bytes = key.encode("utf-8")
        else:
            key_bytes = repr(key).encode("utf-8")
        return int.from_bytes(hashlib.sha256(key_bytes).digest(), "big")

    def get_node(self, key: object) -> Node:
        """Return the physical node responsible for ``key``.

        Args:
            key: Any hashable object. The hash is derived from its byte
                representation, not Python's built-in ``hash``, so behaviour is
                stable across interpreter runs.

        Returns:
            The node identifier that owns the key.
        """
        if not self._ring:
            raise RuntimeError("ring is empty")
        key_hash = self._hash_key(key)
        index = bisect.bisect_right(self._ring, (key_hash, None))  # type: ignore[arg-type]
        if index == len(self._ring):
            index = 0
        return self._ring[index][1]

    @property
    def nodes(self) -> tuple[Node, ...]:
        """The unique physical nodes in this ring, in insertion order."""
        return tuple(self._nodes)

    @property
    def virtual_nodes_per_node(self) -> int:
        """The number of virtual points per physical node."""
        return self._virtual_nodes_per_node

    def __len__(self) -> int:
        """Return the number of virtual points on the ring."""
        return len(self._ring)

    def __iter__(self) -> Iterator[tuple[int, Node]]:
        """Iterate over (hash, node) virtual points in ring order."""
        return iter(self._ring)

    def __contains__(self, key: object) -> bool:
        """Return True if ``key`` is a physical node in this ring."""
        return key in self._nodes
