# Init
from .base import BaseStrategy
from .isa import IsaStrategy
from .fourier import FourierStrategy
from .turtle import TurtleStrategy
from .grandmaster import GrandmasterStrategy  # <--- 1. Import the class

STRATEGIES = {
    "isa": IsaStrategy,
    "fourier": FourierStrategy,
    "turtle": TurtleStrategy,
    "grandmaster": GrandmasterStrategy,       # <--- 2. Register the key
}
