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

