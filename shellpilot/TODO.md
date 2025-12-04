# ShellPilot TO DOs

1. Action Menu `:`
    * aimodel - More information needs to be displayed. It is difficult to currently understand what is available
    * mv, rename, cp, stat, plus many others need to be setup and working
    * Tab will auto fill command line

2. Beginner Help
3. AI Mode Command Helper
4. Better documentation
5. Better AI Prompts
6. Config tokens
7. Modular Add-Ons
8. Plugins - Community Built
9. LS COLORS fix (default are too dark for dark screens)


10. AI Chat mode, allow users to ask questions about different items

# 🧠 ShellPilot – AI Copilot / "Sentra" Roadmap

> Goal: Transform ShellPilot from a smart file manager into a system-aware AI copilot
> that can answer questions, inspect projects, safely modify user config, and help
> keep Linux systems healthy – **without** turning into a generic voice assistant or
> a root-level foot-gun.


## Legend

- ✅ = Completed
- ☐ = Not started / In progress
- [AI] = Requires AI integration (LLM)
- [SAFE] = Touches safety / permissions / backups
- [UI] = Textual UI work
- [CORE] = Core architecture / refactors


---

## Phase I – Foundation: AI Chat & Safety Rails

> Establish the core AI chat mechanism, tool registry, and safe file system layer.
> Sentra should be able to *talk*, *inspect*, and *suggest* before it ever edits.


### Tranche 1.1 – Basic AI Chat Mode (Read-Only)

**Goal:** Add an AI chat interface that can answer conceptual questions and use basic context (cwd, file list) without touching the filesystem.

#### Milestone 1.1.1 – AI Chat Screen / Pane [UI]

- ☐ Create `AIChatView` (e.g. `shellpilot/ui/ai_chat_view.py`)
  - ☐ Scrollable chat log
  - ☐ Input line at bottom (`Input.Submitted` handler)
- ☐ Wire `AIChatView` into `ShellPilotApp`
  - ☐ Add keybinding (e.g. `Ctrl+A`) or command (`:ai`) to open/close
- **Acceptance criteria:**
  - User can open AI chat from ShellPilot.
  - User can send a message and see a response (even if it’s generic).
  - No crash when AI is disabled/unconfigured.

#### Milestone 1.1.2 – AIChatManager Skeleton [CORE] [AI]

- ☐ Create `AIChatManager` class (e.g. `shellpilot/ai/chat.py`)
  - ☐ `__init__(ai_engine, app_ref)`
  - ☐ `async def ask(self, question: str) -> str`
- ☐ Connect `AIChatView` to `AIChatManager.ask()`
- ☐ Use existing `AIEngine` for completions
  - ☐ Basic system prompt: "You are an AI embedded in ShellPilot..."
  - ☐ Include `cwd` and small file list in every prompt
- **Acceptance criteria:**
  - AI answers reflect current directory path and visible items.
  - No write operations are performed anywhere (read-only).

---

### Tranche 1.2 – Tool Registry & Context Management

**Goal:** Give the AI a structured understanding of what tools it *could* use, even if we initially hard-code usage on the Python side.

#### Milestone 1.2.1 – Define Tool Registry Structure [CORE]

- ☐ Create a `tools.py` module or similar (e.g. `shellpilot/ai/tools.py`)
- ☐ Define a `Tool` dataclass:
  - ☐ `name`
  - ☐ `description`
  - ☐ `callable` (Python function)
  - ☐ `args_schema` (optional, for future structured invocations)
- ☐ Register core read-only tools:
  - ☐ `basic_context` → cwd + directory listing
  - ☐ `read_file(path, max_bytes)`
  - ☐ `run_shell(command)` (restricted)
  - ☐ `get_system_info()`
- **Acceptance criteria:**
  - There is a single registry where all AI-callable tools are listed.
  - Tools are callable from a unit test without involving the UI.

#### Milestone 1.2.2 – Prompted Tool Awareness [AI]

- ☐ Extend system prompt to include **tool manifest** description:
  - ☐ Name + brief description of each tool
  - ☐ Guidelines: "Do not invent tools; only use those listed."
- ☐ Add lightweight routing logic in `AIChatManager`:
  - ☐ For now, simple Python-side selection (e.g. keyword-based)
  - ☐ Always include `basic_context` tool output
- **Acceptance criteria:**
  - AI answers can mention local context (files, cwd) based on tool output.
  - No modifying tools exist yet; everything is still read-only and safe.


---

### Tranche 1.3 – SafeFS: Safe Filesystem & Backup Layer [SAFE] [CORE]

