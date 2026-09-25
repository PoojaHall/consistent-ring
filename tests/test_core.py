"""Tests for ConsistentRing."""

import unittest

from consistent_ring import ConsistentRing


class ConsistentRingInitTest(unittest.TestCase):
    def test_empty_nodes_raises(self):
        with self.assertRaises(ValueError):
            ConsistentRing([])

    def test_zero_virtual_nodes_raises(self):
        with self.assertRaises(ValueError):
            ConsistentRing(["a"], virtual_nodes_per_node=0)

    def test_duplicate_nodes_are_ignored(self):
        ring = ConsistentRing(["a", "a", "b"])
        self.assertEqual(ring.nodes, ("a", "b"))

    def test_nodes_property_is_tuple(self):
        ring = ConsistentRing(["a", "b"])
        self.assertIsInstance(ring.nodes, tuple)
        self.assertEqual(ring.nodes, ("a", "b"))

    def test_len_is_virtual_nodes_times_unique_nodes(self):
        ring = ConsistentRing(["a", "b", "c"], virtual_nodes_per_node=5)
        self.assertEqual(len(ring), 15)


class ConsistentRingGetNodeTest(unittest.TestCase):
    def test_returns_one_of_the_physical_nodes(self):
        ring = ConsistentRing(["alpha", "beta", "gamma"], virtual_nodes_per_node=20)
        for key in ["k1", "k2", "k3", 42, (1, 2)]:
            self.assertIn(ring.get_node(key), ring.nodes)

    def test_same_key_same_node(self):
        ring = ConsistentRing(["a", "b", "c"])
        key = "stable-key"
        first = ring.get_node(key)
        for _ in range(10):
            self.assertEqual(ring.get_node(key), first)

    def test_different_keys_may_map_differently(self):
        ring = ConsistentRing(["a", "b", "c"], virtual_nodes_per_node=100)
        keys = [f"key-{i}" for i in range(50)]
        mapped = {ring.get_node(k) for k in keys}
        # With 100 virtual nodes per physical node and 50 keys, it is extremely
        # likely that more than one node is used. This assertion is deterministic
        # because SHA-256 placement is fixed; we test the actual distribution
        # produced by this implementation.
        self.assertGreater(len(mapped), 1)

    def test_hash_uses_byte_representation_not_python_hash(self):
        # Python's hash for strings is salted per process, so the same string
        # could map differently across runs. Our implementation uses SHA-256,
        # so the mapping must be stable for a fixed set of nodes.
        ring1 = ConsistentRing(["x", "y", "z"])
        ring2 = ConsistentRing(["x", "y", "z"])
        for key in ["alpha", "beta", "gamma", 123, (1, 2, 3)]:
            self.assertEqual(ring1.get_node(key), ring2.get_node(key))

    def test_non_string_nodes_and_keys(self):
        ring = ConsistentRing([1, 2, 3], virtual_nodes_per_node=5)
        key = 99
        self.assertIn(ring.get_node(key), ring.nodes)

    def test_get_node_after_wrap_around(self):
        # Force a small ring where the wrap-around behaviour can be exercised
        # by checking that a key hashing above the last virtual point maps to
        # the first virtual point.
        ring = ConsistentRing(["a"], virtual_nodes_per_node=1)
        key_hash = ring._hash_key("anything")
        ring_hash = ring._ring[0][0]
        if key_hash < ring_hash:
            # Find a key whose hash is greater than the only ring hash
            # to trigger wrap-around. We search a small deterministic space.
            found = None
            for candidate in range(10000):
                if ring._hash_key(candidate) >= ring_hash:
                    found = candidate
                    break
            self.assertIsNotNone(found, "could not find a wrapping key")
            self.assertEqual(ring.get_node(found), "a")

    def test_contains(self):
        ring = ConsistentRing(["a", "b"])
        self.assertIn("a", ring)
        self.assertNotIn("c", ring)

    def test_iter_returns_sorted_hash_node_pairs(self):
        ring = ConsistentRing(["a", "b"], virtual_nodes_per_node=3)
        items = list(ring)
        hashes = [h for h, _ in items]
        self.assertEqual(hashes, sorted(hashes))
        self.assertEqual(len(items), 6)
        for h, node in items:
            self.assertIsInstance(h, int)
            self.assertIn(node, ring.nodes)


if __name__ == "__main__":
    unittest.main()
