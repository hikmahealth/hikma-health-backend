from dataclasses import dataclass
from typing import Tuple


@dataclass
class PutOutput:
    uri: str
    hash: Tuple[str, str]
