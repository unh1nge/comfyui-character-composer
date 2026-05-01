import glob
import json
import os
import random
import re

# Modifiers and Negative terms stay here as they are functional "constants" for the engine
DEFAULT_MODIFIERS = [
    "gravure", "photorealistic", "soft lighting", "high detail", "8k",
    "ultra realistic", "cinematic composition", "sensual mood", "soft focus",
    "warm glow", "intimate atmosphere", "cute aesthetic", "glossy aesthetic",
    "tropical glamour", "mythic elegance", "moody shadows"
]

NEGATIVE_PROMPT_TERMS = (
    "no twins, no conjoined limbs, no siamese twins, no deformities, "
    "no mutations, no extra limbs, no abnormalities, bad anatomy, bad proportions, "
    "no futanari, no boygirl, no girlboy, no hermaphrodite, no male anatomy on female body"
)

BAD_PROMPT_TERMS = [
    "twin", "twins", "siamese", "conjoined", "mutation", "mutant",
    "abnormal", "abnormalities", "deform", "deformity", "deformities",
    "extra limb", "extra limbs", "two heads", "two bodies", "two faces", "abomination"
]

FORBIDDEN_GENDER_TERMS = [
    "boygirl", "girlboy", "futanari", "futa", "hermaphrodite", "dickgirl",
    "male-bodied female", "male anatomy", "female with cock", "female body with penis",
    "cock girl", "eggplant girl"
]

