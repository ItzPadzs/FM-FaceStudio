"""Compatibility imports for the Sprint 3 asset index."""

from facestudio.assets.database import AssetDatabase
from facestudio.assets.models import AssetRecord
from facestudio.assets.scanner import AssetScanner, ScanResult

__all__ = [
    "AssetDatabase",
    "AssetRecord",
    "AssetScanner",
    "ScanResult",
]