**Goal:** Centralize all **AI-driven** file reads/writes into a SafeFS layer with backups and path validation.

#### Milestone 1.3.1 – SafeFS Read & Path Validation

- ☐ Create `SafeFS` class (e.g. `shellpilot/ai/safefs.py`):
  - ☐ `read_text(path, max_bytes)`
  - ☐ `exists(path)`
  - ☐ `is_safe(path, home, project_root)`
- ☐ Implement `is_safe` rules:
  - ☐ Only paths under `$HOME`
  - ☐ No symlinks (or explicit handling if allowed)
  - ☐ Explicit allowlist:
    - `$HOME/.bashrc`, `.zshrc`, `.profile`
    - `$HOME/.config/shellpilot/**`
    - `$HOME/.local/share/shellpilot/**`
    - Project root + children for current session
- **Acceptance criteria:**
  - Unsafe paths (e.g. `/etc/passwd`) are rejected.
  - Attempt to read unsafe path returns a controlled error, not a crash.

#### Milestone 1.3.2 – Backup & Retention Policy

- ☐ Define backup directory:
  - ☐ `~/.local/share/shellpilot/backups/`
- ☐ Implement:
  - ☐ `backup(path) -> backup_path`
    - ☐ Timestamp-based filename
    - ☐ Per-original-file directory (e.g. `.bashrc/2025-12-04T...bak`)
  - ☐ Retention logic (can be simple v1):
    - ☐ Keep all for last 7 days
    - ☐ Keep older backups up to 90 days with thinning (e.g. daily/weekly)
- ☐ Add `:ai-restore FILE` or dev-only script for manual restoration
- **Acceptance criteria:**
  - Before any write, a backup is created.
  - Backups are visible on disk and restorable by a basic script.


---

### Tranche 1.4 – Root vs User Modes & Safety Rules [SAFE] [CORE]

**Goal:** Make AI behavior mode-aware: non-root = full Sentra, root/sudo = read-only adviser.

#### Milestone 1.4.1 – User Mode Detection

- ☐ Add helper to detect:
  - ☐ `current_uid`
  - ☐ `username`
  - ☐ `home directory`
- ☐ Pass user info into AI system prompt:
  - ☐ "Current user: {username}, home: {home}, uid: {uid}"
- **Acceptance criteria:**
  - AI can refer to user and home dir in context.
  - No behavioral changes yet; just awareness.

#### Milestone 1.4.2 – Root Read-Only Mode

- ☐ Implement rule: if `uid == 0` (root):
  - ☐ AI tools that write are disabled
  - ☐ SafeFS refuses writes regardless of path
- ☐ UI indicator:
  - ☐ Status bar text: `AI Mode: READ-ONLY (root)`
- ☐ Error messaging:
  - ☐ If a write is attempted under root, return a structured error:
    - "AI cannot modify files while running as root. Here is what you could change manually..."
- **Acceptance criteria:**
  - Running ShellPilot via `sudo` = AI never writes to disk.
  - AI still explains configs and suggests patches/commands.

---

### Tranche 1.5 – AI Contract & Prompt Design [AI] [CORE]

**Goal:** Lock in the behavioral contract for Sentra so it’s consistent and non-chaotic.

#### Milestone 1.5.1 – System Prompt v1

- ☐ Define a dedicated system prompt for AI Chat:
  - ☐ Identity: "You are an embedded ShellPilot AI, not a generic assistant."
  - ☐ Personality: experienced Linux sysadmin, concise and opinionated.
  - ☐ Rules:
    - ☐ Prefer local/system context over generic answers.
    - ☐ Do not fabricate files or tools.
    - ☐ For config changes, prefer small, minimal diffs.
    - ☐ For root mode: advisory-only.
- ☐ Store prompt text in a dedicated file (`ai_system_prompt.md` or config)
- **Acceptance criteria:**
  - AI responses reference local context, not random web-like fluff.
  - Prompt is easy to iterate without code changes.

#### Milestone 1.5.2 – Question Classification (Generic / Project / System)

- ☐ Implement a small classifier step (can be LLM-based):
  - ☐ `generic` → knowledge only (no tools required except basic context)
  - ☐ `project` → project files, TODOs, git status
  - ☐ `system` → logs, disk, system info
- ☐ Route tool usage based on class:
  - ☐ `generic` → minimal context
  - ☐ `project` → include project files, TODOs, git status
  - ☐ `system` → include system info, logs where appropriate
