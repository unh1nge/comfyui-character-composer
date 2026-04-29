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
size_categories:
- n<1K
---

# ComfyUI Character Composer

Structured, JSON-driven character prompt system for ComfyUI.

Designed for **consistent, controllable character generation** using Qwen-based workflows — replacing random prompt chaos with deterministic composition.

<img src="preview/ComfyUI_01625_.png" width="100%" />

---

## 🆕 Update v1.1 – Dynamic Tag Switching

Version 1.1 introduces a **dynamic tag system**:

- Import custom `tags.json` files
- Switch between different tag sets (e.g. SFW / NSFW)
- Adapt the generator to different use cases without modifying code

### Important limitation

Custom tags must follow existing UI structure.

Example:

"Vehicles": ["car", "bike", "jet"]


This will **NOT appear in the UI**, because:
- UI categories are defined in `UI_LAYOUT`
- New categories are ignored unless implemented in code

---

## 🔗 Recommended Stack

- Model: Qwen-Image-Edit-Rapid-AIO  
- Workflow: Adapted from Phr00t’s pipeline and included it as
  comfyui-character-composer Qwen workflow.json  
- Node: ComfyUI Character Composer  

This setup combines:
- Qwen spatial reasoning
- structured prompt composition
- controlled character generation

---

## Workflow Overview

<img src="preview/workflow example.png" width="100%" />
comfyui-character-composer Qwen workflow.json

---

## Why this matters

Most character generation setups:
- rely on random prompts
- produce inconsistent characters
- are difficult to reproduce

This node provides:
- structured trait composition
- deterministic outputs (seed-based)
- precise control over character attributes

---

## Features

- JSON-driven prompt system (`tags.json`)
- Dynamic tag switching (v1.1)
- preserve / random / none logic per trait
- Structured categories (face, body, outfit, pose, scene, etc.)
- Preset system for style injection
- Wildcard support (`{tag}` replacement)
- Built-in prompt sanitization
- Optional auto-fill (`randomize_unspecified`)
- Debug output for full traceability

<img src="preview/ComfyUI_01543_.png" width="100%" />

---

## Example

Input:
    {hair_color} {hair_style} woman in {setting}

Output:
    blonde wavy hair woman in neon-lit alley, cinematic lighting, high detail, 8k

---

## Installation

1. Clone into your ComfyUI custom_nodes directory:

    cd ComfyUI/custom_nodes  
    git clone https://github.com/unh1nge/comfyui-character-composer

2. Restart ComfyUI

3. Add node:
    RandomPromptGenerator  
    (Category: Prompts)

Or use the included workflow:
    comfyui-character-composer Qwen workflow.json

<img src="preview/ComfyUI_01645_.png" width="100%" />

---

## Usage

1. Provide an optional base prompt  
2. Configure traits:
    - preserve → keep detected values  
    - random → randomize  
    - none → remove  
3. Enable `randomize_unspecified` for auto-fill  
4. Use `{tags}` for wildcard injection  
5. Adjust `extra_modifiers` for styling  

<img src="preview/ComfyUI_01877_.png" width="100%" />

---

## Custom Workflow

This repository includes a workflow adapted from Phr00t’s Qwen pipeline, modified to:

- integrate structured prompt composition  
- improve character consistency  
- reduce prompt noise  

---

## Customization

- `tags.json` → define traits  
- `DEFAULT_MODIFIERS` → global style baseline  
- `PRESET_TRAITS` → theme presets  
- `UI_LAYOUT` → UI structure  

---

## What this is NOT

- Not a LoRA trainer  
- Not a ControlNet pipeline  
- Not a full workflow system  

This is a **prompt composition layer**.

---

## Outputs

- `positive_prompt` → final prompt  
- `negative_prompt` → filtered terms  
- `debug` → selected traits  

---

## Acknowledgements

Built on top of:

Phr00t – Qwen Image Edit ecosystem  
https://huggingface.co/Phr00t/Qwen-Image-Edit-Rapid-AIO  

---

## Keywords

ComfyUI, prompt engineering, structured prompts, character generation, Qwen workflow

---

## License

Free to use and modify.
