# 📦 **ShellPilot**
[![CI](https://github.com/girls-whocode/ShellPilot/actions/workflows/ci.yml/badge.svg)](https://github.com/girls-whocode/ShellPilot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Status](https://img.shields.io/badge/status-alpha-orange.svg)

<p align="right">
  <img src="assets/logo-shellpilot.svg" alt="ShellPilot Logo" width="420" />
</p>

*A modern, Textual-powered TUI file manager & shell assistant for Linux power users.*

ShellPilot is a next-generation terminal UI designed for system administrators, developers, and anyone who lives in the shell. Inspired by **Midnight Commander**, **OS/2 Warp**, and modern developer tooling, ShellPilot blends a fast filesystem browser with smart file previews, a built-in action menu, recursive search, session memory, and optional AI-assisted commands.

It’s engineered to feel *native*, *fast*, and unashamedly Linux-nerdy.
Your terminal cockpit. 🚀🐧

> **Note:** ShellPilot is in *ALPHA*. Tested on POP!_OS and Fedora 43.
> If you find bugs (you will), please open an issue!

---

# 🧬 **What Is ShellPilot (In One Sentence)?**

**ShellPilot is a Textual-based terminal file manager and intelligent shell assistant built for speed, safety, and AI-augmented workflows — all inside your terminal.**

---

## 🖼️ Screenshots

<p align="center">
  <img src="docs/img/shellpilot-main.png" alt="ShellPilot main file browser view" width="800" />
</p>

<p align="center">
  <img src="docs/img/shellpilot-preview.png" alt="ShellPilot smart file preview" width="800" />
</p>

<p align="center">
  <img src="docs/img/shellpilot-ai.png" alt="ShellPilot AI explanation mode" width="800" />
</p>

# ✨ **Features**

### 🗂️ File Browser

* Fast directory navigation
* Instant switching
* Persistent bookmarks
* Automatic session restore
* Optional AI insights

### 🧠 Smart File Preview

ShellPilot automatically detects the best way to render files:

* **Images** → inline preview (Pillow)
* **Source code** → syntax-highlighted view
* **Text files** → clean pager
* **Binary files** → hex dump
* **Compressed files:**

  * `.gz`, `.bz2`, `.xz`
  * `.zip` (coming soon)

### 🔍 Powerful Search

* Fuzzy search
* Real-time filtering
* **Recursive search** (configurable)
* Supports `*`, `?`, and future regex mode

### 🛠️ Action Menu

* View
* Edit (external editor)
* Copy
* Move
* Delete (safe)
* Rename
* View metadata
* More tools coming…

### 🗑️ Safe Trash Mode

Files aren't deleted. They're moved to:

```
~/.config/shellpilot/trash/
```

Includes:

* Metadata
* Timestamp
* Restore option
* Empty trash

### 🔧 Shell Integration

* `ls` generator
* `stat` viewer
* Owner/group lookup
* Permissions breakdown

Upcoming:

* Embedded mini-terminal
* Command palette
* AI command suggestions

### 🎨 Media Support

* Fancy image rendering when Pillow is installed
* Falls back gracefully when not

### 🗄️ Persistent Session Memory

ShellPilot remembers:

* Last directory
* Bookmarks
* Search filters
* Layout (future)
* Theme (upcoming)

### 🪶 Lightweight & Fast

Just **Textual + Rich**.
No Electron. No bloat. No nonsense.

---

# ⚙️ **Configuration Files**

ShellPilot stores user data in:

```
~/.config/shellpilot/
```

Contents:

| File             | Purpose                                                |
| ---------------- | ------------------------------------------------------ |
| `config.json`    | General settings (recursive search, AI settings, etc.) |
| `bookmarks.json` | Persistent bookmarks                                   |
| `state.json`     | Session restoration                                    |
| `models.json`    | AI model definitions                                   |
| `settings/`      | Future expansion                                       |

All human-friendly JSON. No surprises.

---

# 🤖 **AI Support (Optional)**

ShellPilot has three AI operation modes:

### 1. Local GGUF Models

Runs with `llama-cpp-python`.

Recommended:

* Phi-3.1 / Phi-3.5
* Llama 3.1 Distill
* Q4 models
* 4+ CPU cores
* 3–8GB RAM depending on model

### 2. Remote AI (OpenAI-Compatible)

Works with:

* vLLM
* DeepSeek
* OpenAI
* Anything with `/v1/chat/completions`

### 3. Disabled (Default)

Pure file manager mode.

---

# 🎯 **Design Philosophy**

ShellPilot is built around:

* **Speed** → immediate feedback
* **Predictability** → no destructive operations
* **Extensibility** → easy to add handlers or actions
* **Minimalism** → stays out of your way
* **Observability** → clear status messages, AI activity logs, and safe operations

---

# 🧩 **Future Extension Hooks**

Upcoming plugin-style extension points:

* Custom preview handlers
* Custom ActionMenu actions
* Custom AI analysis engines
* Search strategy modules
* Panel layout extensions
* Customizable Colors for Users

---

# 👩‍💻 **Developer Quickstart**

```bash
git clone https://github.com/girls-whocode/ShellPilot
cd ShellPilot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --dev
```

Important entry points:

| Component      | File                           |
| -------------- | ------------------------------ |
| UI / Main App  | `shellpilot/ui/app.py`         |
| AI Engine      | `shellpilot/ai/engine.py`      |
| Preview System | `shellpilot/utils/preview.py`  |
| Search Logic   | `shellpilot/core/search.py`    |
| Action Menu    | `shellpilot/ui/action_menu.py` |

---

# 🚀 **Getting Started**

### Requirements

* Python 3.10+
* Linux terminal
* Optional: Pillow, Ripgrep

### Install

```bash
git clone https://github.com/girls-whocode/ShellPilot.git
cd ShellPilot
pip install -r requirements.txt
```

### Run

```bash
python main.py
```

Install as a system command:

```bash
pip install .
shellpilot
```

---

# ⌨️ **Keybindings**

| Key   | Action                        |
| ----- | ----------------------------- |
| ↑ / ↓ | Navigate                      |
| →     | Action menu / enter directory |
| ←     | Up one directory              |
| /     | Search                        |
| :     | Action command palette        |
| a     | AI explain                    |
| h     | Home                          |
| del   | Safe delete                   |
| t     | Trash manager                 |
| ^b    | Bookmark                      |
| ^j    | Next bookmark                 |
| ^,    | Settings                      |
| ?     | Help                          |
| q     | Quit                          |

---

# 🧩 **Roadmap**

### 0.3.x — Core Enhancements

* Editor integration
* Multi-pane
* Clipboard
* Hex viewer upgrade
* File diff

### 0.4.x — Power Tools

* Command palette
* Plugin framework
* Macro engine
* Built-in terminal

### 0.5.x — AI Mode

* File analysis
* Command explanations
* Troubleshooting guidance
* “What does this file do?” mode

### 1.0 — Flight Deck Release

* Multi-panel UI
* Themes
* Installers (`.rpm`, `.deb`)
* Draggable elements
* Full customization

---

# 🚧 **Known Issues (Alpha)**

* Some terminals have small rendering quirks
* Pillow required for image preview
* Large models require more RAM
* Multi-pane mode still in development
* Settings UI is evolving

---

# 🧪 **Testing**

```bash
pytest
```

---

# 🐛 **Issues & Contributions**

Contributions are *very* welcome!

Good areas to contribute:

* Preview handlers
* Search improvements
* Performance enhancements
* Abstracted keyboard actions
* AI tooling
* UI improvements
* Docs & examples

Please open an issue for:

* Bugs
* Ideas
* UX suggestions
* Performance problems

---

# 💖 **Support**

A sponsor link can go here later — open source takes time and caffeine.

---

# 📝 **License**

MIT License — build cool things and share freely.