- **Acceptance criteria:**
  - "What is a symlink?" → generic answer.
  - "What should I do next in this repo?" → project tools used.
  - "Are there boot issues?" → system tools/logs queried.

---

## Phase II – Project Intelligence (Per-Directory Sentra)

> Teach Sentra to understand repos, TODOs, and project structure, and propose next steps.


### Tranche 2.1 – Project Context & Indexing

#### Milestone 2.1.1 – Project Root Detection

- ☐ Implement `get_project_root(cwd)`:
  - ☐ Prefer Git repo root (if `.git/` found)
  - ☐ Fallback to cwd
- ☐ Use project root in:
  - ☐ SafeFS `is_safe` decisions for project files
  - ☐ Context building for AI
- **Acceptance criteria:**
  - In a Git repo, Sentra treats repo root as main context.
  - Outside repos, cwd acts as project root.

#### Milestone 2.1.2 – Project Index Generation [AI]

- ☐ Command: `:ai-index-project`
- ☐ Steps:
  - ☐ Scan for key files:
    - `README*`, `TODO*`, `pyproject.toml`, `requirements.txt`, `package.json`, `Dockerfile`, etc.
  - ☐ Read small snippets (truncated).
  - ☐ Send to AI with instruction: "Summarize project and list 3–5 next logical tasks."
  - ☐ Save to `.shellpilot-ai/project_index.json` under project root
- **Acceptance criteria:**
  - Project index exists after running the command.
  - File contains summary + recommended next steps in JSON format.

---

### Tranche 2.2 – Purposeful Project Q&A

#### Milestone 2.2.1 – “What should I work on next?” [AI]

- ☐ For project-level questions, include:
  - ☐ `project_index.json` (if present)
  - ☐ TODO file (if present)
  - ☐ `git status --short --branch` output
- ☐ AI response should:
  - ☐ Reference-to project summary
  - ☐ Suggest 1–3 concrete next actions
- **Acceptance criteria:**
  - "What should my next TODO be?" yields a useful, project-specific suggestion.
  - Response mentions actual TODO items or git changes.

#### Milestone 2.2.2 – File-Level Explanations

- ☐ Add an AI action from file preview:
  - ☐ e.g. keybinding `A` → "Explain this file"
- ☐ Tools:
  - ☐ Use SafeFS to read file (with size limits)
  - ☐ AI explains function, purpose, or structure
- **Acceptance criteria:**
  - On a Python file, AI can summarize what the script does.
  - On config files, AI describes key settings in plain language.

---

## Phase III – System Intelligence (Health & Logs)

> Let Sentra act as a lab assistant that understands system health, logs, and boot issues.


### Tranche 3.1 – System Snapshot

#### Milestone 3.1.1 – Snapshot Command & Storage

- ☐ Add command: `:ai-scan-system`
- ☐ Collect:
  - ☐ `/etc/os-release` info
  - ☐ `uname -a`
  - ☐ `df -h`
  - ☐ `lsblk`
  - ☐ `systemctl --failed`
  - ☐ `journalctl -b -p warning --no-pager | tail -n 200`
- ☐ Summarize into JSON and save as:
  - ☐ `~/.config/shellpilot/ai/system_snapshot.json`
- **Acceptance criteria:**
  - `system_snapshot.json` exists and is readable.
  - Contains clear, structured summary of system state.

#### Milestone 3.1.2 – "Is my system healthy?" [AI]

- ☐ For questions like:
  - ☐ "Is my system generally healthy?"
  - ☐ "Anything I should fix soon?"
- ☐ Include `system_snapshot.json` in AI context.
- **Acceptance criteria:**
  - AI points out real, specific items (low disk, failed services).
  - If snapshot is outdated, AI suggests running `:ai-scan-system`.

---

### Tranche 3.2 – Log & Security Insight

#### Milestone 3.2.1 – Failed Login Attempts Tool [SAFE]

- ☐ Implement `get_failed_logins()` tool:
  - ☐ Prefer `journalctl` (sshd/auth) with `--since 24 hours ago`
  - ☐ Fallback to `/var/log/auth.log` or `/var/log/secure` (read-only)
  - ☐ Handle permission errors gracefully:
    - Return instructions for using `sudo` and pasting results instead
- **Acceptance criteria:**
  - AI can summarize failed login attempts when permissions allow.
  - When not allowed, AI gives clear manual instructions.

#### Milestone 3.2.2 – Boot Issues Tool [SAFE]

- ☐ Implement `get_boot_issues()`:
  - ☐ `journalctl -b -p warning` or `-p err`
  - ☐ Truncate to last N lines
  - ☐ Same permission-handling as above
