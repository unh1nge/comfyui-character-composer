---
license: apache-2.0
task_categories:
- image-to-image
language:
- en
tags:
- comfyui
- qwen
- character-generation
- custom-node
- workflow
- image-generation
pretty_name: ComfyUI Character Composer
version: 1.2
release_date: 2026-04-30
size_categories:
- n<1K
---
# ComfyUI Character Composer

**Version:** 1.2 • **Release Date:** 2026-04-30 • **License:** Apache-2.0

Structured, JSON-driven character prompt system for ComfyUI.

Designed for consistent, controllable character generation with Qwen-style workflows, replacing random prompt chaos with a more deterministic composition layer.

Spicier companion dataset:
https://huggingface.co/datasets/unh1nge/comfyui-character-composer

<img src="preview/ComfyUI_01625_.png" width="100%" />

## New / Advanced toggles (v1.2)

- `preserve_input_position` (BOOLEAN, advanced): If True and a reference image is supplied, injects a short preserve-position hint into the prompt (or replace `{preserve_position}` if present). For best results wire a bbox extractor (see `ComfyUIBBoxExtractor`).

- `preserve_character_look` (BOOLEAN, advanced): Strictly preserve known look traits from the reference image or UI selections. Unknown look traits remain eligible for `fill_auto_traits`. Only traits with actual values are locked so `fill_auto_traits` can still populate missing fields.

- `outfit_mode` (COMBO): `auto` / `keep` / `random` — keeps or randomizes the `outfit` trait when used with `preserve_character_look` and/or `fill_auto_traits`.

---

## Recommended Stack

- Model: `Qwen-Image-Edit-Rapid-AIO`
- Workflow: adapted from Phr00t's pipeline
- Node: `ComfyUI Character Composer`

This setup combines:
- Qwen spatial reasoning
- structured prompt composition
- controllable character generation

---

## Workflow Overview

<img src="preview/workflow example.png" width="100%" />

---

## Why This Node Exists

Most character-generation pipelines:
- rely on random prompts
- produce inconsistent characters
- become hard to reproduce
- break down when too many pose, style, and scene tags pile up

This node provides:
- structured trait composition
- seed-based deterministic behavior
- prompt cleanup and conflict handling
- JSON-driven customization without rewriting Python

---

## Current Features

- JSON-driven trait libraries via `tags.json` and `tags_NSFW.json`
- Selectable tag source file with merged UI dropdowns
- Smart prompt assembly with weighted core traits
- Wildcard support such as `{hair_color}` or `{interaction}`
- Backward compatibility for legacy `{pose_x}` placeholders
- Workflow-level smart presets
- Composition-aware defaults and conflict handling
- Scene sanitization for unstable interaction / pose / camera combinations
- Complexity guard that trims low-priority details when prompts get overloaded
- Alias matching from JSON, such as `blond -> blonde`
- Tag conflict rules from JSON, such as `kokoshnik` vs `ushanka`
- Detail budgets and category weights from JSON
- Debug outputs explaining what was selected, dropped, and why

<img src="preview/ComfyUI_01543_.png" width="100%" />

---

## Main Controls

### Core inputs

- `input_prompt`
- `seed`
- `tag_file`
- `extra_modifiers`

### High-level steering

- `smart_preset`
  - `none`
  - `safe portrait`
  - `high detail character`
  - `winter fashion`
  - `paired cinematic`
  - `simple anatomy-safe`

 - `composition_mode`
  - `auto`
  - `solo portrait`
  - `fashion`
  - `paired`
  - `close-up`
  - `full body`
  - `winter`
  - `fantasy`

 - `subject_count`
  - `auto` (recommended) — node will infer 1/2/3/4/group from prompt/interaction/pose
  - `1`
  - `2`
  - `3`
  - `4`
  - `group`

- `detail_level`
  - `minimal`
  - `balanced`
  - `rich`

- `style_strength`
  - `subtle`
  - `balanced`
  - `strong`

 

### Utility toggles

- `fill_auto_traits`
  - fills unresolved `auto` fields from the active tag file

- `reset_overrides`
  - pushes trait dropdowns back to `auto` for the current generation

- `bypass_generator`
  - returns the raw `input_prompt` unchanged

### Trait sections

The node UI is grouped into:
- `CORE CREATIVE`
- `CHARACTER LOOK`
- `CAMERA & FRAMING`
- `STYLE & SCENE`
- `OPTIONAL EXTRAS`

Notable rename:
- `pose_x` is now `interaction`

---

## Example

Input:

```text
{hair_color} {hair_style} woman in {setting}
```

Possible output:

