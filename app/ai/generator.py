"""Fitness-plan generation.

Two backends:

* **Gemini** (when a valid ``GEMINI_API_KEY`` is configured) - calls the
  Generative Language REST API with ``httpx`` and expects JSON back.
* **Demo** (default) - a fully offline, deterministic generator that computes
  calories/macros (Mifflin-St Jeor + activity factor) and builds a weekly
  workout split. This keeps the app runnable with no API key.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from .. import config
from ..schemas import PlanRequest

# --------------------------------------------------------------------------- #
# Reference data
# --------------------------------------------------------------------------- #

_ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

_GOAL_LABELS = {
    "lose_weight": "Lose weight",
    "build_muscle": "Build muscle",
    "maintain": "Maintain fitness",
    "improve_endurance": "Improve endurance",
}

# Weekly split templates keyed by (goal-ish focus, days_per_week).
_SPLITS = {
    1: ["Full body"],
    2: ["Upper body", "Lower body"],
    3: ["Push", "Pull", "Legs"],
    4: ["Upper body", "Lower body", "Push", "Pull"],
    5: ["Push", "Pull", "Legs", "Upper body", "Conditioning"],
    6: ["Push", "Pull", "Legs", "Push", "Pull", "Legs"],
    7: ["Push", "Pull", "Legs", "Upper body", "Lower body", "Conditioning", "Active recovery"],
}

_EXERCISES = {
    "Full body": ["Goblet squat", "Push-up", "Bent-over row", "Plank", "Glute bridge"],
    "Upper body": ["Bench/floor press", "Bent-over row", "Overhead press", "Bicep curl", "Tricep dip"],
    "Lower body": ["Back/goblet squat", "Romanian deadlift", "Walking lunge", "Calf raise", "Hip thrust"],
    "Push": ["Bench/floor press", "Overhead press", "Incline press", "Lateral raise", "Tricep extension"],
    "Pull": ["Deadlift", "Bent-over row", "Lat pulldown/pull-up", "Face pull", "Bicep curl"],
    "Legs": ["Back/goblet squat", "Romanian deadlift", "Leg press/step-up", "Walking lunge", "Calf raise"],
    "Conditioning": ["Rowing intervals", "Kettlebell swing", "Burpee", "Mountain climber", "Jump rope"],
    "Active recovery": ["Brisk walk", "Mobility flow", "Light cycling", "Stretching", "Foam rolling"],
}

_EQUIPMENT_NOTE = {
    "none": "Bodyweight-only substitutions where equipment is listed.",
    "basic": "Assumes dumbbells/resistance bands are available.",
    "full_gym": "Assumes access to a full gym (barbells, machines, cables).",
}


# --------------------------------------------------------------------------- #
# Demo (offline) generator
# --------------------------------------------------------------------------- #

def _bmr(req: PlanRequest) -> float:
    """Mifflin-St Jeor basal metabolic rate."""
    base = 10 * req.weight_kg + 6.25 * req.height_cm - 5 * req.age
    if req.sex == "male":
        return base + 5
    if req.sex == "female":
        return base - 161
    return base - 78  # midpoint for "other"


def _macros(calories: int, goal: str, weight_kg: float) -> dict[str, int]:
    """Protein/fat/carb split in grams."""
    protein_per_kg = 2.0 if goal in {"build_muscle", "lose_weight"} else 1.6
    protein_g = round(protein_per_kg * weight_kg)
    fat_g = round((0.25 * calories) / 9)
    carb_cal = max(calories - (protein_g * 4 + fat_g * 9), 0)
    carb_g = round(carb_cal / 4)
    return {"protein_g": protein_g, "fat_g": fat_g, "carb_g": carb_g}


def _meals(calories: int, dietary_pref: str) -> list[dict[str, str]]:
    proteins = {
        "omnivore": ["eggs", "chicken breast", "Greek yogurt", "lean beef", "white fish"],
        "vegetarian": ["eggs", "paneer", "Greek yogurt", "lentils", "cottage cheese"],
        "vegan": ["tofu", "tempeh", "lentils", "chickpeas", "edamame"],
        "pescatarian": ["eggs", "salmon", "tuna", "shrimp", "Greek yogurt"],
    }[dietary_pref]
    split = {"Breakfast": 0.25, "Lunch": 0.35, "Dinner": 0.30, "Snack": 0.10}
    meals = []
    for i, (meal, frac) in enumerate(split.items()):
        meals.append(
            {
                "meal": meal,
                "target_calories": str(round(calories * frac)),
                "idea": f"{proteins[i % len(proteins)].capitalize()} with whole grains and vegetables",
            }
        )
    return meals


def _demo_plan(req: PlanRequest) -> dict[str, Any]:
    bmr = _bmr(req)
    tdee = bmr * _ACTIVITY_FACTORS[req.activity_level]

    adjust = {
        "lose_weight": -0.20,
        "build_muscle": +0.12,
        "maintain": 0.0,
        "improve_endurance": +0.05,
    }[req.goal]
    calories = max(round(tdee * (1 + adjust)), 1200)

    bmi = round(req.weight_kg / ((req.height_cm / 100) ** 2), 1)

    split = _SPLITS[req.days_per_week]
    days = []
    for i, focus in enumerate(split, start=1):
        exercises = _EXERCISES[focus]
        sets_reps = "20-30 min steady + intervals" if focus in {"Conditioning", "Active recovery"} else "3-4 sets x 8-12 reps"
        days.append(
            {
                "day": f"Day {i}",
                "focus": focus,
                "exercises": exercises,
                "prescription": sets_reps,
            }
        )

    return {
        "summary": {
            "name": req.name,
            "goal": _GOAL_LABELS[req.goal],
            "bmi": bmi,
            "bmr_kcal": round(bmr),
            "tdee_kcal": round(tdee),
            "target_calories_kcal": calories,
            "days_per_week": req.days_per_week,
            "note": "Estimates for general guidance only - not medical advice.",
        },
        "workout": {
            "split": split,
            "equipment_note": _EQUIPMENT_NOTE[req.equipment],
            "days": days,
            "warmup": "5-10 min light cardio + dynamic mobility before each session.",
        },
        "nutrition": {
            "target_calories_kcal": calories,
            "macros": _macros(calories, req.goal, req.weight_kg),
            "dietary_pref": req.dietary_pref,
            "hydration": "Aim for 30-40 ml of water per kg of bodyweight daily.",
            "sample_day": _meals(calories, req.dietary_pref),
        },
    }


# --------------------------------------------------------------------------- #
# Gemini generator
# --------------------------------------------------------------------------- #

_PROMPT = """You are FitBuddy, a certified fitness and nutrition coach.
Create a personalized plan for this person and return ONLY valid JSON matching
exactly this shape (no markdown, no commentary):

