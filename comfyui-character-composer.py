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
        rf"(?:\b[a-zA-Z]+\s+){{0,2}}{escaped_tag}\b",
        "",
        prompt,
        flags=re.IGNORECASE,
    )
    return cleaned

# The UI_LAYOUT is the ONLY place where keys are defined. 
# This tells the script which dropdowns to create.
UI_LAYOUT = [
    ("--- FACE & HAIR ---", ["hair_color", "hair_style", "eye_color", "expression", "makeup"]),
    ("--- BODY & IDENTITY ---", ["body_type", "chest_size", "age", "ethnicity", "fantasy_race"]),
    ("--- OUTFIT & ACCESSORIES ---", ["outfit", "accessory"]),
    ("--- POSE & CAMERA ---", ["pose", "focus", "camera_angle", "camera_gear"]),
    ("--- STYLE & VIBE ---", ["preset", "vibe", "style_adjective", "creative_twist"]),
    ("--- SCENE & ATMOSPHERE ---", ["setting", "background_mood", "atmosphere", "prop"])
]

# Flatten the layout to get a master list of all keys the engine should handle
MASTER_KEYS = [key for _, keys in UI_LAYOUT for key in keys]

TAG_CACHE = {
    "mtime": None,
    "data": None,
}

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

def _normalize_prompt(prompt: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", prompt.lower())

def _sanitize_prompt(prompt: str) -> str:
    sanitized = prompt
    for term in BAD_PROMPT_TERMS:
        sanitized = re.sub(rf"\b{re.escape(term)}\b", "", sanitized, flags=re.IGNORECASE)
    sanitized = _remove_futanari_terms(sanitized)
    return re.sub(r"\s+", " ", sanitized).strip()

def _search_keyword(prompt: str, choices: list[str]) -> str | None:
    normalized = _normalize_prompt(prompt)
    for choice in sorted(choices, key=len, reverse=True):
        if re.search(rf"\b{re.escape(choice.lower())}\b", normalized):
            return choice
    return None

def _is_none_selection(value) -> bool:
    return value is None or str(value).strip().lower() in ("none", "")


def _get_json_tags() -> dict:
    """Reads the tags.json file. Returns empty lists for any missing MASTER_KEYS."""
    tags_path = os.path.join(os.path.dirname(__file__), "tags.json")
    loaded_tags = {}
    mtime = None

    if os.path.exists(tags_path):
        try:
            mtime = os.path.getmtime(tags_path)
            if TAG_CACHE["mtime"] == mtime and TAG_CACHE["data"] is not None:
                return TAG_CACHE["data"]
            with open(tags_path, "r", encoding="utf-8") as f:
                loaded_tags = json.load(f)
        except Exception as e:
            print(f"ComfyUICharacterComposer Error: Could not read tags.json - {e}")

    # Ensure every key in our UI exists, even if the JSON forgot it
    result = {}
    for key in MASTER_KEYS:
        raw = loaded_tags.get(key, [])
        if isinstance(raw, list):
            normalized = [str(v) for v in raw if v is not None]
        elif isinstance(raw, str):
            normalized = [raw]
        else:
            normalized = []
        result[key] = normalized or ["missing_key_in_json"]

    TAG_CACHE["mtime"] = mtime
    TAG_CACHE["data"] = result
    return result

class ComfyUICharacterComposer:
    DESCRIPTION = "Strict JSON-driven prompt generator for cute & tropical gravure."
    CATEGORY = "Prompt"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "IMAGE")
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "debug", "image1")
    FUNCTION = "generate"

    @classmethod
    def INPUT_TYPES(cls):
        def create_combo(options, include_none=True):
            base = ["preserve", "random"]
            if include_none: base.append("none")
            return ("COMBO", {"default": "preserve", "options": base + options})

        tag_data = _get_json_tags()
        inputs = {
            "required": {
                "input_prompt": ("STRING", {"default": "", "multiline": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "extra_modifiers": ("STRING", {"default": ", ".join(DEFAULT_MODIFIERS)}),
                "randomize_unspecified": ("BOOLEAN", {"default": False}),
                "reset_to_preserve": ("BOOLEAN", {"default": False, "tooltip": "Force all non-preset trait controls back to preserve mode for this generation."}),
                "bypass_generator": ("BOOLEAN", {"default": False}),
            },
            "optional": { "image1": ("IMAGE", {"image_upload": True}) }
        }
        
        for section_header, attributes in UI_LAYOUT:
            inputs["required"][section_header] = ("STRING", {"default": "", "socketless": True, "extra_dict": {"readonly": True, "disabled": True}})
            for key in attributes:
                opts = tag_data.get(key, ["missing_key_in_json"])
                inputs["required"][key] = create_combo(opts, include_none=(key not in ["body_type", "ethnicity"]))
            
        return inputs

    def generate(self, input_prompt, seed, extra_modifiers, randomize_unspecified, bypass_generator, image1=None, **kwargs):
        if bypass_generator:
            return (input_prompt.strip(), NEGATIVE_PROMPT_TERMS, "Bypass Active", image1)

        rng = random.Random(seed)
        tag_data = _get_json_tags()
        prompt_clean = _sanitize_prompt(input_prompt)
        prompt_clean = _remove_futanari_terms(prompt_clean)
        
        if kwargs.get("reset_to_preserve"):
            for key in MASTER_KEYS:
                kwargs[key] = "preserve"

        # 1. Selection Logic
        extracted = {k: _search_keyword(prompt_clean, tag_data[k]) for k in MASTER_KEYS}
        final_choices = {}
        for key in MASTER_KEYS:
            ui_val = kwargs.get(key, "preserve")
            if ui_val == "preserve":
                final_choices[key] = extracted.get(key)
            elif ui_val == "random":
                final_choices[key] = rng.choice(tag_data[key])
            elif _is_none_selection(ui_val):
                final_choices[key] = None
            else:
                final_choices[key] = ui_val

        preset_name = final_choices.get("preset")
        if preset_name and preset_name in PRESET_TRAITS:
            for trait_key, trait_value in PRESET_TRAITS[preset_name].items():
                if final_choices.get(trait_key) is None and kwargs.get(trait_key, "preserve") == "preserve":
                    final_choices[trait_key] = trait_value

        # 2. Random Fill
        if randomize_unspecified:
            for key in MASTER_KEYS:
                if not final_choices.get(key) and not _is_none_selection(kwargs.get(key)):
                    final_choices[key] = rng.choice(tag_data[key])

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
        user_text = re.sub(r"\{.*?\}", "", user_text)
        user_text = _remove_futanari_terms(user_text)

        # 4. Sentence Construction
        # Build subject
        subject_traits = [final_choices.get(k) for k in ["chest_size", "body_type", "age", "ethnicity", "fantasy_race"] if k not in used and final_choices.get(k)]
        
        hair_color = final_choices.get("hair_color") if "hair_color" not in used else None
        hair_style = final_choices.get("hair_style") if "hair_style" not in used else None
        if hair_color or hair_style:
            subject_traits.append(f"{hair_color or ''} {hair_style or ''}".strip() + " hair")
            
        subject_traits.append("woman")
        subject_sentence = " ".join([p for p in subject_traits if p]).strip()

        # Build Core Context
        cam = final_choices.get("camera_gear") if "camera_gear" not in used else None
        vibe = final_choices.get("vibe") if "vibe" not in used else None
        
        core_block = f"{cam or ''}, a {vibe or ''} portrait of {subject_sentence}".strip(", ")
        
        # Build Detail List
        details = []
        for k in ["expression", "makeup", "outfit", "accessory", "pose", "focus", "camera_angle", "setting", "atmosphere", "prop"]:
            if k not in used and final_choices.get(k):
                val = final_choices[k]
                if k == "outfit":
                    details.append(f"wearing {val}")
                elif k == "camera_angle":
                    details.append(f"shot as a {val}")
                elif k == "setting":
                    details.append(f"at the {val}")
                elif k == "atmosphere":
                    details.append(f"with {val}")
                else:
                    details.append(val)

        # 5. Final Assembly
        pieces = [user_text.strip(), core_block, ", ".join(details), extra_modifiers.strip()]
        final_prompt = ", ".join([p for p in pieces if p])
        
        # Cleanup
        final_prompt = re.sub(r"\s+", " ", final_prompt)
        final_prompt = re.sub(r",\s*,", ",", final_prompt).strip(" ,")
        
        debug_str = " | ".join(f"{k}={v}" for k, v in final_choices.items() if v)
        
        return (final_prompt, NEGATIVE_PROMPT_TERMS, debug_str, image1)

NODE_CLASS_MAPPINGS = {
    "ComfyUICharacterComposer": ComfyUICharacterComposer,
}
