"""Request/response models for the plan API."""

from typing import Literal

from pydantic import BaseModel, Field

Goal = Literal["lose_weight", "build_muscle", "maintain", "improve_endurance"]
Sex = Literal["male", "female", "other"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]
DietaryPref = Literal["omnivore", "vegetarian", "vegan", "pescatarian"]
Equipment = Literal["none", "basic", "full_gym"]


class PlanRequest(BaseModel):
    name: str = Field(default="Athlete", max_length=60)
    age: int = Field(ge=13, le=100)
    sex: Sex = "other"
    height_cm: float = Field(ge=100, le=250)
    weight_kg: float = Field(ge=30, le=300)
    goal: Goal = "maintain"
    activity_level: ActivityLevel = "moderate"
    days_per_week: int = Field(default=3, ge=1, le=7)
    dietary_pref: DietaryPref = "omnivore"
    equipment: Equipment = "basic"


class PlanResponse(BaseModel):
    id: int | None = None
    source: str  # "gemini" or "demo"
    summary: dict
    workout: dict
    nutrition: dict
