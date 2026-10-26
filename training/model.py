from __future__ import annotations

import torch
from mahjong_ai.actions import ACTION_COUNT
from mahjong_ai.features import FEATURE_SIZE
from torch import nn


class PolicyValueNet(nn.Module):
    def __init__(self, feature_size: int = FEATURE_SIZE, hidden: int = 256, action_count: int = ACTION_COUNT):
        super().__init__()
        self.feature_size = feature_size
        self.action_count = action_count
        self.encoder = nn.Sequential(
            nn.Linear(feature_size, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
        )
        self.policy = nn.Linear(hidden, action_count)
        self.value = nn.Linear(hidden, 1)

    def forward(self, features: torch.Tensor, mask: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
        encoded = self.encoder(features)
        logits = self.policy(encoded)
        if mask is not None:
            logits = logits.masked_fill(~mask, torch.finfo(logits.dtype).min)
        value = torch.tanh(self.value(encoded)).squeeze(-1)
        return logits, value


class TilePolicyValueNet(PolicyValueNet):
    """Learned shared discard scorer; no ranking rules or heuristic action masks.

    Visible v6 features are unchanged. Sharing tile weights makes structural
    generalisation possible without learning 34 unrelated discard functions.
    """
    def __init__(self, hidden: int = 256):
        super().__init__(hidden=hidden)
        offsets = [0, 34, 68, 102, *range(176, 312, 34), *range(312, 448, 34),
                   *range(448, 584, 34), 593, 635, 669, 703, 737]
        self.register_buffer("tile_indices", torch.tensor([[o+t for o in offsets] for t in range(34)]))
        self.tile_embedding = nn.Parameter(torch.zeros(34, 16))
        self.tile_score = nn.Sequential(nn.Linear(hidden + len(offsets) + 16, 128), nn.ReLU(), nn.Linear(128, 1))
        nn.init.zeros_(self.tile_score[-1].weight)
        nn.init.zeros_(self.tile_score[-1].bias)

    def forward(self, features: torch.Tensor, mask: torch.Tensor | None = None):
        encoded = self.encoder(features)
        local = features[:, self.tile_indices]
        context = encoded.unsqueeze(1).expand(-1, 34, -1)
        embedding = self.tile_embedding.unsqueeze(0).expand(features.shape[0], -1, -1)
        scores = self.tile_score(torch.cat([context, local, embedding], dim=-1)).squeeze(-1)
        base = self.policy(encoded)
        logits = torch.cat([base[:, :12], base[:, 12:46] + scores, base[:, 46:]], dim=1)
        if mask is not None:
            logits = logits.masked_fill(~mask, torch.finfo(logits.dtype).min)
        # Unbounded critic can represent the actual score/64 return of high-fan wins.
        return logits, self.value(encoded).squeeze(-1)


def model_from_checkpoint(checkpoint: dict) -> PolicyValueNet:
    kind = checkpoint.get("model_kind", "mlp-v1")
    if kind not in ("mlp-v1", "tile-shared-v1"):
        raise ValueError(f"unsupported model architecture: {kind}")
    cls = TilePolicyValueNet if kind == "tile-shared-v1" else PolicyValueNet
    return cls(hidden=int(checkpoint["hidden"]))