def _remove_futanari_terms(prompt: str) -> str:
    sanitized = prompt
    for term in FORBIDDEN_GENDER_TERMS:
        sanitized = re.sub(rf"\b{re.escape(term)}\b", "", sanitized, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", sanitized).strip()


def _cleanup_removed_prompt_text(prompt: str) -> str:
    cleaned = re.sub(r"\s*,\s*", ", ", prompt)
    cleaned = re.sub(
        r"(^|\s)(?:and|or|with)(?=\s*(?:,|$))",
        r"\1",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:and|or|with)\b(?:\s+\b(?:and|or|with)\b)+",
        "and",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
    return cleaned


def _remove_tag_phrase(prompt: str, tag: str) -> str:
    escaped_tag = re.escape(tag)
    cleaned = re.sub(
        rf"(?:\b[\w'\-]+\s+){{0,2}}{escaped_tag}\b",
        "",
        prompt,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

# The UI_LAYOUT is the ONLY place where keys are defined. 
# This tells the script which dropdowns to create.
UI_LAYOUT = [
    ("--- CORE CREATIVE ---", ["preset", "subject", "gender", "outfit", "pose", "interaction", "setting"]),
    ("--- CHARACTER LOOK ---", ["body_type", "chest_size", "age", "ethnicity", "fantasy_race", "hair_color", "hair_style", "eye_color", "expression", "makeup"]),
    ("--- CAMERA & FRAMING ---", ["focus", "camera_angle", "camera_gear"]),
    ("--- STYLE & SCENE ---", ["vibe", "style_adjective", "creative_twist", "background_mood", "atmosphere"]),
    ("--- OPTIONAL EXTRAS ---", ["accessory", "prop", "background_prop"])
]

# Flatten the layout to get a master list of all keys the engine should handle
MASTER_KEYS = [key for _, keys in UI_LAYOUT for key in keys]

# Keys that define a character's visual identity/look
LOOK_KEYS = [
    "subject",
    "gender",
    "body_type",
    "chest_size",
    "hair_color",
    "hair_style",
    "eye_color",
    "makeup",
    "outfit",
    "fantasy_race",
    "ethnicity",
]

GENDER_OPTIONS = ["male", "female"]
DETAIL_LEVEL_OPTIONS = ["minimal", "balanced", "rich"]
STYLE_STRENGTH_OPTIONS = ["subtle", "balanced", "strong"]
COMPOSITION_MODE_OPTIONS = ["auto", "solo portrait", "fashion", "paired", "close-up", "full body", "winter", "fantasy"]
SUBJECT_COUNT_OPTIONS = ["1", "2", "3", "4", "group"]
SMART_PRESET_OPTIONS = ["none", "safe portrait", "high detail character", "winter fashion", "beach glam", "neon nightlife", "romantic boudoir", "fantasy ethereal", "studio editorial", "paired cinematic", "simple anatomy-safe"]
GENERATION_PROFILE_OPTIONS = ["custom", "clean portrait", "expressive fashion", "cinematic scene", "safe paired", "winter character", "beach scene", "fantasy character"]

PRESET_TRAITS = {
    "gravure": {
        "expression": "sultry",
        "makeup": "glossy lips",
        "camera_angle": "three-quarter shot",
        "vibe": "modern",
        "outfit": "bikini",
        "atmosphere": "soft sunlight",
    },
    "editorial": {
        "expression": "confident",
        "makeup": "bold makeup",
        "camera_angle": "close-up portrait",
        "vibe": "modern",
        "outfit": "elegant dress",
        "atmosphere": "studio lighting",
    },
    "boudoir": {
        "expression": "dreamy",
        "makeup": "soft glam",
        "camera_angle": "close-up portrait",
        "vibe": "vintage",
        "outfit": "lingerie",
        "atmosphere": "magazine glow",
    },
    "retro": {
        "expression": "playful",
        "makeup": "dewy skin",
        "camera_angle": "full body shot",
        "vibe": "vintage",
        "outfit": "retro swimsuit",
        "atmosphere": "golden hour",
    },
    "kawaii": {
        "expression": "playful",
        "makeup": "rosy cheeks",
        "camera_angle": "mid shot",
        "vibe": "kawaii",
        "outfit": "oversized sweater",
        "atmosphere": "bright morning light",
    },
    "tropical": {
        "expression": "playful",
        "makeup": "dewy skin",
        "camera_angle": "full body shot",
        "vibe": "summer vacation",
        "outfit": "tropical sarong",
        "atmosphere": "tropical heat",
    },
}

SMART_PRESET_DEFAULTS = {
    "safe portrait": {"composition_mode": "solo portrait", "detail_level": "minimal", "style_strength": "subtle", "subject_count": "1"},
    "high detail character": {"composition_mode": "fashion", "detail_level": "rich", "style_strength": "balanced", "subject_count": "1"},
    "winter fashion": {"composition_mode": "winter", "detail_level": "balanced", "style_strength": "balanced", "subject_count": "1"},
    "beach glam": {"composition_mode": "full body", "detail_level": "balanced", "style_strength": "strong", "subject_count": "1"},
    "neon nightlife": {"composition_mode": "fashion", "detail_level": "rich", "style_strength": "strong", "subject_count": "1"},
    "romantic boudoir": {"composition_mode": "solo portrait", "detail_level": "balanced", "style_strength": "balanced", "subject_count": "1"},
    "fantasy ethereal": {"composition_mode": "fantasy", "detail_level": "rich", "style_strength": "strong", "subject_count": "1"},
    "studio editorial": {"composition_mode": "fashion", "detail_level": "balanced", "style_strength": "subtle", "subject_count": "1"},
    "paired cinematic": {"composition_mode": "paired", "detail_level": "rich", "style_strength": "strong", "subject_count": "2"},
    "simple anatomy-safe": {"composition_mode": "full body", "detail_level": "minimal", "style_strength": "subtle", "subject_count": "1"},
}

GENERATION_PROFILE_DEFAULTS = {
    "clean portrait": {
        "smart_preset": "safe portrait",
        "composition_mode": "solo portrait",
        "subject_count": "1",
        "detail_level": "minimal",
        "style_strength": "subtle",
    },
    "expressive fashion": {
        "smart_preset": "high detail character",
        "composition_mode": "fashion",
        "subject_count": "1",
        "detail_level": "rich",
        "style_strength": "balanced",
    },
    "cinematic scene": {
        "smart_preset": "none",
        "composition_mode": "full body",
        "subject_count": "1",
        "detail_level": "rich",
        "style_strength": "strong",
    },
    "safe paired": {
        "smart_preset": "paired cinematic",
        "composition_mode": "paired",
        "subject_count": "2",
        "detail_level": "minimal",
        "style_strength": "subtle",
    },
    "winter character": {
        "smart_preset": "winter fashion",
        "composition_mode": "winter",
        "subject_count": "1",
        "detail_level": "balanced",
        "style_strength": "balanced",
    },
    "beach scene": {
        "smart_preset": "beach glam",
        "composition_mode": "full body",
        "subject_count": "1",
        "detail_level": "balanced",
        "style_strength": "strong",
    },
    "fantasy character": {
        "smart_preset": "fantasy ethereal",
        "composition_mode": "fantasy",
        "subject_count": "1",
        "detail_level": "balanced",
        "style_strength": "strong",
    },
}

COMPOSITION_MODE_DEFAULTS = {
    "solo portrait": {"camera_angle": "close-up portrait", "focus": "portrait focus"},
    "fashion": {"camera_angle": "full body shot", "focus": "full body focus"},
    "paired": {"camera_angle": "mid shot", "focus": "full body focus"},
    "close-up": {"camera_angle": "close-up portrait", "focus": "face focus"},
    "full body": {"camera_angle": "full body shot", "focus": "full body focus"},
    "winter": {"background_mood": "soft light", "atmosphere": "soft sunlight"},
    "fantasy": {"creative_twist": "ethereal", "vibe": "dreamlike"},
}

def _normalize_prompt(prompt: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", prompt.lower())

def _sanitize_prompt(prompt: str) -> str:
    sanitized = prompt
    for term in BAD_PROMPT_TERMS:
        sanitized = re.sub(rf"\b{re.escape(term)}\b", "", sanitized, flags=re.IGNORECASE)
    sanitized = _remove_futanari_terms(sanitized)
    return re.sub(r"\s+", " ", sanitized).strip()

def _is_none_selection(value) -> bool:
    return value is None or str(value).strip().lower() in ("none", "")

DEFAULT_TAG_FILE = "tags.json"

TAG_CACHE = {
    "path": None,
    "mtime": None,
    "data": None,
}

DEFAULT_INTERACTION_SCENE_FAMILIES = {
    "carry": ["lifted", "carry", "arms"],
    "wall": ["wall"],
    "seated": ["spoon", "lap", "seated", "sitting"],
    "dance": ["dance", "dip", "turn"],
    "kiss": ["kiss", "nuzzl", "cheek", "forehead", "tongue", "lip bite"],
    "embrace": ["hug", "embrace", "cuddl", "waist", "shoulder", "hands", "fingers", "bodies together"],
}

DEFAULT_SCENE_COMPATIBLE_POSE_HINTS = {
    "carry": ["one leg raised", "arms up", "leaning forward", "against wall", "standing"],
    "wall": ["against wall", "one leg raised", "looking over shoulder", "standing side view", "hands on hips"],
    "seated": ["sitting", "kneeling", "lying on back", "legs crossed"],
    "dance": ["standing", "one leg raised", "hands on hips", "looking over shoulder"],
    "kiss": ["standing", "leaning forward", "against wall", "looking over shoulder", "hands behind head"],
    "embrace": ["standing", "leaning forward", "kneeling", "sitting", "against wall"],
}

DEFAULT_EXTREME_FOCUS_TERMS = ["close-up", "tight crop", "cleavage focus", "side profile"]
DEFAULT_EXTREME_CAMERA_TERMS = ["close-up", "overhead", "top-down", "pov"]
DEFAULT_COMPLEX_INTERACTION_TERMS = ["lifted", "grinding", "dip", "pressing", "spoon", "dance"]
DEFAULT_COMPLEXITY_LEVEL_TERMS = {
    "high": DEFAULT_COMPLEX_INTERACTION_TERMS,
    "medium": ["kiss", "embrace", "cuddl", "hug", "waist", "shoulder"],
}
DEFAULT_ACCESSORY_DROP_TERMS = ["stockings", "garters", "gloves", "headphones", "scarf"]
DEFAULT_SETTING_DROP_TERMS = ["studio apartment", "indoor set", "balcony"]
DEFAULT_SETTING_RESTRICTED_SCENES = ["carry", "dance"]
DEFAULT_CAMERA_DOWNGRADE = "mid shot"
DEFAULT_DETAIL_BUDGETS = {
    "minimal": {"portrait": 4, "pose": 1, "scene": 2, "style": 1},
    "balanced": {"portrait": 6, "pose": 2, "scene": 4, "style": 2},
    "rich": {"portrait": 8, "pose": 3, "scene": 5, "style": 3},
}
DEFAULT_CATEGORY_WEIGHTS = {
    "subject": 1.2,
    "outfit": 1.12,
    "pose": 1.08,
    "interaction": 1.08,
    "style": 1.0,
    "scene": 1.0,
}
DEFAULT_COMPLEXITY_THRESHOLDS = {"balanced": 8, "high": 11}
DEFAULT_TAG_CONFLICTS = {
    "kokoshnik headdress": ["ushanka fur hat"],
    "ushanka fur hat": ["kokoshnik headdress"],
    "cat ears accessory": ["bunny ears accessory"],
    "bunny ears accessory": ["cat ears accessory"],
    "cat ears": ["bunny ears"],
    "bunny ears": ["cat ears"],
    "winter boots": ["high heels stylish", "high heels on floor"],
    "tall fur boots": ["high heels stylish", "high heels on floor"],
}
DEFAULT_SMART_PRESET_RULES = {
    "winter fashion": {
        "preferred_terms": {
            "outfit": ["fur", "shuba", "winter coat", "snow maiden", "snegurochka"],
            "setting": ["enchanted winter forest", "winter forest", "snow"],
            "background_mood": ["winter glow", "snowfall", "frosted twilight"],
            "atmosphere": ["crisp winter air", "frosty mist", "snowy hush"],
            "hair_color": ["silver", "platinum", "white", "ash blonde"],
            "accessory": ["ushanka", "fur", "winter boots", "kokoshnik"],
            "ethnicity": ["caucasian", "japanese", "korean", "chinese", "vietnamese", "thai", "filipina"],
        },
        "blocked_terms": {
            "setting": ["tropical", "beach", "poolside", "seaside"],
            "background_mood": ["ocean breeze", "golden hour"],
            "atmosphere": ["tropical heat", "humid summer"],
            "prop": ["tropical cocktail", "ice cream"],
        },
    },
    "beach glam": {
        "preferred_terms": {
            "outfit": ["bikini", "swimsuit"],
            "setting": ["beach", "poolside", "cabana", "seaside"],
            "background_mood": ["golden hour", "ocean breeze", "bright morning"],
            "atmosphere": ["soft sunlight", "golden hour", "tropical heat", "humid summer"],
            "hair_color": ["blonde", "honey blonde", "golden blonde", "sunlit"],
            "hair_style": ["beach waves", "wet hair", "loose waves"],
            "accessory": ["seashell", "flower crown"],
        },
        "blocked_terms": {
            "setting": ["winter", "dungeon", "bdsm", "tatami"],
            "background_mood": ["frosted", "moonlit winter"],
            "atmosphere": ["crisp winter", "frosty mist"],
            "accessory": ["ushanka", "kokoshnik", "winter boots"],
        },
    },
    "neon nightlife": {
        "preferred_terms": {
            "setting": ["neon alley", "rooftop bar", "strip club", "penthouse", "love hotel"],
            "background_mood": ["neon", "rainy neon", "dim red", "moody evening"],
            "atmosphere": ["electric night air", "warm cinematic", "intimate lighting"],
            "hair_color": ["black", "blue-black", "deep violet", "red"],
            "makeup": ["bold makeup", "smoky eyes", "glossy lips", "wet-look"],
            "accessory": ["choker", "layered silver chains", "body chain", "spiked choker"],
        },
        "blocked_terms": {
            "setting": ["winter forest", "garden", "beach club", "onsen"],
            "background_mood": ["bright morning", "soft snowfall"],
            "atmosphere": ["crisp winter", "snowy hush"],
            "accessory": ["ushanka", "flower crown"],
        },
    },
    "romantic boudoir": {
        "preferred_terms": {
            "outfit": ["lingerie", "lace", "silk robe", "sheer babydoll"],
            "setting": ["cozy bedroom", "love hotel", "silk bed", "private candlelit suite", "red velvet sofa"],
            "background_mood": ["candlelit", "soft light", "velvet shadows", "magazine glow"],
            "atmosphere": ["romantic candlelit haze", "intimate lighting", "soft backlight"],
            "hair_style": ["loose waves", "bedhead", "wet hair"],
            "accessory": ["lace gloves", "garters", "body chain", "earrings"],
        },
        "blocked_terms": {
            "setting": ["beach", "winter forest", "dungeon", "strip club"],
            "background_mood": ["neon", "snowfall"],
            "accessory": ["ushanka", "winter boots", "cat ears", "bunny ears"],
        },
    },
    "fantasy ethereal": {
        "preferred_terms": {
            "fantasy_race": ["elf", "fairy", "fae", "angel", "celestial", "nymph"],
            "setting": ["moonlit ruins", "enchanted winter forest", "ancient garden", "glowing mist"],
            "background_mood": ["magical haze", "moonlit", "gentle haze"],
            "atmosphere": ["enchanted moonlit mist", "frosty mist", "gentle haze"],
            "hair_color": ["silver", "white", "lavender", "rose gold"],
            "accessory": ["flower crown", "butterfly hair clips", "kokoshnik"],
            "creative_twist": ["ethereal", "moonlit enchantment", "dreamlike haze"],
        },
        "blocked_terms": {
            "setting": ["strip club", "bdsm", "dungeon", "poolside"],
            "background_mood": ["dim red", "sweaty musk"],
            "prop": ["vibrator", "fuckmachine"],
        },
    },
    "studio editorial": {
        "preferred_terms": {
            "setting": ["editorial photo studio", "led light studio", "indoor studio", "seamless backdrop"],
            "background_mood": ["editorial flash", "magazine glow", "soft light"],
            "atmosphere": ["polished studio clarity", "studio lighting"],
            "camera_gear": ["Sony A7R IV", "Canon R5", "85mm lens", "raw photo"],
            "hair_style": ["slick", "short bob", "high ponytail", "long straight"],
            "accessory": ["earrings", "bracelet", "layered silver chains"],
        },
        "blocked_terms": {
            "setting": ["winter forest", "beach", "dungeon", "onsen"],
            "background_mood": ["ocean breeze", "snowfall", "dim red"],
            "prop": ["vibrator", "fuckmachine", "ice cream"],
        },
    },
}


def _is_usable_tag_value(value) -> bool:
    return value is not None and str(value).strip() != ""


def _pick_random_choice(rng: random.Random, values: list[str]) -> str | None:
    usable_values = [value for value in values if _is_usable_tag_value(value)]
    return rng.choice(usable_values) if usable_values else None


def _default_composer_rules() -> dict:
    return {
        "interaction_scene_families": DEFAULT_INTERACTION_SCENE_FAMILIES,
        "scene_compatible_pose_hints": DEFAULT_SCENE_COMPATIBLE_POSE_HINTS,
        "extreme_focus_terms": DEFAULT_EXTREME_FOCUS_TERMS,
        "extreme_camera_terms": DEFAULT_EXTREME_CAMERA_TERMS,
        "complexity_level_terms": DEFAULT_COMPLEXITY_LEVEL_TERMS,
        "accessory_drop_terms": DEFAULT_ACCESSORY_DROP_TERMS,
        "setting_drop_terms": DEFAULT_SETTING_DROP_TERMS,
        "setting_restricted_scenes": DEFAULT_SETTING_RESTRICTED_SCENES,
        "camera_downgrade": DEFAULT_CAMERA_DOWNGRADE,
        "detail_budgets": DEFAULT_DETAIL_BUDGETS,
        "category_weights": DEFAULT_CATEGORY_WEIGHTS,
        "complexity_thresholds": DEFAULT_COMPLEXITY_THRESHOLDS,
    }


def _normalize_composer_rules(raw_rules) -> dict:
    rules = _default_composer_rules()
    if not isinstance(raw_rules, dict):
        return rules

    for key in (
        "interaction_scene_families",
        "scene_compatible_pose_hints",
        "complexity_level_terms",
        "detail_budgets",
        "category_weights",
        "complexity_thresholds",
    ):
        if isinstance(raw_rules.get(key), dict):
            if key in ("interaction_scene_families", "scene_compatible_pose_hints", "complexity_level_terms"):
                rules[key] = {
                    str(name): [str(item) for item in values if _is_usable_tag_value(item)]
                    for name, values in raw_rules[key].items()
                    if isinstance(values, list)
                } or rules[key]
            elif key == "detail_budgets":
                normalized_budgets = {}
                for level, values in raw_rules[key].items():
                    if not isinstance(values, dict):
                        continue
                    normalized_budgets[str(level)] = {
                        str(bucket): int(amount)
                        for bucket, amount in values.items()
                        if isinstance(amount, (int, float))
                    }
                rules[key] = normalized_budgets or rules[key]
            else:
                rules[key] = {
                    str(name): float(value)
                    for name, value in raw_rules[key].items()
                    if isinstance(value, (int, float))
                } or rules[key]

    for key in (
        "extreme_focus_terms",
        "extreme_camera_terms",
        "accessory_drop_terms",
        "setting_drop_terms",
        "setting_restricted_scenes",
    ):
        if isinstance(raw_rules.get(key), list):
            rules[key] = [str(item) for item in raw_rules[key] if _is_usable_tag_value(item)] or rules[key]

    if _is_usable_tag_value(raw_rules.get("camera_downgrade")):
        rules["camera_downgrade"] = str(raw_rules["camera_downgrade"])

    return rules


def _infer_interaction_scene_family(interaction: str | None, rules: dict) -> str | None:
    if not interaction:
        return None
    lowered = interaction.lower()
    for family, markers in rules["interaction_scene_families"].items():
        if any(marker in lowered for marker in markers):
            return family
    return "embrace"


def _pose_matches_scene_family(pose: str | None, family: str | None, rules: dict) -> bool:
    if not pose or not family:
        return True
    lowered_pose = pose.lower()
    return any(marker in lowered_pose for marker in rules["scene_compatible_pose_hints"].get(family, []))


def _interaction_complexity(interaction: str | None, rules: dict) -> str:
    if not interaction:
        return "none"
    lowered = interaction.lower()
    for level in ("high", "medium"):
        if any(term in lowered for term in rules["complexity_level_terms"].get(level, [])):
            return level
    return "low"


def _normalize_tag_aliases(raw_aliases) -> dict[str, dict[str, str]]:
    normalized = {}
    if not isinstance(raw_aliases, dict):
        return normalized
    for key, aliases in raw_aliases.items():
        if not isinstance(aliases, dict):
            continue
        normalized[str(key)] = {
            str(alias).lower(): str(target)
            for alias, target in aliases.items()
            if _is_usable_tag_value(alias) and _is_usable_tag_value(target)
        }
    return normalized


def _normalize_tag_conflicts(raw_conflicts) -> dict[str, list[str]]:
    conflicts = dict(DEFAULT_TAG_CONFLICTS)
    if not isinstance(raw_conflicts, dict):
        return conflicts
    for key, values in raw_conflicts.items():
        if not _is_usable_tag_value(key) or not isinstance(values, list):
            continue
        conflicts[str(key)] = [str(value) for value in values if _is_usable_tag_value(value)]
    return conflicts


def _normalize_smart_preset_rules(raw_rules) -> dict:
    normalized = {}
    base_rules = DEFAULT_SMART_PRESET_RULES
    source = raw_rules if isinstance(raw_rules, dict) else {}
    preset_names = set(base_rules.keys()) | set(source.keys())
    for preset_name in preset_names:
        combined = {"preferred_terms": {}, "blocked_terms": {}}
        for bucket in ("preferred_terms", "blocked_terms"):
            base_bucket = base_rules.get(preset_name, {}).get(bucket, {})
            source_bucket = source.get(preset_name, {}).get(bucket, {}) if isinstance(source.get(preset_name), dict) else {}
            merged_keys = set(base_bucket.keys()) | set(source_bucket.keys())
            for key in merged_keys:
                values = source_bucket.get(key, base_bucket.get(key, []))
                if isinstance(values, list):
                    combined[bucket][str(key)] = [str(v) for v in values if _is_usable_tag_value(v)]
        normalized[str(preset_name)] = combined
    return normalized


def _search_keyword(prompt: str, choices: list[str], aliases: dict[str, str] | None = None) -> str | None:
    normalized = _normalize_prompt(prompt)
    alias_map = aliases or {}
    search_terms = [(choice, choice) for choice in choices]
    search_terms.extend((alias, target) for alias, target in alias_map.items())
    for term, target in sorted(search_terms, key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"\b{re.escape(term.lower())}\b", normalized):
            return target
    return None


def _weight_text(text: str, weight: float) -> str:
    if not text or abs(weight - 1.0) < 0.01:
        return text
    return f"({text}:{weight:.2f})"


def _select_preferred_value(options: list[str], preferred_values: list[str]) -> str | None:
    for preferred in preferred_values:
        for option in options:
            if option == preferred or preferred.lower() in option.lower():
                return option
    return None


def _select_from_terms(options: list[str], preferred_terms: list[str], rng: random.Random, random_pick: bool = False) -> str | None:
    matches = [
        option for option in options
        if any(term.lower() in option.lower() for term in preferred_terms)
    ]
    if not matches:
        return None
    return rng.choice(matches) if random_pick else matches[0]


def _resolve_preset_name(preset_value: str | None) -> str | None:
    if not preset_value:
        return None
    lowered = preset_value.lower()
    for preset_key in PRESET_TRAITS:
        if lowered == preset_key or preset_key in lowered:
            return preset_key
    return preset_value if preset_value in PRESET_TRAITS else None


def _apply_smart_preset_preferences(final_choices: dict, tag_data: dict, smart_preset_rules: dict, smart_preset: str, rng: random.Random) -> dict:
    biased = dict(final_choices)
    preset_rule = smart_preset_rules.get(smart_preset, {})
    preferred_terms = preset_rule.get("preferred_terms", {})
    random_pick_keys = {"outfit", "ethnicity", "hair_color", "hair_style", "accessory"}
    for key, terms in preferred_terms.items():
        if biased.get(key):
            continue
        selected = _select_from_terms(tag_data.get(key, []), terms, rng, random_pick=(key in random_pick_keys))
        if selected:
            biased[key] = selected
    return biased


def _apply_smart_preset_blocklist(final_choices: dict, smart_preset_rules: dict, smart_preset: str, dropped_traits: list[str]) -> dict:
    sanitized = dict(final_choices)
    preset_rule = smart_preset_rules.get(smart_preset, {})
    blocked_terms = preset_rule.get("blocked_terms", {})
    for key, terms in blocked_terms.items():
        value = sanitized.get(key)
        if value and any(term.lower() in str(value).lower() for term in terms):
            dropped_traits.append(f"{key}: {value} (blocked by {smart_preset} preset)")
            sanitized[key] = None
    return sanitized


def _apply_mode_biases(final_choices: dict, tag_data: dict, smart_preset_rules: dict, composition_mode: str, smart_preset: str, style_strength: str, subject_count: str, fill_auto_traits: bool, rng: random.Random) -> dict:
    biased = dict(final_choices)
    mode_defaults = COMPOSITION_MODE_DEFAULTS.get(composition_mode, {})
    for key, value in mode_defaults.items():
        if not biased.get(key):
            preferred_value = _select_preferred_value(tag_data.get(key, []), [value])
            if preferred_value:
                biased[key] = preferred_value
    biased = _apply_smart_preset_preferences(biased, tag_data, smart_preset_rules, smart_preset, rng)

    if smart_preset == "paired cinematic" and not biased.get("interaction"):
        preferred_interaction = _select_preferred_value(tag_data.get("interaction", []), ["passionate embrace", "hugging", "kissing"])
        if preferred_interaction:
            biased["interaction"] = preferred_interaction

    if composition_mode == "paired" and subject_count == "1" and biased.get("interaction") and fill_auto_traits:
        biased["interaction"] = None

    if smart_preset in ("safe portrait", "simple anatomy-safe"):
        for key in ("prop", "interaction"):
            if fill_auto_traits and key in biased:
                biased[key] = None

    if style_strength == "subtle" and not biased.get("creative_twist"):
        biased["creative_twist"] = None

    return biased


def _apply_tag_conflicts(final_choices: dict, tag_conflicts: dict[str, list[str]], dropped_traits: list[str]) -> dict:
    sanitized = dict(final_choices)
    selected_items = [(key, value) for key, value in sanitized.items() if value]
    priority_order = ["subject", "gender", "outfit", "pose", "interaction", "setting", "accessory", "prop"]
    priority_map = {name: index for index, name in enumerate(priority_order)}
    selected_items.sort(key=lambda item: priority_map.get(item[0], 999))

    kept_values: dict[str, str] = {}
    for key, value in selected_items:
        conflicts = tag_conflicts.get(value, [])
        if any(conflict in kept_values.values() for conflict in conflicts):
            sanitized[key] = None
            dropped_traits.append(f"{key}: {value} (conflicts with higher-priority selection)")
            continue
        kept_values[key] = value
    return sanitized


def _calculate_chaos_score(final_choices: dict, subject_count: str, interaction_complexity: str) -> int:
    active_count = sum(1 for value in final_choices.values() if value)
    score = active_count
    if subject_count == "2":
        score += 2
    elif subject_count == "3":
        score += 3
    elif subject_count == "4":
        score += 4
    elif subject_count == "group":
        score += 5
    if interaction_complexity == "medium":
        score += 2
    elif interaction_complexity == "high":
        score += 4
    return score


def _apply_complexity_guard(final_choices: dict, rules: dict, detail_level: str, style_strength: str, chaos_score: int, dropped_traits: list[str]) -> dict:
    sanitized = dict(final_choices)
    thresholds = rules["complexity_thresholds"]
    if chaos_score < thresholds.get("balanced", 8):
        return sanitized

    low_priority_drop_order = ["prop", "background_prop", "accessory", "creative_twist", "background_mood", "style_adjective", "atmosphere"]
    if style_strength == "strong":
        low_priority_drop_order = ["prop", "background_prop", "accessory", "background_mood", "atmosphere"] + [key for key in low_priority_drop_order if key not in ("prop", "background_prop", "accessory", "background_mood", "atmosphere")]

    limit = thresholds.get("high", 11)
    score = chaos_score
    for key in low_priority_drop_order:
        if score <= limit:
            break
        if sanitized.get(key):
            dropped_traits.append(f"{key}: {sanitized[key]} (trimmed by complexity guard)")
            sanitized[key] = None
            score -= 1 if detail_level != "minimal" else 2
    return sanitized


def _sanitize_scene_conflicts(final_choices: dict, rules: dict) -> tuple[dict, list[str], dict]:
    sanitized = dict(final_choices)
    dropped_traits: list[str] = []
    interaction = sanitized.get("pose_x")
    if not interaction:
        interaction = sanitized.get("interaction")
    if not interaction:
        return sanitized, dropped_traits, {"scene_family": None, "interaction_complexity": "none"}

    scene_family = _infer_interaction_scene_family(interaction, rules)
    complexity = _interaction_complexity(interaction, rules)

    pose = sanitized.get("pose")
    if pose and not _pose_matches_scene_family(pose, scene_family, rules):
        dropped_traits.append(f"pose: {pose} (not compatible with {scene_family} interaction)")
        sanitized["pose"] = None

    focus = sanitized.get("focus")
    if focus and any(term in focus.lower() for term in rules["extreme_focus_terms"]):
        dropped_traits.append(f"focus: {focus} (too extreme for active interaction)")
        sanitized["focus"] = None

    camera_angle = sanitized.get("camera_angle")
    if complexity == "high" and camera_angle and any(term in camera_angle.lower() for term in rules["extreme_camera_terms"]):
        dropped_traits.append(f"camera_angle: {camera_angle} -> {rules['camera_downgrade']} (interaction too complex)")
        sanitized["camera_angle"] = rules["camera_downgrade"]

    if complexity == "high":
        sanitized["prop"] = None
        if final_choices.get("prop"):
            dropped_traits.append(f"prop: {final_choices['prop']} (high-complexity interaction)")
        if sanitized.get("background_prop"):
            dropped_traits.append(f"background_prop: {sanitized['background_prop']} (high-complexity interaction)")
            sanitized["background_prop"] = None
        if sanitized.get("accessory"):
            accessory_text = sanitized["accessory"].lower()
            if any(term in accessory_text for term in rules["accessory_drop_terms"]):
                dropped_traits.append(f"accessory: {sanitized['accessory']} (too unstable for high-complexity interaction)")
                sanitized["accessory"] = None

    if complexity in ("medium", "high") and sanitized.get("setting"):
        setting_text = sanitized["setting"].lower()
        if any(term in setting_text for term in rules["setting_drop_terms"]) and scene_family in rules["setting_restricted_scenes"]:
            dropped_traits.append(f"setting: {sanitized['setting']} (restricted for {scene_family} interaction)")
            sanitized["setting"] = None

    return sanitized, dropped_traits, {"scene_family": scene_family, "interaction_complexity": complexity}


def _resolve_tag_file_path(tag_file: str) -> str:
    if not tag_file:
        return os.path.join(os.path.dirname(__file__), DEFAULT_TAG_FILE)
    if os.path.isabs(tag_file):
        return tag_file
    return os.path.join(os.path.dirname(__file__), tag_file)


def _find_tags_json_files() -> list[str]:
    node_dir = os.path.dirname(__file__)
    json_files = glob.glob(os.path.join(node_dir, "*.json"))
    tag_files = [os.path.basename(f) for f in json_files if "tag" in os.path.basename(f).lower()]
    return sorted(tag_files)


def _build_source_tag_options(tag_files: list[str]) -> dict[str, list[str]]:
    tag_options = {key: (GENDER_OPTIONS.copy() if key == "gender" else []) for key in MASTER_KEYS}
    for tag_file in tag_files:
        data = _get_json_tags(tag_file)
        for key, values in data.items():
            if key not in tag_options or key == "gender":
                continue
            for value in values:
                if not _is_usable_tag_value(value):
                    continue
                tag_options[key].append(f"{tag_file}::{value}")

    return {key: sorted(set(values)) for key, values in tag_options.items()}


def _get_tag_bundle(tag_file: str = DEFAULT_TAG_FILE) -> dict:
    """Reads the tags JSON file and returns normalized tags plus optional composer rules."""
    tags_path = _resolve_tag_file_path(tag_file)
    loaded_data = {}
    mtime = None

    if not os.path.exists(tags_path) and tag_file != DEFAULT_TAG_FILE:
        fallback_path = os.path.join(os.path.dirname(__file__), DEFAULT_TAG_FILE)
        print(f"ComfyUICharacterComposer Warning: Tags file '{tag_file}' not found, falling back to '{DEFAULT_TAG_FILE}'")
        tags_path = fallback_path

    if os.path.exists(tags_path):
        try:
            mtime = os.path.getmtime(tags_path)
            if TAG_CACHE["path"] == tags_path and TAG_CACHE["mtime"] == mtime and TAG_CACHE["data"] is not None:
                return TAG_CACHE["data"]
            with open(tags_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
        except Exception as e:
            print(f"ComfyUICharacterComposer Error: Could not read tags.json - {e}")

    tags = {}
    for key in MASTER_KEYS:
        if key == "gender":
            tags[key] = GENDER_OPTIONS.copy()
            continue
        raw = loaded_data.get(key, []) if isinstance(loaded_data, dict) else []
        if key == "interaction" and isinstance(loaded_data, dict) and not raw:
            raw = loaded_data.get("pose_x", [])
        if isinstance(raw, list):
            normalized = [str(v) for v in raw if _is_usable_tag_value(v)]
        elif isinstance(raw, str):
            normalized = [raw] if _is_usable_tag_value(raw) else []
        else:
            normalized = []
        tags[key] = normalized

    result = {
        "tags": tags,
        "rules": _normalize_composer_rules(loaded_data.get("_composer_rules") if isinstance(loaded_data, dict) else None),
        "aliases": _normalize_tag_aliases(loaded_data.get("_tag_aliases") if isinstance(loaded_data, dict) else None),
        "conflicts": _normalize_tag_conflicts(loaded_data.get("_tag_conflicts") if isinstance(loaded_data, dict) else None),
        "smart_preset_rules": _normalize_smart_preset_rules(loaded_data.get("_smart_preset_rules") if isinstance(loaded_data, dict) else None),
    }
    TAG_CACHE["path"] = tags_path
    TAG_CACHE["mtime"] = mtime
    TAG_CACHE["data"] = result
    return result


def _get_json_tags(tag_file: str = DEFAULT_TAG_FILE) -> dict:
    return _get_tag_bundle(tag_file)["tags"]


def _get_composer_rules(tag_file: str = DEFAULT_TAG_FILE) -> dict:
    return _get_tag_bundle(tag_file)["rules"]


def _get_tag_aliases(tag_file: str = DEFAULT_TAG_FILE) -> dict:
    return _get_tag_bundle(tag_file)["aliases"]


def _get_tag_conflicts(tag_file: str = DEFAULT_TAG_FILE) -> dict:
    return _get_tag_bundle(tag_file)["conflicts"]


def _get_smart_preset_rules(tag_file: str = DEFAULT_TAG_FILE) -> dict:
    return _get_tag_bundle(tag_file)["smart_preset_rules"]

class ComfyUICharacterComposer:
    DESCRIPTION = "Strict JSON-driven prompt generator for cute & tropical gravure."
    CATEGORY = "Prompt"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "trait_summary", "debug", "why_this_prompt", "dropped_traits", "chaos_score", "stability_hint", "image1")
    FUNCTION = "generate"

    @classmethod
    def INPUT_TYPES(cls):
        def create_combo(options, include_none=True, default="auto", advanced=False):
            base = ["auto", "random"]
            if include_none: base.append("none")
            if default not in base:
                default = "auto"
            return ("COMBO", {"default": default, "options": base + options, "advanced": advanced})

        tags_files = _find_tags_json_files()
        tag_file_default = DEFAULT_TAG_FILE if DEFAULT_TAG_FILE in tags_files else (tags_files[0] if tags_files else DEFAULT_TAG_FILE)
        tag_data = _build_source_tag_options(tags_files or [tag_file_default])
        inputs = {
            "required": {
                "input_prompt": ("STRING", {"default": "", "multiline": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "extra_modifiers": ("STRING", {"default": ", ".join(DEFAULT_MODIFIERS), "advanced": True}),
                "generation_profile": ("COMBO", {"default": "custom", "options": GENERATION_PROFILE_OPTIONS, "tooltip": "High-level bundled preset for the most common good generation setups."}),
                "smart_preset": ("COMBO", {"default": "none", "options": SMART_PRESET_OPTIONS, "tooltip": "Workflow-level preset that biases composition and stability defaults.", "advanced": True}),
                "composition_mode": ("COMBO", {"default": "auto", "options": COMPOSITION_MODE_OPTIONS, "tooltip": "High-level composition intent used to bias defaults and conflict handling."}),
                "subject_count": create_combo(SUBJECT_COUNT_OPTIONS, include_none=False, default="auto"),
                "detail_level": ("COMBO", {"default": "balanced", "options": DETAIL_LEVEL_OPTIONS, "tooltip": "Controls how many secondary details are added to the final prompt."}),
                "style_strength": ("COMBO", {"default": "balanced", "options": STYLE_STRENGTH_OPTIONS, "tooltip": "Controls how strongly vibe, style, and scene flavoring are applied."}),
                "fill_auto_traits": ("BOOLEAN", {"default": False, "advanced": True}),
                "reset_overrides": ("BOOLEAN", {"default": False, "tooltip": "Force all trait override controls back to auto mode for this generation.", "advanced": True}),
                "bypass_generator": ("BOOLEAN", {"default": False, "advanced": True}),
                "preserve_input_position": ("BOOLEAN", {"default": False, "tooltip": "If True and a reference image is supplied, add hints to preserve subject positions and composition from the input image.", "advanced": True}),
                "preserve_character_look": ("BOOLEAN", {"default": False, "tooltip": "Strict: prevent changing look-related tags (hair_color, hair_style, eye_color, outfit, makeup, body_type, chest_size, fantasy_race, ethnicity) when a reference image is supplied.", "advanced": True}),
                "outfit_mode": create_combo(["keep"], include_none=False, default="auto"),
                "tag_file": ("COMBO", {"default": tag_file_default, "options": tags_files or [DEFAULT_TAG_FILE], "tooltip": "Select which tags JSON file to use for generation."}),
            },
            "optional": { "image1": ("IMAGE", {"image_upload": True}) }
        }
        
        advanced_trait_keys = {
            "age", "ethnicity", "fantasy_race", "camera_gear",
            "style_adjective", "creative_twist", "background_mood",
            "accessory", "prop", "background_prop",
        }
        for section_header, attributes in UI_LAYOUT:
            inputs["required"][section_header] = ("STRING", {"default": "", "socketless": True, "extra_dict": {"readonly": True, "disabled": True}})
            for key in attributes:
                opts = tag_data.get(key, [])
                default_value = "none" if key in ["prop", "background_prop"] else "auto"
                inputs["required"][key] = create_combo(
                    opts,
                    include_none=(key not in ["body_type", "ethnicity"]),
                    default=default_value,
                    advanced=(key in advanced_trait_keys),
                )
            
        return inputs

    def generate(self, input_prompt, seed, extra_modifiers, generation_profile, smart_preset, composition_mode, subject_count, detail_level, style_strength, fill_auto_traits, bypass_generator, preserve_input_position=False, preserve_character_look=False, outfit_mode="auto", tag_file=DEFAULT_TAG_FILE, image1=None, **kwargs):
        if bypass_generator:
            return (input_prompt.strip(), NEGATIVE_PROMPT_TERMS, "", "Bypass Active", "Bypass mode returned the raw input prompt.", "", "0", "bypassed", image1)

        rng = random.Random(seed)
        tag_data = _get_json_tags(tag_file)
        composer_rules = _get_composer_rules(tag_file)
        tag_aliases = _get_tag_aliases(tag_file)
        tag_conflicts = _get_tag_conflicts(tag_file)
        smart_preset_rules = _get_smart_preset_rules(tag_file)
        prompt_clean = _sanitize_prompt(input_prompt)
        # preserve hint control -- only active when a reference image is provided
        attach_preserve_hint = False
        preserve_hint_text = "match composition and subject positions of the reference image"

        profile_defaults = GENERATION_PROFILE_DEFAULTS.get(generation_profile, {})
        if generation_profile != "custom":
            if smart_preset == "none" and profile_defaults.get("smart_preset"):
                smart_preset = profile_defaults["smart_preset"]
            if composition_mode == "auto" and profile_defaults.get("composition_mode"):
                composition_mode = profile_defaults["composition_mode"]
            if subject_count in ("1", "auto") and profile_defaults.get("subject_count"):
                subject_count = profile_defaults["subject_count"]
            if detail_level == "balanced" and profile_defaults.get("detail_level"):
                detail_level = profile_defaults["detail_level"]
            if style_strength == "balanced" and profile_defaults.get("style_strength"):
                style_strength = profile_defaults["style_strength"]

        smart_defaults = SMART_PRESET_DEFAULTS.get(smart_preset, {})
        if composition_mode == "auto":
            composition_mode = smart_defaults.get("composition_mode", "auto")
        if subject_count in ("1", "auto") and smart_defaults.get("subject_count") and smart_defaults["subject_count"] != "1":
            subject_count = smart_defaults["subject_count"]
        if detail_level == "balanced" and smart_defaults.get("detail_level"):
            detail_level = smart_defaults["detail_level"]
        if style_strength == "balanced" and smart_defaults.get("style_strength"):
            style_strength = smart_defaults["style_strength"]
        
        if kwargs.get("reset_overrides"):
            for key in MASTER_KEYS:
                kwargs[key] = "auto"

        # 1. Selection Logic
        extracted = {k: _search_keyword(prompt_clean, tag_data[k], tag_aliases.get(k)) for k in MASTER_KEYS}
        final_choices = {}
        for key in MASTER_KEYS:
            ui_val = kwargs.get(key, "auto")
            if ui_val == "auto":
                final_choices[key] = extracted.get(key)
            elif ui_val == "random":
                final_choices[key] = _pick_random_choice(rng, tag_data.get(key, []))
            elif _is_none_selection(ui_val):
                final_choices[key] = None
            else:
                if "::" in ui_val:
                    source_tag_file, value = ui_val.split("::", 1)
                    source_tag_data = _get_json_tags(source_tag_file)
                    final_choices[key] = value if value in source_tag_data.get(key, []) else None
                else:
                    final_choices[key] = ui_val if ui_val in tag_data.get(key, []) or key == "gender" else None

        # Prepare strict look-preservation if requested and a reference image is supplied.
        locked_look_values: dict[str, str | None] = {}
        locked_keys: list[str] = []
        if preserve_character_look and image1 is not None:
            for k in LOOK_KEYS:
                ui_val = kwargs.get(k, "auto")
                if ui_val != "auto" and not _is_none_selection(ui_val):
                    # user explicitly set this trait in the UI
                    locked_look_values[k] = final_choices.get(k)
                elif extracted.get(k) is not None:
                    # trait inferred from the input prompt
                    locked_look_values[k] = extracted.get(k)
                else:
                    # nothing provided; keep whatever current value is (may be None)
                    locked_look_values[k] = final_choices.get(k)
        # Outfit mode handling (auto/random/keep): allow explicit outfit control
        # independent of preserve_character_look. This updates locked_look_values
        # and final_choices so subsequent biasing and random-fill behave correctly.
        om = (outfit_mode or "auto").lower()
        if om == "keep":
            ui_val = kwargs.get("outfit", "auto")
            outfit_val = None
            if ui_val != "auto" and not _is_none_selection(ui_val):
                outfit_val = final_choices.get("outfit")
            elif extracted.get("outfit") is not None:
                outfit_val = extracted.get("outfit")
            elif final_choices.get("outfit") is not None:
                outfit_val = final_choices.get("outfit")
            if outfit_val is not None:
                locked_look_values["outfit"] = outfit_val
        elif om in ("random", "randomize"):
            # Ensure outfit isn't locked and clear it so auto-fill can randomize it.
            if "outfit" in locked_look_values:
                locked_look_values.pop("outfit", None)
            final_choices["outfit"] = None
        # Only treat keys that actually have a value as locked. This allows
        # `fill_auto_traits` to populate look traits that were unknown.
        locked_keys = [k for k, v in locked_look_values.items() if v is not None]

        # Auto-infer subject_count from interaction/pose/subject when set to 'auto'
        if subject_count == "auto":
            interaction_val = final_choices.get("interaction") or ""
            pose_val = final_choices.get("pose") or ""
            subject_val = final_choices.get("subject") or ""
            combined = " ".join([interaction_val, pose_val, subject_val, prompt_clean or ""]).lower()
            if re.search(r"\b(threesome|trio|three|3)\b", combined):
                subject_count = "3"
            elif re.search(r"\b(foursome|four|4)\b", combined):
                subject_count = "4"
            elif re.search(r"\b(two|2|pair|couple|paired|partner|partners)\b", combined):
                subject_count = "2"
            elif re.search(r"\b(group|crowd|many|several|bunch|people)\b", combined):
                subject_count = "group"
            else:
                subject_count = "1"

        final_choices = _apply_mode_biases(final_choices, tag_data, smart_preset_rules, composition_mode, smart_preset, style_strength, subject_count, fill_auto_traits, rng)
        # Re-apply locked look values so mode biases can't change them. Only
        # reapply keys that were actually locked (have non-None values).
        if locked_keys:
            for k in locked_keys:
                final_choices[k] = locked_look_values[k]

        final_choices, dropped_traits, scene_meta = _sanitize_scene_conflicts(final_choices, composer_rules)

        # Protect look keys from being modified by smart-preset blocklists and tag conflict resolution.
        if locked_keys:
            protected = dict(final_choices)
            for k in locked_keys:
                protected[k] = None
            protected = _apply_smart_preset_blocklist(protected, smart_preset_rules, smart_preset, dropped_traits)
            protected = _apply_tag_conflicts(protected, tag_conflicts, dropped_traits)
            for k in locked_keys:
                protected[k] = locked_look_values[k]
            final_choices = protected
        else:
            final_choices = _apply_smart_preset_blocklist(final_choices, smart_preset_rules, smart_preset, dropped_traits)
            final_choices = _apply_tag_conflicts(final_choices, tag_conflicts, dropped_traits)

        preset_name = _resolve_preset_name(final_choices.get("preset"))
        if preset_name and preset_name in PRESET_TRAITS:
            for trait_key, trait_value in PRESET_TRAITS[preset_name].items():
                if trait_key in locked_keys:
                    continue
                if final_choices.get(trait_key) is None and kwargs.get(trait_key, "auto") == "auto":
                    final_choices[trait_key] = trait_value

        # 2. Random Fill
        if fill_auto_traits:
            for key in MASTER_KEYS:
                if key in locked_keys:
                    continue
                if kwargs.get(key, "auto") == "auto" and not final_choices.get(key):
                    final_choices[key] = _pick_random_choice(rng, tag_data.get(key, []))
            # run blocklist/conflict resolution while protecting locked look keys
            if locked_keys:
                protected = dict(final_choices)
                for k in locked_keys:
                    protected[k] = None
                protected = _apply_smart_preset_blocklist(protected, smart_preset_rules, smart_preset, dropped_traits)
                protected = _apply_tag_conflicts(protected, tag_conflicts, dropped_traits)
                for k in locked_keys:
                    protected[k] = locked_look_values[k]
                final_choices = protected
            else:
                final_choices = _apply_smart_preset_blocklist(final_choices, smart_preset_rules, smart_preset, dropped_traits)
                final_choices = _apply_tag_conflicts(final_choices, tag_conflicts, dropped_traits)

        chaos_score_value = _calculate_chaos_score(final_choices, subject_count, scene_meta["interaction_complexity"])
        final_choices = _apply_complexity_guard(final_choices, composer_rules, detail_level, style_strength, chaos_score_value, dropped_traits)

        # Final safety: re-apply any locked look values so they survive all
        # biasing, blocklist, conflict resolution, and complexity trimming.
        if locked_keys:
            for k in locked_keys:
                final_choices[k] = locked_look_values[k]

        # 3. Wildcard Injection
        used = set()
        user_text = input_prompt

        # If the user explicitly chose none, remove any matched terms from the raw prompt
        for key in MASTER_KEYS:
            if final_choices.get(key) is None and extracted.get(key):
                user_text = _remove_tag_phrase(user_text, extracted[key])
        user_text = _cleanup_removed_prompt_text(user_text)

        for k, v in final_choices.items():
            tag = f"{{{k}}}"
            if tag in user_text:
                user_text = user_text.replace(tag, str(v) if v else "")
                used.add(k)
            if k == "interaction" and "{pose_x}" in user_text:
                user_text = user_text.replace("{pose_x}", str(v) if v else "")
                used.add(k)
        # If user asked to preserve input composition and an image is supplied,
        # try to inject a model hint. If the user included the placeholder
        # `{preserve_position}` in their prompt, replace it; otherwise defer
        # appending to the modifiers section so it's prominent.
        if preserve_input_position and image1 is not None:
            if "{preserve_position}" in user_text:
                user_text = user_text.replace("{preserve_position}", preserve_hint_text)
                used.add("preserve_input_position")
            else:
                attach_preserve_hint = True

        user_text = re.sub(r"\{.*?\}", "", user_text)
        user_text = _remove_futanari_terms(user_text)

        # 4. Sentence Construction
        # Build a strong subject anchor first so the model gets the main concept early.
        subject_traits = [
            final_choices.get(k)
            for k in ["subject", "body_type", "chest_size", "age", "ethnicity", "fantasy_race"]
            if k not in used and final_choices.get(k)
        ]
        gender_value = final_choices.get("gender") if "gender" not in used else None
        if subject_count == "2":
            if gender_value == "male":
                subject_anchor = "2 men"
            elif gender_value == "female":
                subject_anchor = "2 women"
            else:
                subject_anchor = "2 people"
        elif subject_count == "group":
            subject_anchor = "group of people"
        elif gender_value == "male":
            subject_anchor = "1 man"
        elif gender_value == "female":
            subject_anchor = "1 woman"
        else:
            subject_anchor = "1 person"
        if not subject_traits:
            subject_traits.append("model")

        hair_color = final_choices.get("hair_color") if "hair_color" not in used else None
        hair_style = final_choices.get("hair_style") if "hair_style" not in used else None
        if hair_color or hair_style:
            subject_traits.append(f"{hair_color or ''} {hair_style or ''}".strip() + " hair")

        eye_color = final_choices.get("eye_color") if "eye_color" not in used else None
        if eye_color:
            subject_traits.append(eye_color)

        subject_sentence = ", ".join([_weight_text(subject_anchor, composer_rules["category_weights"].get("subject", 1.0))] + [p for p in subject_traits if p]).strip(" ,")
        active_budgets = composer_rules["detail_budgets"].get(detail_level, composer_rules["detail_budgets"]["balanced"])
        style_budget = active_budgets.get("style", 2)

        # Build Core Context
        cam = final_choices.get("camera_gear") if "camera_gear" not in used else None
        vibe = final_choices.get("vibe") if "vibe" not in used else None
        style_adjective = final_choices.get("style_adjective") if "style_adjective" not in used else None

        core_context_parts = []
        if vibe:
            core_context_parts.append(vibe)
        if style_adjective:
            core_context_parts.append(style_adjective)
        if style_strength == "strong" and final_choices.get("creative_twist") and "creative_twist" not in used:
            core_context_parts.append(final_choices["creative_twist"])
        core_context_parts = core_context_parts[:style_budget]
        core_context_text = " ".join(core_context_parts).strip()
        if core_context_text:
            core_block = f"{subject_sentence}, {cam or ''}, {_weight_text(core_context_text + ' portrait', composer_rules['category_weights'].get('style', 1.0))}".strip(" ,")
        else:
            core_block = f"{subject_sentence}, {cam or ''}, portrait".strip(" ,")
        
        # Build Detail List
        portrait_details = []
        scene_details = []
        pose_details = []

        expression = final_choices.get("expression") if "expression" not in used else None
        makeup = final_choices.get("makeup") if "makeup" not in used else None
        outfit = final_choices.get("outfit") if "outfit" not in used else None
        accessory = final_choices.get("accessory") if "accessory" not in used else None
        focus = final_choices.get("focus") if "focus" not in used else None
        camera_angle = final_choices.get("camera_angle") if "camera_angle" not in used else None
        setting = final_choices.get("setting") if "setting" not in used else None
        background_mood = final_choices.get("background_mood") if "background_mood" not in used else None
        atmosphere = final_choices.get("atmosphere") if "atmosphere" not in used else None
        creative_twist = final_choices.get("creative_twist") if "creative_twist" not in used else None
        pose = final_choices.get("pose") if "pose" not in used else None
        interaction = final_choices.get("interaction") if "interaction" not in used else None
        prop = final_choices.get("prop") if "prop" not in used else None
        background_prop = final_choices.get("background_prop") if "background_prop" not in used else None

        if expression:
            portrait_details.append(expression)
        if makeup:
            portrait_details.append(makeup)
        if outfit:
            portrait_details.append(_weight_text(f"wearing {outfit}", composer_rules["category_weights"].get("outfit", 1.0)))
        if accessory:
            portrait_details.append(accessory)
        if focus:
            portrait_details.append(focus)
        if camera_angle:
            portrait_details.append(f"shot as a {camera_angle}")

        if interaction:
            pose_details.append(_weight_text(f"interaction: {interaction}", composer_rules["category_weights"].get("interaction", 1.0)))
            if pose and any(term in interaction.lower() for term in ["kiss", "partner", "threesome", "hug", "embrace", "grinding", "spoon"]):
                pose = None
        if pose:
            pose_details.append(_weight_text(f"body pose: {pose}", composer_rules["category_weights"].get("pose", 1.0)))

        if setting:
            scene_details.append(f"at the {setting}")
        if background_mood:
            scene_details.append(background_mood)
        if atmosphere:
            scene_details.append(f"with {atmosphere}")
        if creative_twist:
            scene_details.append(creative_twist)
        if prop and len(scene_details) < 4:
            scene_details.append(prop)
        if background_prop and len(scene_details) < 5:
            scene_details.append(f"background detail: {background_prop}")

        if style_strength == "subtle":
            if final_choices.get("creative_twist"):
                dropped_traits.append(f"creative_twist: {final_choices['creative_twist']} (suppressed by subtle style strength)")
            scene_details = [detail for detail in scene_details if detail != final_choices.get("creative_twist")]
        elif style_strength == "strong" and final_choices.get("creative_twist") and final_choices["creative_twist"] not in scene_details:
            scene_details.insert(0, final_choices["creative_twist"])

        detail_budgets = composer_rules["detail_budgets"]
        budgets = detail_budgets.get(detail_level, detail_budgets["balanced"])
        portrait_budget = budgets.get("portrait", 6)
        pose_budget = budgets.get("pose", 2)
        scene_budget = budgets.get("scene", 4)
        details = (
            portrait_details[:portrait_budget]
            + pose_details[:pose_budget]
            + scene_details[:scene_budget]
        )

        # 5. Final Assembly
        modifiers_front = extra_modifiers.strip()
        # Append preserve hint to the front modifiers if needed so composition
        # guidance is seen early by the model.
        if attach_preserve_hint:
            if modifiers_front:
                modifiers_front = f"{modifiers_front}, {preserve_hint_text}"
            else:
                modifiers_front = preserve_hint_text
        pieces = [modifiers_front, user_text.strip(), core_block, ", ".join(details)]
        final_prompt = ", ".join([p for p in pieces if p])

        # Auto-hint for numeric plurals (e.g., "3 women" or "2 men"):
        # If the user requested multiple people by number, append a short hint
        # to encourage the model to make each person visually distinct.
        try:
            if re.search(r"\b\d+\s+(women|men)\b", input_prompt, flags=re.IGNORECASE):
                hint = "each with distinct appearance"
                if hint.lower() not in final_prompt.lower():
                    final_prompt = f"{final_prompt}, {hint}" if final_prompt else hint
        except Exception:
            # Non-critical hinting should never break generation; ignore on error.
            pass

        # Cleanup
        final_prompt = re.sub(r"\s+", " ", final_prompt)
        final_prompt = re.sub(r",\s*,", ",", final_prompt).strip(" ,")

        if chaos_score_value <= 6:
            stability_hint = "low risk"
        elif chaos_score_value <= 10:
            stability_hint = "medium risk"
        else:
            stability_hint = "high risk"
        
        locked_look_summary = ",".join([f"{k}={locked_look_values.get(k)}" for k in locked_keys]) if locked_keys else "none"
        why_this_prompt = ", ".join(
            [
                f"generation_profile={generation_profile}",
                f"preserve_input_position={bool(preserve_input_position)}",
                f"preserve_character_look={bool(preserve_character_look)}",
                f"locked_look={locked_look_summary}",
                f"smart_preset={smart_preset}",
                f"composition_mode={composition_mode}",
                f"subject_count={subject_count}",
                f"detail_level={detail_level}",
                f"style_strength={style_strength}",
                f"scene_family={scene_meta['scene_family'] or 'none'}",
                f"interaction_complexity={scene_meta['interaction_complexity']}",
            ]
        )
        trait_summary = ", ".join(
            [f"generation_profile: {generation_profile}", f"detail_level: {detail_level}", f"style_strength: {style_strength}", f"subject_count: {subject_count}"] + [f"{k}: {v}" for k, v in final_choices.items() if v]
        )
        debug_str = " | ".join(
            [f"generation_profile={generation_profile}", f"detail_level={detail_level}", f"style_strength={style_strength}", f"subject_count={subject_count}", f"chaos_score={chaos_score_value}", f"stability_hint={stability_hint}"] + [f"{k}={v}" for k, v in final_choices.items() if v]
        )
        dropped_traits_str = "; ".join(dropped_traits) if dropped_traits else "none"
        
        return (final_prompt, NEGATIVE_PROMPT_TERMS, trait_summary, debug_str, why_this_prompt, dropped_traits_str, str(chaos_score_value), stability_hint, image1)

NODE_CLASS_MAPPINGS = {
    "ComfyUICharacterComposer": ComfyUICharacterComposer,
}
