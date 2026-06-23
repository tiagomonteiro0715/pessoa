"""CLI batch runner: ask a fixed set of prompts via the shared chat logic."""
import subprocess

from src.chat import (
    build_memory,
    ensure_model_pulled,
    ensure_server_env,
    stream_answer,
)

PROMPTS = {
    "definition":   "In one short sentence, what is an avatar in computing?",
    "origin":       "Where does the word 'avatar' come from?",
    "first_use":    "When was the term 'avatar' first used for a digital representation?",
    "games":        "How are avatars used in video games today?",
    "vr":           "Why do avatars matter in virtual reality?",
    "social":       "Name two ways avatars are used on social platforms.",
    "ai_agents":    "How might an AI agent use an avatar to communicate?",
    "privacy":      "What's one privacy benefit of using an avatar online?",
    "future":       "What's a likely development for avatars in the next 5 years?",
    "fun_fact":     "Tell me one surprising fact about avatars.",
}


def main():
    ensure_server_env()
    ensure_model_pulled()

    mem = build_memory()
    for i, (key, prompt) in enumerate(PROMPTS.items(), start=1):
        print(f"\n[{i}/{len(PROMPTS)}] {key} — {prompt}")
        print("Response:")
        for piece in stream_answer(mem, prompt):
            print(piece, end="", flush=True)
        print()

    print("\n--- ollama ps (check GPU/CPU placement) ---")
    print(subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout)


if __name__ == "__main__":
    main()