- **Acceptance criteria:**
  - AI can answer “Are there any boot issues?” with a summarised set of real errors/warnings.
  - Permission issues handled without crashing.

---

## Phase IV – Safe Config Editing & Dotfile Surgery

> Give Sentra "hands" in the home directory, with strict safety and full backup.


### Tranche 4.1 – Patch-Based Editing

#### Milestone 4.1.1 – Diff Application Engine [SAFE]

- ☐ Implement a diff/patch helper:
  - ☐ Accept unified diff format
  - ☐ Apply to existing file content
  - ☐ Fail gracefully if patch can’t be applied cleanly
- ☐ Integrate with `SafeFS`:
  - ☐ `apply_patch(path, diff) -> success/error`
  - ☐ Always backup before write
- **Acceptance criteria:**
  - Unit tests can:
    - Apply a simple patch to a text file
    - Verify backup was created
    - Verify resulting file matches expected content

#### Milestone 4.1.2 – ShellPilot-Managed Blocks

- ☐ Define block markers:
  - ☐ `# >>> shellpilot-managed: <name> >>>`
  - ☐ `# <<< shellpilot-managed: <name> <<<`
- ☐ Rules:
  - ☐ AI can create new blocks in safe files.
  - ☐ AI can modify **only** content inside these markers for later edits.
  - ☐ Non-shellpilot sections should only be *appended to*, not rewritten.
- **Acceptance criteria:**
  - AI-generated patches that touch outside ShellPilot blocks are rejected or require explicit manual confirmation.
  - Existing ShellPilot blocks can be updated cleanly.

---

### Tranche 4.2 – Auto-Venv Setup (First Real Edit Use Case)

#### Milestone 4.2.1 – Auto-Venv Design [AI] [SAFE]

- ☐ Decide behavior:
  - ☐ Hook into `cd` function in `.bashrc` (or `.zshrc` later)
  - ☐ If `.venv/bin/activate` or `venv/bin/activate` exists, source it on entering directory
- ☐ Prompt AI with:
  - ☐ Current `.bashrc` content (truncated)
  - ☐ Instruction to output unified diff adding a `shellpilot-managed` block
- **Acceptance criteria:**
  - Diff only adds a clearly-marked ShellPilot block.
  - No unrelated bashrc content is altered.

#### Milestone 4.2.2 – UX: Confirm & Apply

- ☐ When the user asks:
  - ☐ "Can you set up automatic venv activation?"
- Steps:
  - ☐ AI proposes diff.
  - ☐ Show diff in UI:
    - ☐ Confirmation prompt (Y/n)
  - ☐ If yes:
    - ☐ `SafeFS.backup` + `SafeFS.apply_patch`
- **Acceptance criteria:**
  - After confirmation, `.bashrc` includes the ShellPilot block.
  - `cd` into a project with `.venv` auto-activates environment.
  - Backups exist and can roll back changes.

---

## Phase V – Extended Skills & Autonomy (Optional / Future)

> Let Sentra chain actions, manage more config, and feel more like Tony Stark’s lab assistant.


### Tranche 5.1 – Skill Registry & Chained Actions

#### Milestone 5.1.1 – Skills as First-Class Concepts

- ☐ Represent “skills” as high-level operations:
  - ☐ `failed_logins_report`
  - ☐ `boot_health_check`
  - ☐ `auto_venv_setup`
  - ☐ `alias_management`
- ☐ Each skill maps to:
  - ☐ Underlying tools
  - ☐ Preconditions & safety rules
  - ☐ Optional user confirmations
- **Acceptance criteria:**
  - New skills can be added declaratively without rewriting core logic.

#### Milestone 5.1.2 – Multi-Step Plans (Controlled)

- ☐ Allow AI to propose **short plans**:
  - ☐ Inspect something -> suggest action -> ask permission -> perform action
- ☐ Hard limits:
  - ☐ Max steps (e.g. 2–3 per user request)
  - ☐ No destructive commands
- **Acceptance criteria:**
  - AI can say: "I checked X and Y. With your permission, I can now apply Z."
  - No unprompted multi-step edits.

---

## Developer Notes & Guardrails

- Always route **all AI-originated writes** through `SafeFS`.
- Always display a diff for config changes to user-owned dotfiles.
- For root/sudo:
  - AI must never write to disk.
  - Must provide clear manual instructions instead.
- For any ambiguity in safety:
  - Prefer "explain and suggest" over "edit and pray".

