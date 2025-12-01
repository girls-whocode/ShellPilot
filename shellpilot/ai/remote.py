# shellpilot/ai/remote.py

from __future__ import annotations

from pathlib import Path
from typing import Literal
import os
import requests
from requests import HTTPError

from shellpilot.ai.config import load_ai_config

ProviderType = Literal["gpt", "gemini", "copilot"]


class RemoteAIError(RuntimeError):
    pass


def _build_file_prompt(path: Path, content: str) -> str:
    # Mirror the semantics of AIEngine.analyze_file
    return (
        "You are ShellPilot, a Linux-focused assistant. You are helping a "
        "senior Linux engineer understand a file on a Linux system.\n\n"
        "TASK:\n"
        "1. Identify what kind of file this appears to be (log, config, script, JSON, YAML, systemd unit, etc.).\n"
        "2. Summarize what it does or contains in clear bullet points.\n"
        "3. If it looks like a config or script, call out any obvious issues, "
        "risks, or misconfigurations.\n"
        "4. Suggest 2–3 next steps the user might take to debug or improve things.\n\n"
        f"File path: {path}\n\n"
        "File content snippet (may be truncated):\n\n"
        f"{content}\n\n"
        "Respond in Markdown:\n"
        "- Heading with guessed file type\n"
        "- 3–7 bullet points summarizing\n"
        "- 'Next steps:' section with 2–3 bullets.\n"
    )


def _build_dir_prompt(path: Path, manifest: str) -> str:
    return (
        "You are a senior Linux systems engineer and security analyst.\n"
        "You are given a non-recursive manifest of a directory on disk. "
        "Each entry may include:\n"
        "- file/dir name\n"
        "- owner and group\n"
        "- Unix permissions\n"
        "- size\n"
        "- modification time\n"
        "- some heuristic flags\n\n"
        "TASK:\n"
        "1. Explain in plain language what this directory most likely is used for.\n"
        "2. Call out particularly interesting or risky entries (world-writable files, "
        "setuid/setgid binaries, SSH keys, strange scripts, etc.).\n"
        "3. Suggest 3–5 concrete next shell commands the user could run to investigate "
        "further.\n\n"
        f"Directory path: {path}\n\n"
        "Manifest:\n"
        f"{manifest}\n\n"
        "Respond in Markdown with sections:\n"
        "- 'What this directory looks like'\n"
        "- 'Notable or risky files'\n"
        "- 'Suggested next commands'.\n"
    )


# -------------------- OpenAI GPT --------------------


def _call_openai(prompt: str) -> str:
    cfg = load_ai_config()
    key = cfg.get("openai_api_key")
    if not key:
        raise RemoteAIError("OpenAI provider selected but no openai_api_key is configured.")

    endpoint = os.getenv("SHELLPILOT_GPT_ENDPOINT", "https://api.openai.com/v1/chat/completions")
    model = os.getenv("SHELLPILOT_GPT_MODEL", "gpt-4o-mini")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are ShellPilot, a concise Linux-focused assistant running in a terminal file manager.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
    }

    try:
        resp = requests.post(endpoint, headers=headers, json=body, timeout=90)
        # Instead of raw raise_for_status, give a nicer message:
        if resp.status_code >= 400:
            try:
                data = resp.json()
                msg = data.get("error", {}).get("message") or resp.text
            except Exception:
                msg = resp.text
            raise RemoteAIError(f"OpenAI error {resp.status_code}: {msg}")
    except HTTPError as exc:
        # Fallback, just in case
        raise RemoteAIError(f"OpenAI HTTP error: {exc}") from exc
    except Exception as exc:
        raise RemoteAIError(f"OpenAI request failed: {exc}") from exc

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise RemoteAIError(f"Unexpected OpenAI response format: {exc}") from exc


# -------------------- Google Gemini --------------------


def _call_gemini(prompt: str) -> str:
    cfg = load_ai_config()
    key = cfg.get("gemini_api_key")
    if not key:
        raise RemoteAIError("Gemini provider selected but no gemini_api_key is configured.")

    model = os.getenv("SHELLPILOT_GEMINI_MODEL", "gemini-1.5-flash-latest")
    base_url = os.getenv(
        "SHELLPILOT_GEMINI_ENDPOINT",
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    )

    params = {"key": key}
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
        },
    }

    resp = requests.post(base_url, params=params, json=body, timeout=90)
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as exc:
        raise RemoteAIError(f"Unexpected Gemini response format: {exc}") from exc


# -------------------- GitHub Copilot (stub / customizable) --------------------


def _call_copilot(prompt: str) -> str:
    """
    This is intentionally a stub.

    GitHub Copilot's API is not a simple public 'chat completions' drop-in like OpenAI.
    If you have a custom Copilot gateway, point ShellPilot to it by editing this
    function or wiring env vars here.
    """
    raise RemoteAIError(
        "Copilot provider is selected, but no HTTP integration is configured.\n"
        "Edit shellpilot/ai/remote.py::_call_copilot() to point at your Copilot gateway."
    )


# -------------------- Public entrypoints --------------------


def analyze_file_remote(provider: ProviderType, path: Path, content: str) -> str:
    prompt = _build_file_prompt(path, content)
    if provider == "gpt":
        return _call_openai(prompt)
    if provider == "gemini":
        return _call_gemini(prompt)
    if provider == "copilot":
        return _call_copilot(prompt)
    raise RemoteAIError(f"Unsupported remote provider: {provider}")


def analyze_directory_remote(provider: ProviderType, path: Path, manifest: str) -> str:
    prompt = _build_dir_prompt(path, manifest)
    if provider == "gpt":
        return _call_openai(prompt)
    if provider == "gemini":
        return _call_gemini(prompt)
    if provider == "copilot":
        return _call_copilot(prompt)
    raise RemoteAIError(f"Unsupported remote provider: {provider}")
