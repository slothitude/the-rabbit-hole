"""Game theory computational primitives — forecast dimensions per game type."""

GAME_FORECAST_MODELS = {
    "chicken": {
        "dimensions": ["credibility_of_damage_acceptance", "audience_costs", "offramp_availability", "miscalculation_risk"],
        "equilibrium": "brinkmanship until one side blinks",
        "escalation_pattern": "linear then sudden",
        "stabilization_mechanism": "secret backchannel communication",
        "typical_duration": "days to weeks",
        "wildcard_type": "accidental escalation through signaling failure",
    },
    "cheap talk": {
        "dimensions": ["media_amplification", "verifiability", "consensus_fabrication", "cascade_probability"],
        "equilibrium": "talk without action until audience desensitizes",
        "escalation_pattern": "logarithmic — rapid spike then plateau",
        "stabilization_mechanism": "fact-checking, source fatigue",
        "typical_duration": "hours to days",
        "wildcard_type": "leaked proof that converts talk into costly signal",
    },
    "repeated game": {
        "dimensions": ["reputation_preservation", "intra_group_punishment", "coalition_incentives", "grim_trigger_risk"],
        "equilibrium": "tit-for-tat with occasional cooperation",
        "escalation_pattern": "stepwise — each round raises stakes",
        "stabilization_mechanism": "future shadow — actors know they'll meet again",
        "typical_duration": "weeks to months",
        "wildcard_type": "new player enters who doesn't know the history",
    },
    "prisoner's dilemma": {
        "dimensions": ["trust_deficit", "communication_impossibility", "defection_incentive", "enforcement_mechanism"],
        "equilibrium": "mutual defection unless repeated interaction changes incentives",
        "escalation_pattern": "simultaneous then locked",
        "stabilization_mechanism": "third-party enforcement or repeated interaction",
        "typical_duration": "event-driven",
        "wildcard_type": "communication channel opens between prisoners",
    },
    "moral hazard": {
        "dimensions": ["insulation_from_consequences", "risk_transfer", "principal_agent_gap", "regulatory_capture"],
        "equilibrium": "excessive risk until crisis forces restructuring",
        "escalation_pattern": "exponential — hidden until visible",
        "stabilization_mechanism": "crisis forces accountability",
        "typical_duration": "months to years",
        "wildcard_type": "hidden exposure suddenly becomes public",
    },
    "coordination game": {
        "dimensions": ["common_knowledge", "focal_points", "communication_channels", "trust_threshold"],
        "equilibrium": "multiple equilibria — which one gets selected depends on focal points",
        "escalation_pattern": "sudden — tipping point when coordination threshold is reached",
        "stabilization_mechanism": "lock-in after coordination",
        "typical_duration": "variable",
        "wildcard_type": "new focal point emerges that shifts the coordination equilibrium",
    },
}

# Map common LLM game type labels to model keys
GAME_TYPE_ALIASES = {
    "chicken": "chicken",
    "brinkmanship": "chicken",
    "game of chicken": "chicken",
    "cheap talk": "cheap talk",
    "cheap-talk": "cheap talk",
    "signaling": "cheap talk",
    "repeated game": "repeated game",
    "iterated": "repeated game",
    "prisoner's dilemma": "prisoner's dilemma",
    "prisoners dilemma": "prisoner's dilemma",
    "pd game": "prisoner's dilemma",
    "moral hazard": "moral hazard",
    "coordination game": "coordination game",
    "coordination": "coordination game",
    "stag hunt": "coordination game",
    "assurance game": "coordination game",
}


def get_game_model(game_type: str) -> dict | None:
    """Get the forecast model for a game type, resolving aliases."""
    key = GAME_TYPE_ALIASES.get(game_type.lower().strip())
    if key:
        return GAME_FORECAST_MODELS[key]
    return None


def get_game_dimensions_prompt(game_type: str) -> str:
    """Generate game-type-specific forecast prompt section."""
    model = get_game_model(game_type)
    if not model:
        return ""

    dims = ", ".join(d.replace("_", " ").title() for d in model["dimensions"])
    dim_list = "\n".join(f"  - {d}" for d in model["dimensions"])
    return f"""
GAME_TYPE_FORECAST:
Given that this is a {game_type}:
DIMENSION_SCORES: [score each dimension 1-10: {dim_list}]
EXPECTED_EQUILIBRIUM: [{model['equilibrium']}]
ESCALATION_PATTERN: [{model['escalation_pattern']}]
STABILIZATION_MECHANISM: [{model['stabilization_mechanism']}]
GAME_SPECIFIC_WILDCARD: [{model['wildcard_type']}]
DEVIATION_FROM_MODEL: [how is this instance different from the textbook version]
"""
