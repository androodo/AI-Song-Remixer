import argparse
import json
import os
from typing import Any, Dict, List, Optional

import numpy as np

from audio_ai.embed import embed_audio_file
from audio_ai.index import IndexData, ReferenceItem, save_index


def _infer_effect_from_name(name: str) -> str:
    n = name.lower()
    for eff in ["lofi", "jazz", "dubstep", "vaporwave", "rock"]:
        if eff in n:
            return eff
    return "lofi"


def _load_metadata(meta_path: str) -> Dict[str, Any]:
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_index(
    reference_dir: str,
    *,
    ffmpeg_exe: Optional[str] = None,
    meta_path: Optional[str] = None,
) -> IndexData:
    """
    Builds an embedding index from audio files in reference_dir.

    Optional metadata JSON format (meta_path):
    {
      "items": [
        {"file": "lofi_example1.mp3", "effect": "lofi", "params": {...}, "label": "warm vinyl"},
        ...
      ]
    }
    """
    meta = None
    meta_items: Dict[str, Dict[str, Any]] = {}
    if meta_path and os.path.exists(meta_path):
        meta = _load_metadata(meta_path)
        for it in meta.get("items", []):
            meta_items[str(it.get("file", ""))] = dict(it)

    audio_exts = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"}
    paths: List[str] = []
    for root, _, files in os.walk(reference_dir):
        for fn in files:
            if os.path.splitext(fn)[1].lower() in audio_exts:
                paths.append(os.path.join(root, fn))
    paths.sort()
    if not paths:
        raise RuntimeError(f"No audio files found in {reference_dir}")

    embs: List[np.ndarray] = []
    items: List[ReferenceItem] = []

    for p in paths:
        fn = os.path.basename(p)
        md = meta_items.get(fn, {})
        effect = str(md.get("effect") or _infer_effect_from_name(fn))
        params = dict(md.get("params") or {})
        label = str(md.get("label") or "")

        emb = embed_audio_file(p, ffmpeg_exe=ffmpeg_exe)
        embs.append(emb)
        items.append(ReferenceItem(path=p, effect=effect, params=params, label=label))

    embeddings = np.stack(embs, axis=0).astype(np.float32)
    return IndexData(embeddings=embeddings, items=items)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build local audio embedding index (offline).")
    ap.add_argument("--reference-dir", default="reference_audio", help="Folder of reference clips")
    ap.add_argument("--meta", default="reference_audio/metadata.json", help="Optional metadata JSON")
    ap.add_argument("--ffmpeg", default=None, help="Path to ffmpeg executable (or relies on PATH)")
    ap.add_argument("--out-dir", default=os.path.join("audio_ai", "index_data"), help="Output index dir")
    args = ap.parse_args()

    data = build_index(args.reference_dir, ffmpeg_exe=args.ffmpeg, meta_path=args.meta)
    save_index(data, index_dir=args.out_dir)
    print(f"Built index with {len(data.items)} items -> {args.out_dir}")


if __name__ == "__main__":
    main()

