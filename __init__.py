"""ComfyUI Character Composer custom node package."""

from .comfyui_character_composer import NODE_CLASS_MAPPINGS, ComfyUICharacterComposer

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "ComfyUICharacterComposer", "WEB_DIRECTORY"]
