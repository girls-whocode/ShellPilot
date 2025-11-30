from __future__ import annotations

from pathlib import Path
from typing import Optional
import os

from llama_cpp import Llama

# Default model location:
# ShellPilot/
#   shellpilot/
#   models/
#       phi-3.5-mini/
#           Phi-3.5-mini-instruct-Q4_K_M.gguf
_DEFAULT_MODEL = (
    Path(__file__)
    .resolve()
    .parents[2]
    / "models"
    / "phi-3.5-mini"
    / "Phi-3.5-mini-instruct-Q4_K_M.gguf"
)

class AIEngine:
    """
    Thin wrapper around llama-cpp for ShellPilot.

    Responsibilities:
    - Load the local GGUF model
    - Provide high-level helpers like `analyze_file` and `ask`
    """

    def __init__(self, model_path: Optional[Path] = None) -> None:
        self.model_path = Path(model_path or _DEFAULT_MODEL)

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"AI model not found at {self.model_path}. "
                "Make sure you downloaded the GGUF file."
            )

        # CPU-only setup for now.
        n_threads = max(1, (os.cpu_count() or 4))

        self._llm = Llama(
            model_path=str(self.model_path),
            n_ctx=4096,
            n_threads=n_threads,
            n_gpu_layers=0,  # CPU only
        )

    # ---------- Low-level call helper ----------

    def _run(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> str:
        """
        Call the model with a plain prompt and return the text output.
        """
        result = self._llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["</s>"],
        )

        text = result["choices"][0]["text"]
        return text.strip()

    # ---------- Public helpers ----------

    def analyze_file(self, path: Path, content: str) -> str:
        """
        Explain what a file is, what it's used for, and any obvious issues.
        Designed for logs, configs, scripts, etc.
        """
        # Keep prompt size under control for huge files
        snippet = content
        max_chars = 8000
        if len(snippet) > max_chars:
            snippet = snippet[:max_chars]
            snippet += "\n\n[... truncated by ShellPilot for length ...]\n"

        prompt = (
            "You are ShellPilot, a Linux-focused TUI assistant running locally "
            "inside a terminal file manager. You are helping a senior Linux "
            "engineer understand a file on a Linux system.\n\n"
            "User environment:\n"
            "- OS: generic Linux (Fedora/Ubuntu/Alma/etc.)\n"
            "- ShellPilot is browsing the filesystem and showing file previews.\n"
            "- The user understands Linux, systemd, networking, etc., but wants "
            "quick, concise insights.\n\n"
            "TASK:\n"
            "1. Identify what kind of file this appears to be (log, config, script, JSON, YAML, systemd unit, etc.).\n"
            "2. Summarize what it does or contains in clear bullet points.\n"
            "3. If it looks like a config or script, call out any obvious issues, risks, or misconfigurations.\n"
            "4. Suggest 2-3 next steps the user might take to debug or improve things.\n\n"
            f"File path: {path}\n\n"
            "File content snippet (may be truncated):\n\n"
            f"{snippet}\n\n"
            "Now, respond with:\n"
            "- A short heading with the file type guess\n"
            "- 3-7 bullet points summarizing\n"
            "- A \"Next steps:\" section with 2-3 bullets.\n"
        )

        return self._run(prompt, max_tokens=512, temperature=0.2)

    def ask(self, question: str, context: Optional[str] = None) -> str:
        """
        Generic Q&A helper the rest of the app can use.

        `context` can be log output, error messages, or config snippets.
        """
        ctx_txt = ""
        if context:
            ctx = context
            if len(ctx) > 6000:
                ctx = ctx[:6000] + "\n\n[... truncated context ...]\n"
            ctx_txt = f"\n\nContext:\n{ctx}\n"

        prompt = (
            "You are ShellPilot, a Linux terminal assistant.\n"
            "Answer the user's question as a concise, practical Linux-savvy helper.\n"
            "If you give commands, assume a Bash shell on a typical Linux system.\n\n"
            f"Question:\n{question}\n"
            f"{ctx_txt}\n"
            "Now answer in a clear, practical way. If you suggest commands, "
            "explain briefly what they do.\n"
        )

        return self._run(prompt, max_tokens=384, temperature=0.3)


# ---------- Singleton accessor ----------

_engine: Optional[AIEngine] = None

def get_engine() -> AIEngine:
    """
    Lazy-load a global AIEngine instance.
    """
    global _engine
    if _engine is None:
        _engine = AIEngine()
    return _engine
