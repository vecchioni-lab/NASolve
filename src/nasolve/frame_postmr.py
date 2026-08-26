"""Post-MR site and restraint manifests for approved standard frames."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StandardSite:
    chain: str
    resid: str

    @property
    def text(self) -> str:
        return f"{self.chain}:{self.resid}"


@dataclass(frozen=True)
class FramePostMRSpec:
    name: str
    sites: tuple[StandardSite, StandardSite]
    pair_file: str
    secondary_structure_file: str


FRAME_POSTMR_SPECS: dict[str, FramePostMRSpec] = {
    "W": FramePostMRSpec(
        name="W",
        sites=(StandardSite("A", "12"), StandardSite("B", "4")),
        pair_file="5W6W_Std_padd.txt",
        secondary_structure_file="5W6W_secondary_structure.eff",
    ),
}


def restraint_data_directory(data_root: Path | None = None) -> Path:
    if data_root is not None:
        return Path(data_root) / "restraints"
    return Path(__file__).resolve().parent / "data" / "restraints"


def frame_postmr_spec(frame_name: str) -> FramePostMRSpec:
    try:
        return FRAME_POSTMR_SPECS[frame_name]
    except KeyError as exc:
        raise KeyError(
            f"PostMR site manifest is not configured for standard frame {frame_name}"
        ) from exc


__all__ = [
    "FRAME_POSTMR_SPECS",
    "FramePostMRSpec",
    "StandardSite",
    "frame_postmr_spec",
    "restraint_data_directory",
]
