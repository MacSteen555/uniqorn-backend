
from pathlib import Path

import yaml

def load_prompt(file: Path, prompt: str, **kwargs) -> str:
    with open(file, "r", encoding="utf-8") as f:
        prompt = yaml.safe_load(f.read())
    
    select_prompt = prompt[prompt]

    for key, value in kwargs.items():
        select_prompt = select_prompt.replace(f"{{{key}}}", value)

    return select_prompt