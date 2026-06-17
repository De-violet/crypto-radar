"""
Strategy registry. Add new strategies here.

Usage:
    from strategies import get_strategies, STRATEGY_REGISTRY

    # Get strategies by name list (default: all enabled)
    active = get_strategies(["reversal", "breakout"])

    # Get all enabled strategies (controlled by env var STRATEGIES)
    active = get_strategies()  # reads STRATEGIES env, comma-separated
"""
import os

from .base import BaseStrategy, SignalResult
from .breakout import BreakoutStrategy
from .reversal import ReversalStrategy
from .trend_follow import TrendFollowStrategy

# Registry: name -> class
STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    "reversal": ReversalStrategy,
    "breakout": BreakoutStrategy,
    "trend_follow": TrendFollowStrategy,
}


def get_strategies(names: list[str] | None = None) -> list[BaseStrategy]:
    """
    Instantiate strategies by name. If names is None, read STRATEGIES env var
    (comma-separated); if env not set, return ALL registered strategies.

    Examples:
        STRATEGIES="reversal,breakout" -> [ReversalStrategy(), BreakoutStrategy()]
        STRATEGIES="reversal"          -> [ReversalStrategy()]
        STRATEGIES unset               -> all 3 strategies
    """
    if names is None:
        env = os.environ.get("STRATEGIES", "").strip()
        if env:
            names = [s.strip() for s in env.split(",") if s.strip()]
        else:
            names = list(STRATEGY_REGISTRY.keys())

    instances = []
    for name in names:
        cls = STRATEGY_REGISTRY.get(name)
        if cls is None:
            import logging
            logging.getLogger("crypto-radar").warning(
                f"Unknown strategy '{name}', skipping. "
                f"Available: {list(STRATEGY_REGISTRY.keys())}"
            )
            continue
        instances.append(cls())
    return instances


__all__ = [
    "BaseStrategy",
    "SignalResult",
    "STRATEGY_REGISTRY",
    "get_strategies",
    "ReversalStrategy",
    "BreakoutStrategy",
    "TrendFollowStrategy",
]
