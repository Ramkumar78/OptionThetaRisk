# Init
from .base import BaseStrategy
from .isa import IsaStrategy
from .fourier import FourierStrategy
from .turtle import TurtleStrategy
from .grandmaster_screener import GrandmasterScreener

STRATEGIES = {
    "isa": IsaStrategy,
    "fourier": FourierStrategy,
    "turtle": TurtleStrategy,
    "grandmaster": GrandmasterScreener,
}
