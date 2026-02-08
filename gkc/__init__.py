"""
GKC - Global Knowledge Commons

A Python package for working with the Global Knowledge Commons including
Wikidata, Wikipedia, and OpenStreetMap.
"""

__version__ = "0.1.0"

from gkc.auth import OpenStreetMapAuth, WikidataAuth, WikipediaAuth

__all__ = ["WikidataAuth", "WikipediaAuth", "OpenStreetMapAuth"]
