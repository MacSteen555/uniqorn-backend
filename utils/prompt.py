from functools import cache
from pathlib import Path
from typing import Any, Dict


@cache
def load_file(file_name: str) -> Dict[str, Any]:
    """Load a YAML file and cache the result."""
    import yaml
    
    with open(file_name, "r", encoding="utf-8") as file:
        return yaml.safe_load(file.read())


def load_prompt(file: Path, prompt: str, **kwargs) -> str:
    prompt_data = load_file(str(file))
    
    if prompt not in prompt_data:
        raise KeyError(f"Prompt '{prompt}' not found in {file}")
    
    selected_prompt = prompt_data[prompt]
    
    for key, value in kwargs.items():
        selected_prompt = selected_prompt.replace(f"{{{key}}}", str(value))
    
    return selected_prompt