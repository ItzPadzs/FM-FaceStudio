"""Deterministic, UV-safe portrait and skin-transfer building blocks.

Portrait alignment operates only on the source photograph. Donor UV geometry and
animation-sensitive regions remain fixed throughout compositing.
"""

from facestudio.ai.skin_transfer.alignment import FaceLandmarks, ManualLandmarkDetector, align_portrait
from facestudio.ai.skin_transfer.pipeline import SkinTransferPipeline, SkinTransferRequest, SkinTransferResult
from facestudio.ai.skin_transfer.portrait_pipeline import PortraitSkinTransferPipeline, PortraitSkinTransferRequest
from facestudio.ai.skin_transfer.profiles import MaskProfile, load_mask_profile

__all__ = [
    "FaceLandmarks",
    "ManualLandmarkDetector",
    "MaskProfile",
    "PortraitSkinTransferPipeline",
    "PortraitSkinTransferRequest",
    "SkinTransferPipeline",
    "SkinTransferRequest",
    "SkinTransferResult",
    "align_portrait",
    "load_mask_profile",
]