```text
gravure, photorealistic, soft lighting, 8k, (1woman:1.20), model blonde beach waves hair, shot on 35mm film grain, modern portrait, wearing bikini minimal fabric, shot as a three-quarter shot natural perspective, at the tropical beach open horizon
```

---

## Installation

1. Clone into your `ComfyUI/custom_nodes` directory:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/unh1nge/comfyui-character-composer
```

2. Restart ComfyUI.

3. Add the node:
   `ComfyUICharacterComposer`
   Category: `Prompt`

You can also use the included workflow JSON files.

<img src="preview/ComfyUI_01645_.png" width="100%" />

---

## Usage

1. Start with an optional natural-language base prompt.
2. Pick a `tag_file`.
3. Set a `smart_preset` or `composition_mode` if you want the node to bias defaults for you.
4. Choose `subject_count`, `detail_level`, and `style_strength`.
5. Leave most dropdowns on `auto` unless you need exact overrides.
6. Use `fill_auto_traits` when you want the node to complete unresolved traits.
7. Use `{tags}` inside `input_prompt` if you want explicit wildcard injection.
8. Check `why_this_prompt`, `dropped_traits`, and `chaos_score` when debugging bad generations.

<img src="preview/ComfyUI_01877_.png" width="100%" />

---

## JSON Customization

The node is intentionally data-driven. Most tuning can now happen in JSON.

### Trait lists

The standard visible dropdown values still live in keys such as:
- `hair_color`
- `outfit`
- `interaction`
- `setting`
- `prop`

`interaction` will also load from legacy `pose_x` arrays if needed.

### `_composer_rules`

Optional rule block for prompt behavior and scene stability.

Examples:
- `interaction_scene_families`
- `scene_compatible_pose_hints`
- `complexity_level_terms`
- `extreme_focus_terms`
- `extreme_camera_terms`
- `accessory_drop_terms`
- `setting_drop_terms`
- `setting_restricted_scenes`
- `camera_downgrade`
- `detail_budgets`
- `category_weights`
- `complexity_thresholds`

### `_tag_aliases`

Optional synonym mapping for prompt detection without bloating the UI.

Examples:
- `blond -> blonde`
- `fur hat -> ushanka fur hat`
- `snow maiden outfit -> snegurochka costume`

### `_tag_conflicts`

Optional conflict map for incompatible selections.

Examples:
- `kokoshnik headdress` conflicts with `ushanka fur hat`
- `cat ears` conflicts with `bunny ears`
- `winter boots` conflicts with `high heels`

---

## Prompt Behavior Notes

- Core traits are weighted more strongly than decorative traits.
- Composition mode can auto-bias camera, focus, scene, and style defaults.
- Smart presets can override default `detail_level`, `style_strength`, `subject_count`, and composition intent.
- Complex interaction scenes may automatically drop risky focus, props, accessories, or settings.
- The complexity guard trims low-priority traits when the prompt becomes too crowded.

This is meant to improve stability, not produce perfectly identical prompts for every setup or model.

---

## Outputs

- `positive_prompt`
  - final assembled prompt

- `negative_prompt`
  - built-in negative terms

- `trait_summary`
  - compact readable summary of active choices

- `debug`
  - denser trace string for selected values and chaos score

- `why_this_prompt`
  - short explanation of the active smart preset, composition mode, subject count, and interaction complexity

- Note: `why_this_prompt` now also includes `locked_look=...` showing which look keys (if any) were preserved during generation.

- `dropped_traits`
  - traits removed by scene conflicts, tag conflicts, style suppression, or the complexity guard

- `chaos_score`
  - rough complexity score for the chosen combination

- `image1`
  - passthrough image input

---

## Included Workflows

This repository includes workflow JSON files adapted from the Qwen ecosystem and adjusted for structured prompt composition.
 
- [text-to-image-wf.json](text-to-image-wf.json) — text-to-image starter workflow.

- [comfyui-character-composer Qwen workflow.json](comfyui-character-composer%20Qwen%20workflow.json) — Qwen image-to-image workflow.

They are useful as starting points for:
- text-to-image
- text-to-video
- character-consistent edits

---

## What This Is Not

- Not a LoRA trainer
- Not a ControlNet pipeline
- Not a full workflow engine

This is a prompt composition layer.

---

## Acknowledgements

Built on top of:

Phr00t - Qwen Image Edit ecosystem
https://huggingface.co/Phr00t/Qwen-Image-Edit-Rapid-AIO

---

## Keywords

ComfyUI, prompt engineering, structured prompts, character generation, Qwen workflow

---

## License

Free to use and modify.
