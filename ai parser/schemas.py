from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from intents import Intent


class Destination(BaseModel):
    city: str = "Paris"
    country: str = "FR"


class Dates(BaseModel):
    start_date: Optional[str] = None  # ISO8601 string (YYYY-MM-DD) or null
    end_date: Optional[str] = None
    days: Optional[int] = Field(default=None, ge=1)
    source: Literal["explicit", "missing"] = "missing"


class Party(BaseModel):
    adult: int = Field(default=0, ge=0)
    highschool: int = Field(default=0, ge=0)
    middleschool: int = Field(default=0, ge=0)
    elementary: int = Field(default=0, ge=0)
    toddler: int = Field(default=0, ge=0)
    trip_style: Literal["solo", "couple", "friends", "family", "unknown"] = "unknown"

    @property
    def total(self) -> int:
        return (
            self.adult
            + self.highschool
            + self.middleschool
            + self.elementary
            + self.toddler
        )


class Lodging(BaseModel):
    text: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class Mobility(BaseModel):
    travel_mode: Literal["walk", "transit", "both"] = "both"
    optimize: Literal["min_time", "min_transfers"] = "min_time"
    max_walk_km_per_day: Optional[int] = None
    wheelchair: bool = False
    stroller: bool = False


class Pace(BaseModel):
    level: Literal["slow", "normal", "fast"] = "normal"
    max_places_per_day: int = 6


class Budget(BaseModel):
    currency: str = "EUR"
    budget_total: Optional[int] = None
    budget_per_day: Optional[int] = None
    budget_mode: Literal["save", "normal", "flex"] = "normal"


class PreferencesWeights(BaseModel):
    cafe: float = 0.5
    museum: float = 0.5
    park: float = 0.5
    shopping: float = 0.5
    night_view: float = 0.5


class Preferences(BaseModel):
    weights: PreferencesWeights = Field(default_factory=PreferencesWeights)
    themes: List[str] = Field(default_factory=list)
    must_include: List[str] = Field(default_factory=list)
    must_avoid: List[str] = Field(default_factory=list)


class Constraints(BaseModel):
    museum_per_day: Optional[int] = None
    indoor_focus: bool = False
    rainy_plan: bool = False


class OutputOptions(BaseModel):
    include_map: bool = True
    include_excel: bool = True
    include_cost: bool = True


class Clarify(BaseModel):
    needed: bool = False
    missing_fields: List[str] = Field(default_factory=list)


class CreatePlanPayload(BaseModel):
    intent: Literal["CREATE_PLAN"] = Intent.CREATE_PLAN.value
    destination: Destination = Field(default_factory=Destination)
    dates: Dates = Field(default_factory=Dates)
    party: Party = Field(default_factory=Party)
    lodging: Lodging = Field(default_factory=Lodging)
    mobility: Mobility = Field(default_factory=Mobility)
    pace: Pace = Field(default_factory=Pace)
    budget: Budget = Field(default_factory=Budget)
    preferences: Preferences = Field(default_factory=Preferences)
    constraints: Constraints = Field(default_factory=Constraints)
    output: OutputOptions = Field(default_factory=OutputOptions)
    clarify: Clarify = Field(default_factory=Clarify)


class Operation(BaseModel):
    op: Literal[
        "add",
        "remove",
        "replace",
        "swap",
        "move",
        "set_constraint",
        "set_pace",
        "set_mobility",
        "set_quantity",
    ]
    target_day: Optional[int] = Field(default=None, ge=1)
    target_slot: Optional[Literal["morning", "lunch", "afternoon", "dinner", "night"]] = None
    swap_slots: Optional[List[Literal["morning", "lunch", "afternoon", "dinner", "night"]]] = None
    category: Optional[str] = None
    place_name: Optional[str] = None
    quantity: Optional[int] = Field(default=None, ge=1)
    from_quantity: Optional[int] = Field(default=None, ge=1)
    to_quantity: Optional[int] = Field(default=None, ge=1)
    constraints_patch: Optional[Dict[str, Any]] = None
    pace: Optional[Literal["slow", "normal", "fast"]] = None
    mobility: Optional[Dict[str, Any]] = None


class ModifyPlanPayload(BaseModel):
    intent: Literal["MODIFY_PLAN"] = Intent.MODIFY_PLAN.value
    trip_id: Optional[str] = None
    operations: List[Operation] = Field(default_factory=list)
    clarify: Clarify = Field(default_factory=Clarify)


class AgentRunRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class AgentRunResponse(BaseModel):
    status: Literal["ASK", "DONE", "ERROR"]
    intent: str
    trip_id: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    clarify: Clarify = Field(default_factory=Clarify)
