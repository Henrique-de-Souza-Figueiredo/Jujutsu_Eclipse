"""Dispose complete entity trees, including Ursina's Python-side registries."""
from ursina import destroy as destroy_entity


def dispose(node):
    if node is None or node.is_empty():
        return
    for child in list(node.children):
        dispose(child)
    destroy_entity(node)
