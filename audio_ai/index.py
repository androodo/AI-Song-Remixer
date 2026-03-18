import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class ReferenceItem:
    path: str
    effect: str
    params: Dict[str, Any]
    label: str = ""


@dataclass(frozen=True)
class IndexData:
    embeddings: np.ndarray  # shape (N, D), float32, L2-normalized
    items: List[ReferenceItem]


DEFAULT_INDEX_DIR = os.path.join("audio_ai", "index_data")
EMB_PATH = os.path.join(DEFAULT_INDEX_DIR, "embeddings.npy")
META_PATH = os.path.join(DEFAULT_INDEX_DIR, "references.json")


def ensure_index_dir(index_dir: str = DEFAULT_INDEX_DIR) -> None:
    os.makedirs(index_dir, exist_ok=True)


def save_index(data: IndexData, index_dir: str = DEFAULT_INDEX_DIR) -> None:
    ensure_index_dir(index_dir)
    np.save(os.path.join(index_dir, "embeddings.npy"), data.embeddings.astype(np.float32))
    meta = [
        {"path": it.path, "effect": it.effect, "params": it.params, "label": it.label}
        for it in data.items
    ]
    with open(os.path.join(index_dir, "references.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def load_index(index_dir: str = DEFAULT_INDEX_DIR) -> Optional[IndexData]:
    emb_path = os.path.join(index_dir, "embeddings.npy")
    meta_path = os.path.join(index_dir, "references.json")
    if not (os.path.exists(emb_path) and os.path.exists(meta_path)):
        return None

    embeddings = np.load(emb_path).astype(np.float32)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    items = [
        ReferenceItem(
            path=str(m.get("path", "")),
            effect=str(m.get("effect", "lofi")),
            params=dict(m.get("params", {})),
            label=str(m.get("label", "")),
        )
        for m in meta
    ]
    if embeddings.ndim != 2 or embeddings.shape[0] != len(items):
        raise ValueError("Index embeddings/metadata mismatch")
    return IndexData(embeddings=embeddings, items=items)


def cosine_topk(
    query: np.ndarray, embeddings: np.ndarray, k: int = 5
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Return (indices, scores) for top-k cosine similarity.
    Assumes embeddings are L2-normalized and query is L2-normalized.
    """
    if query.ndim != 1:
        raise ValueError("query must be 1D")
    scores = embeddings @ query.astype(np.float32)
    if k >= scores.shape[0]:
        idx = np.argsort(-scores)
    else:
        idx_part = np.argpartition(-scores, k)[:k]
        idx = idx_part[np.argsort(-scores[idx_part])]
    return idx.astype(np.int64), scores[idx].astype(np.float32)


def recommend_from_index(
    query_embedding: np.ndarray,
    data: IndexData,
    *,
    k: int = 5,
) -> Dict[str, Any]:
    idx, scores = cosine_topk(query_embedding, data.embeddings, k=k)

    top = []
    for i, s in zip(idx.tolist(), scores.tolist()):
        it = data.items[i]
        top.append(
            {
                "effect": it.effect,
                "params": it.params,
                "label": it.label,
                "path": it.path,
                "score": float(s),
            }
        )

    # Simple majority-vote on effect among top-k, tie-broken by best score
    by_effect: Dict[str, Tuple[int, float, Dict[str, Any]]] = {}
    for cand in top:
        eff = cand["effect"]
        count, best, best_cand = by_effect.get(eff, (0, -1.0, cand))
        count += 1
        if cand["score"] > best:
            best = cand["score"]
            best_cand = cand
        by_effect[eff] = (count, best, best_cand)

    # Pick effect by (count, best_score)
    eff_sorted = sorted(
        by_effect.items(), key=lambda kv: (kv[1][0], kv[1][1]), reverse=True
    )
    chosen = eff_sorted[0][1][2]

    return {
        "effect": chosen["effect"],
        "params": chosen.get("params") or {},
        "confidence": float(chosen["score"]),
        "candidates": top,
    }

