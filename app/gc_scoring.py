from dataclasses import dataclass


@dataclass
class LeadScore:
    company: str
    role: str
    confidence: int
    evidence: str


def calculate_confidence(source_type: str) -> int:
    scores = {
        "developer": 100,
        "contractor": 100,
        "press": 80,
        "permit": 60,
        "linkedin": 40,
        "rumor": 20,
    }

    return scores.get(source_type.lower(), 0)
