"""Export a quality-approved raw episode with only RoboDojo observation fields."""
import argparse
from pathlib import Path

import h5py
import numpy as np

from recording import CAMERAS, OFFICIAL_STATE_FIELDS


COMMAND_FIELDS = (
    "left_arm_joint_states", "left_ee_joint_states",
    "right_arm_joint_states", "right_ee_joint_states",
)


def export_episode(source, destination):
    source, destination = Path(source), Path(destination)
    with h5py.File(source, "r") as raw:
        if not raw.attrs.get("complete") or not raw.attrs.get("quality_pass") or not raw.attrs.get("training_eligible"):
            raise ValueError("Only complete, quality-approved training episodes can be exported")
        if not raw.attrs.get("success"):
            raise ValueError("An unsuccessful episode is not a positive demonstration")
        valid = np.asarray(raw["action_valid"][:], dtype=bool)
        if len(valid) < 3 or not np.all(valid[:-1]) or valid[-1]:
            raise ValueError("Expected valid transitions followed by one terminal row")
        count = len(valid) - 1
        if set(raw["state"]) != set(OFFICIAL_STATE_FIELDS) or set(raw["command"]) != set(COMMAND_FIELDS):
            raise ValueError("State or command fields differ from the expected RoboDojo contract")
        if set(raw["vision"]) != set(CAMERAS):
            raise ValueError("Camera fields differ from the expected RoboDojo contract")
        with h5py.File(destination, "x") as out:
            for name in ("data_format_version", "instruction", "additional_info"):
                raw.copy(name, out)
            out.create_group("state")
            out.create_group("action")
            for name in OFFICIAL_STATE_FIELDS:
                out[f"state/{name}"] = raw[f"state/{name}"][:count]
            for name in COMMAND_FIELDS:
                out[f"action/{name}"] = raw[f"command/{name}"][:count]
            for camera in CAMERAS:
                prefix = f"vision/{camera}"
                for name in ("shape", "intrinsic_matrix"):
                    raw.copy(f"{prefix}/{name}", out.require_group(prefix), name=name)
                for name in ("colors", "extrinsic_matrix"):
                    source_dataset = raw[f"{prefix}/{name}"]
                    chunks = (min(source_dataset.chunks[0], count), *source_dataset.chunks[1:])
                    out.create_dataset(f"{prefix}/{name}", data=source_dataset[:count],
                                       chunks=chunks, compression=source_dataset.compression)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(export_episode(args.source, args.destination))