{{
  "summary": {{"name": str, "goal": str, "bmi": number, "bmr_kcal": number,
               "tdee_kcal": number, "target_calories_kcal": number,
               "days_per_week": number, "note": str}},
  "workout": {{"split": [str], "equipment_note": str,
               "days": [{{"day": str, "focus": str, "exercises": [str],
                          "prescription": str}}],
               "warmup": str}},
  "nutrition": {{"target_calories_kcal": number,
                 "macros": {{"protein_g": number, "fat_g": number, "carb_g": number}},
                 "dietary_pref": str, "hydration": str,
                 "sample_day": [{{"meal": str, "target_calories": str, "idea": str}}]}}
}}

Person profile (JSON):
{profile}
"""


async def _gemini_plan(req: PlanRequest) -> dict[str, Any]:
    model = config.WORKOUT_MODEL
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={config.GEMINI_API_KEY}"
    )
    payload = {
        "contents": [
            {"parts": [{"text": _PROMPT.format(profile=req.model_dump_json())}]}
        ],
        "generationConfig": {"response_mime_type": "application/json"},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #

async def generate_plan(req: PlanRequest) -> tuple[dict[str, Any], str]:
    """Return ``(plan, source)`` where source is ``"gemini"`` or ``"demo"``.

    Falls back to the offline demo generator if the AI backend is unavailable
    or the API call fails for any reason.
    """
    if config.ai_available():
        try:
            plan = await _gemini_plan(req)
            return plan, "gemini"
        except Exception:
            # Any failure (bad key, wrong model, network, malformed JSON) -
            # degrade gracefully to the offline generator.
            return _demo_plan(req), "demo"
    return _demo_plan(req), "demo"
