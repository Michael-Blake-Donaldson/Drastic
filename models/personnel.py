from dataclasses import dataclass

@dataclass
class Personnel:
    role: str
    number: int
    pay_rate: float  # per hour
    volunteer: bool