"""Deterministic, UV-safe skin-transfer building blocks.

The prototype deliberately operates on already aligned images. It changes colour and
surface detail while preserving donor geometry and protected facial regions.
"""

from facestudio.ai.skin_transfer.pipeline import SkinTransferPipeline, SkinTransferRequest, SkinTransferResult

__all__ = ["SkinTransferPipeline", "SkinTransferRequest", "SkinTransferResult"]
