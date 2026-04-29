# comfyui-character-composer
<img src="preview/workflow example.png" alt="ComfyUI workflow example" width="100%" />

A custom ComfyUI node and Qwen Workflow for generating polished character prompts using JSON-driven, configurable prompt traits.

The node is designed for easy character generation, with options for preserving existing prompts, randomizing traits, and excluding unwanted categories.

<img src="preview/ComfyUI_01625_.png" alt="Random Prompt Generator preview 2" width="100%" />


## Features

- JSON-driven prompt tag selection
- `preserve`, `random`, and `none` options for each trait
- Supports detailed trait categories like hair, body, outfit, pose, setting, and atmosphere
- Built-in prompt sanitization and exclusion support
- Compatible with ComfyUI custom node workflow

<img src="preview/ComfyUI_01543_.png" alt="Random Prompt Generator preview 1" width="100%" />

## Installation

1. Copy the `comfyui-character-composer` folder into your ComfyUI `custom_nodes` directory.
2. Restart ComfyUI so it detects the new node.
3. Open the node graph and add the `ComfyUICharacterComposer` node. It is located in "Prompts".

<img src="preview/ComfyUI_01645_.png" alt="Random Prompt Generator preview 3" width="100%" />


## Usage

1. Provide an input prompt to guide the generator.
2. Choose from the dropdowns to preserve, randomize, or remove values.
3. Enable `randomize_unspecified` to fill any unspecified trait boxes automatically.
4. Optionally use `extra_modifiers` to append additional style and quality tags.

<img src="preview/ComfyUI_01877_.png" alt="Random Prompt Generator preview 4" width="100%" />

## Customization

- Edit `tags.json` to modify available trait options.
- Update `DEFAULT_MODIFIERS` in `comfyui_character_composer.py` to change the default prompt modifiers.
- Add or adjust presets in `PRESET_TRAITS` for prebuilt theme combinations.

## Notes

- The node returns the generated prompt as the `positive_prompt` output.
- It also returns a `debug` string showing selected trait values.
- Image metadata is not automatically populated; save prompts separately if needed.

## License

Use this node freely in your ComfyUI projects. Modify the code and tags to fit your character generation needs.
