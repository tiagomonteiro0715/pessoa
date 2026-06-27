"""Launcher: ensure Ollama is up, pull gemma4:e2b if missing, run the Streamlit UI.

Optional flags:
    --skill <name-or-path>           Use a Claude Skill markdown file as the persona.
                                     <name> resolves to skills/<name>.md; a path
                                     (absolute or with .md extension) is used directly.
    --skill-mode {append,replace}    How the skill combines with the base pt-PT
                                     persona. Default: append (stacks on top).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SKILLS_DIR = ROOT / "skills"


def _resolve_skill(value: str) -> Path:
    """Bare name → skills/<name>.md ; any path → used directly."""
    p = Path(value)
    looks_like_path = p.suffix == ".md" or os.sep in value or "/" in value
    resolved = (
        (p if p.is_absolute() else (Path.cwd() / p).resolve())
        if looks_like_path else (SKILLS_DIR / f"{value}.md")
    )
    if not resolved.is_file():
        raise SystemExit(f"[pessoa] skill file not found: {resolved}")
    return resolved


parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--skill",
    help="Name (looks up skills/<name>.md) or path to a Claude Skill markdown file.",
)
parser.add_argument(
    "--skill-mode",
    choices=("append", "replace"),
    default="append",
    help="Combine mode (default: append).",
)
args = parser.parse_args()

if args.skill:
    skill_path = _resolve_skill(args.skill)
    os.environ["PESSOA_SKILL"] = str(skill_path)
    os.environ["PESSOA_SKILL_MODE"] = args.skill_mode
    print(f"[pessoa] skill: {skill_path.name} (mode={args.skill_mode})", flush=True)

# Import AFTER env vars are set so chat.py reads them at module load.
sys.path.insert(0, str(ROOT / "src"))
from chat import ensure_model_pulled, ensure_server_env  # noqa: E402

ensure_server_env()
ensure_model_pulled()
subprocess.run([sys.executable, "-m", "streamlit", "run",
                str(ROOT / "src" / "app.py")])
