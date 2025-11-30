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
            # If your model was quantized with larger context, 8192 is a nice upgrade.
            # If not, leaving 4096 is fine – no need to force it.
            n_ctx=8192,
            n_threads=n_threads,
            n_gpu_layers=0,   # CPU-only
            n_batch=512,      # better throughput for longer generations
        )

    def _run(
        self,
        prompt: str,
        max_tokens: int = 768,   # was 320
        temperature: float = 0.15,
    ) -> str:
        """
        Call the model with a plain prompt and return the text output.
        """
        result = self._llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_k=40,
            top_p=0.9,
            repeat_penalty=1.1,
            stop=["</s>", "<|end|>", "<|endoftext|>"],
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
        max_chars = 16000   # was 8000 – allow ~2x more context
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

        return self._run(prompt, max_tokens=1024, temperature=0.15)

    def analyze_directory(self, path: Path, manifest: str) -> str:
        """
        Ask the model to explain what this directory is, surface anything suspicious,
        and suggest next investigation commands. Returns Markdown.
        """
        prompt = (
            "You are a senior Linux systems engineer and security analyst. "
            "You are given a non-recursive manifest of a directory on disk.\n"
            "Each entry may include:\n"
            "- file/dir name\n"
            "- owner and group\n"
            "- Unix permissions\n"
            "- size\n"
            "- modification time\n"
            "- some heuristic flags\n\n"
            "Directory path:\n"
            f"{path}\n\n"
            f"Manifest:\n{manifest}\n\n"
            "Your tasks:\n\n"
            "1. Briefly explain what this directory is *likely* used for\n"
            "   (based on names, file types, and location in the filesystem).\n"
            "2. Highlight anything that looks unusual, risky, or potentially malicious.\n"
            "   - World-writable files\n"
            "   - suid/sgid binaries\n"
            "   - strange locations for executables\n"
            "   - double-extension webshell-style names\n"
            "   - suspicious naming patterns\n"
            "3. For each suspicious item, explain *why* it might be risky\n"
            "   and how an admin could verify whether it's benign.\n"
            "4. Suggest 5–10 concrete shell commands the admin could run next\n"
            "   to investigate further (read-only commands only, no destructive actions).\n\n"
            "Format your answer in Markdown with clear headings, bullet lists, and fenced code blocks for shell commands.\n"
        )

        return self._run(prompt, max_tokens=1024)

    def ask(self, question: str, context: Optional[str] = None) -> str:
        """
        Generic Q&A helper the rest of the app can use.

        `context` can be log output, error messages, or config snippets.
        """
        ctx_txt = ""
        if context:
            ctx = context
            if len(ctx) > 12000:
                ctx = ctx[:12000] + "\n\n[... truncated context ...]\n"
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

        return self._run(prompt, max_tokens=768, temperature=0.3)


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
