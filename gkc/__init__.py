"""
GKC - Global Knowledge Commons

A Python package for working with the Global Knowledge Commons including
Wikidata, Wikipedia, Wikimedia Commons, and OpenStreetMap.
"""

__version__ = "0.1.0"

from gkc.auth import OpenStreetMapAuth, WikiverseAuth

__all__ = ["WikiverseAuth", "OpenStreetMapAuth"]
