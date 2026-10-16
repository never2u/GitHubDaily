"""Token usage and estimated cost of the Claude calls in one run."""

from __future__ import annotations

from collections import defaultdict

# USD per 1M tokens (input, output).
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}
USD_TO_KRW = 1400


class Usage:
    def __init__(self):
        self.tokens = defaultdict(lambda: [0, 0, 0])  # model -> [calls, input, output]

    def record(self, response) -> None:
        model = getattr(response, "model", "unknown")
        u = getattr(response, "usage", None)
        row = self.tokens[model]
        row[0] += 1
        if u is not None:
            row[1] += (getattr(u, "input_tokens", 0) or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0)
            row[2] += getattr(u, "output_tokens", 0) or 0

    def cost(self) -> float:
        total = 0.0
        for model, (_, tin, tout) in self.tokens.items():
            pin, pout = PRICES.get(model, PRICES["claude-opus-5-5"])  # unknown: price high
            total += tin / 1e6 * pin + tout / 1e6 * pout
        return total

    def report(self) -> list[str]:
        if not self.tokens:
            return ["usage: no Claude calls"]
        lines = [f"usage: {m}: {c} calls, {i:,} in / {o:,} out tokens" for m, (c, i, o) in self.tokens.items()]
        usd = self.cost()
        lines.append(f"usage: estimated cost ${usd:.4f} (~{usd * USD_TO_KRW:.0f} KRW) today, "
                     f"~${usd * 30:.2f}/month at this rate")
        return lines
