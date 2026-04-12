from __future__ import annotations

from enum import Enum


class HazardType(str, Enum):
    FLOOD = "flood"
    HURRICANE = "hurricane"
    WILDFIRE = "wildfire"
    EARTHQUAKE = "earthquake"
    CONFLICT_DISPLACEMENT = "conflict_displacement"


class ScenarioStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    LOCKED = "locked"


class ConfidenceLevel(str, Enum):
    BASELINE = "baseline"
    CONDITIONAL = "conditional"
    LOW = "low"
    UNSUPPORTED = "unsupported"


class AssumptionCategory(str, Enum):
    WATER = "water"
    FOOD = "food"
    SHELTER = "shelter"
    NON_FOOD_ITEMS = "non_food_items"
    SANITATION = "sanitation"
    STAFFING = "staffing"
    TRANSPORT = "transport"
    CONTINGENCY = "contingency"
    TIMING = "timing"
    COST = "cost"