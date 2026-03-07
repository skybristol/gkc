"""Wikibase integration utilities for GKC.

Phase 0 scope: foundation ontology profile loading, audit, and init.
"""

from gkc.wikibase.foundation import (
    FoundationAuditError,
    FoundationAuditReport,
    FoundationInitError,
    FoundationInitReport,
    FoundationProfileError,
    audit_wikibase_foundation,
    init_wikibase_foundation,
    load_foundation_profiles,
)

__all__ = [
    "FoundationAuditError",
    "FoundationAuditReport",
    "FoundationInitError",
    "FoundationInitReport",
    "FoundationProfileError",
    "audit_wikibase_foundation",
    "init_wikibase_foundation",
    "load_foundation_profiles",
]
