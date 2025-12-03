from __future__ import annotations

from pathlib import Path
from typing import Optional
import os
import urllib.request  # needed for download_model
import urllib.request
import urllib.error
from llama_cpp import Llama

from shellpilot.ai.hardware import detect_nvidia_gpu
from shellpilot.ai.models import get_model_registry, get_model_path
from shellpilot.config import load_config

# Default model location (legacy, not really used now that we have a registry,
# but kept here in case you want a hard fallback somewhere else):
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

    def __init__(self, model_id: str = "phi-3.5-mini-q4") -> None:
        # Use the lazy-loaded registry instead of AI_MODEL_REGISTRY
        registry = get_model_registry()

        if model_id not in registry:
            raise ValueError(f"Unknown AI model id: {model_id}")

        self.model_id = model_id
        self.model_spec = registry[model_id]
        self.model_path: Path = get_model_path(model_id)

        # CPU thread setup (still defaults to "use all cores")
        n_threads = max(1, (os.cpu_count() or 4))
        self.n_threads = n_threads

        # Detect NVIDIA GPU once and remember it
        self.gpu_info = detect_nvidia_gpu()
        self.use_gpu = bool(self.gpu_info)

        if self.gpu_info:
            # You can swap this to your logging system later
            print(
                f"[ShellPilot][AI] Detected NVIDIA GPU: "
                f"{self.gpu_info.name} ({self.gpu_info.memory_mb} MB VRAM)"
            )
        else:
            print("[ShellPilot][AI] No NVIDIA GPU detected, using CPU mode")

        # Lazily created llama-cpp instance
        self._llm: Optional[Llama] = None

    def _create_llm(self) -> Llama:
        """
        Construct the underlying llama-cpp model.

        - If an NVIDIA GPU is detected and the llama-cpp wheel was built with CUDA,
          we try to offload all layers to GPU (n_gpu_layers = -1).
        - If that fails for any reason (no CUDA build, driver mismatch, etc.),
          we log and fall back to CPU-only (n_gpu_layers = 0).
        """
        base_kwargs = {
            "model_path": str(self.model_path),
            "n_ctx": 8192,
            "n_threads": self.n_threads,
            "n_batch": 512,
        }

        # First: try GPU if available
        if getattr(self, "use_gpu", False):
            try:
                print("[ShellPilot][AI] Initializing llama-cpp with GPU offload...")
                return Llama(
                    **base_kwargs,
                    n_gpu_layers=-1,  # offload as many layers as possible
                )
            except Exception as e:
                # If GPU init fails, fall back to CPU and don't try again
                print(
                    "[ShellPilot][AI] GPU initialization failed, "
                    f"falling back to CPU-only mode. Error: {e!r}"
                )
                self.use_gpu = False

        # CPU-only path (what you had before)
        print(
            f"[ShellPilot][AI] Initializing llama-cpp in CPU mode "
            f"({self.n_threads} threads)"
        )
        return Llama(
            **base_kwargs,
            n_gpu_layers=0,
        )

    def _run(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.15,
    ) -> str:
        """
        Call the model with a plain prompt and return the text output.
        """
        # Lazily load the model the first time we actually need it
        if self._llm is None:
            if not self.model_path.is_file():
                raise FileNotFoundError(
                    f"AI model '{self.model_spec.name}' not found at {self.model_path}."
                )
            self._llm = self._create_llm()

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

    def download_model(self, progress_cb=None) -> None:
        """
        Download the GGUF model for the current model_spec if it's missing.

        `progress_cb(downloaded_bytes, total_bytes)` is optional and lets
        the UI show progress.
        """
        if self.model_path.is_file():
            return

        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        url = self.model_spec.download_url
        tmp_path = self.model_path.with_suffix(self.model_path.suffix + ".part")

        # Token resolution order:
        # 1) Environment variables (HF_TOKEN / HUGGINGFACEHUB_API_TOKEN)
        # 2) AppConfig (Settings screen)
        token = (
            os.getenv("HF_TOKEN")
            or os.getenv("HUGGINGFACEHUB_API_TOKEN")
            or load_config().hf_token
        )

        req = urllib.request.Request(url)
        if token and "huggingface.co" in url:
            req.add_header("Authorization", f"Bearer {token}")

        try:
            with urllib.request.urlopen(req) as resp, open(tmp_path, "wb") as out:
                total = getattr(resp, "length", None) or 0
                downloaded = 0

                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total:
                        progress_cb(downloaded, total)

            tmp_path.rename(self.model_path)

        except urllib.error.HTTPError as e:
            # This is where 401/403/etc. show up
            raise RuntimeError(
                f"Model download failed ({e.code} {e.reason}). "
                "If this is a Hugging Face model, make sure the URL is correct and "
                "that your token is set in Settings (or HF_TOKEN env) and you "
                "have accepted the model's license."
            ) from e

    def switch_model(self, model_id: str) -> None:
        """
        Switch to another model in the registry.
        Caller is responsible for ensuring the model file exists
        (or calling download_model first).
        """
        if model_id == self.model_id:
            return  # already on this model

        registry = get_model_registry()

        if model_id not in registry:
            raise ValueError(f"Unknown AI model id: {model_id}")

        self.model_id = model_id
        self.model_spec = registry[model_id]
        self.model_path = get_model_path(model_id)

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"AI model '{self.model_spec.name}' not found at {self.model_path}."
            )

        # Let the old Llama instance get GC'd
        self._llm = self._create_llm()

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

        return self._run(prompt, max_tokens=2048, temperature=0.2)

    def ask(self, question: str, context: Optional[str] = None) -> str:
        """
        Generic Q&A helper the rest of the app can use.

        `context` can be log output, error messages, or config snippets.
        """
        ctx_txt = ""
        if context:
            ctx = context
            if len(ctx) > 24000:
                ctx = ctx[:24000] + "\n\n[... truncated context ...]\n"
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

        return self._run(prompt, max_tokens=2048, temperature=0.3)


# ---------- Singleton accessor ----------

_engine: Optional[AIEngine] = None
_current_model_id = "phi-3.5-mini-q4"


def get_engine() -> AIEngine:
    """
    Lazy-load a global AIEngine instance.
    """
    global _engine
    global _current_model_id

    if _engine is None:
        _engine = AIEngine(model_id=_current_model_id)
    return _engine


def set_engine_model(model_id: str) -> AIEngine:
    """
    Switch the global engine to a different model id.
    Creates a new AIEngine if needed.
    """
    global _engine
    global _current_model_id

    if _engine is None:
        _current_model_id = model_id
        _engine = AIEngine(model_id=model_id)
        return _engine

    if model_id == _current_model_id:
        return _engine

    _current_model_id = model_id
    _engine.switch_model(model_id)
    return _engine
