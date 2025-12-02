# 📦 **ShellPilot**

*A modern, Textual-powered TUI file manager & shell assistant for Linux power users.*

ShellPilot is a next-generation terminal UI designed for system administrators, developers, and anyone who lives in the shell. Inspired by **Midnight Commander**, **OS/2 Warp**, and modern developer tooling, ShellPilot blends a fast filesystem browser with smart file previews, a built-in action menu, recursive search, session memory, and optional AI-assisted commands.

ShellPilot is engineered to feel *native*, *fast*, and *comfortably Linux-nerdy*.
It’s your terminal cockpit. 🚀🐧

**NOTE**: This is really ALPHA level development still... I have tested it on 1 laptop, with 2 different OS (Fedora 43 and POP!_OS). I am currently using POP!_OS because of the NVIDIA support. I am building out the self hosted, and local AI modules now. If there are errors, or problems, please open an issue. I will get to them as quickly as possible.

---

# ✨ **Features**

### 🗂️ File Browser

* Navigate directories with arrow keys
* Instant directory switching
* Automatic session restore
* Bookmarks (persistent)
* Keyboard shortcuts for common actions
* AI integration (By default disabled)

### 🧠 Smart File Preview

Automatically detects file type and displays the best preview mode:

* **Images** → Rich or Pillow-based inline preview
* **Code** → Syntax highlighting with line numbers
* **Plain text** → Clean text viewer
* **Binary files** → Hex dump preview
* **Compressed files** → Automatic decompression preview support for:

  * `.gz`
  * `.bz2`
  * `.xz`
  * `.zip` (coming soon)

### 🔍 Powerful Search

* Fuzzy filename search
* Real-time filtering
* **Recursive search** option (configurable)
* Supports wildcards (`*`, `?`) and regex toggle (future)

### 🛠️ Action Menu

Right-side context menu includes:

* View file
* Edit file (external editor launch)
* Copy / Move / Delete
* Rename
* View metadata
* Safe Trash (with restore)
* More coming soon…

### 🗑️ Safe Trash System

Deletion never touches your filesystem directly.
Files are moved to a private **ShellPilot trash directory** with:

* Timestamps
* Metadata
* One-click restore
* Empty trash option

### 🔧 Shell Command Integration

ShellPilot integrates with system utilities:

* `ls` generator
* `file` (future)
* `stat`
* Permissions viewer
* Owner/group resolution

Coming soon:

* Built-in mini terminal
* Command palette
* AI command suggestions

### 🎨 Image & Rich Media Support

If **Pillow** is installed, images are rendered beautifully inline.
Otherwise, ShellPilot falls back to simple info mode.

### 🗄️ Session Memory

ShellPilot remembers:

* Last visited directory
* Bookmarks
* Filter settings
* Future: layout + panel state

### 🪶 Lightweight & Fast

No Electron bloat.
No GUI overhead.
Just **Textual + Rich** doing what they do best.

---

# 📁 **Project Structure**

Example layout (yours will evolve):

```
ShellPilot/
├── shellpilot/
│   ├── ai/
│   │   ├── config.py
│   │   ├── engine.py
│   │   ├── models.py
│   │   └── remote.py
│   ├── core/
│   │   ├── commands.py
│   │   ├── fs_browser.py
│   │   ├── git.py
│   │   └── search.py
│   ├── ui/
│   │   ├── action_menu.py
│   │   ├── app.py
│   │   ├── app.tcss
│   │   ├── search_bar.py
│   │   ├── settings.py
│   │   └── widgets.py
│   ├── utils/
│   │   ├── log_highlighter.py
│   │   ├── ls_colors.py
│   │   ├── preview.py
│   │   └── shell.py
├── models/
│   └── (empty by default - use action menu to download models)
├── README.md
├── requirements.txt
├── .gitignore
├── models.json
└── main.py
```

---

# 🚀 **Getting Started**

### Prerequisites

* Python **3.10** or later
* Linux (recommended)
* Optional:

  * **Pillow** → image previews
  * **Ripgrep** → future fast recursive search

### Installation

Clone the repo:

```bash
git clone https://github.com/girls-whocode/ShellPilot.git
cd ShellPilot
```

(If you have a virtual environment)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# ▶️ **Run ShellPilot**

```
python main.py
```

or if you want to install it as a system command later:

```bash
pip install .
shellpilot
```

---

# ⌨️ Keybindings

| Key   | Action                                 |
| ----- | -------------------------------------- |
| ↑ / ↓ | Navigate entries                       |
| →     | Enter directory / open action menu     |
| ←     | Go up one directory                    |
| `?`   | Toggle Help Menu                       |
| `:`   | Action Command Menu                    |
| `/`   | Search / Filter (advanced & recursive) |
| `h`   | Jump to Home Directory                 |
| `t`   | Trash (recovery)                       |
| `del` | Delete file or folder to Trash         |
| `^b`  | Bookmark folder                        |
| `^j`  | Next Bookmark folder                   |
| `^,`  | Open Settings Menu                     |
| `a`   | Open AI explain                        |
| `e`   | Bookmark folder                        |
| `q`   | Quit                                   |

More are being added continuously.

---

# 🧩 **Roadmap**

### 0.3.x — Core Enhancements

* Editor integration (nano/vim/micro detection)
* Multi-pane layout
* Clipboard support
* Improved hex viewer
* File diffing

### 0.4.x — Power Tools

* Embedded mini-terminal
* Command palette
* Plugin architecture
* Keyboard macro support

### 0.5.x — AI Mode

* Optional LLM-powered:

  * Command explanations
  * Command generation
  * Help mode (“what does this file do?”)
  * System troubleshooting

### 1.0 — "Full Flight Deck" Release

* Multi-panel layout (classic MC style)
* Split horizontal/vertical panels
* Drag-and-drop inside TUI
* Config-driven theming
* Installer package (.rpm / .deb)

---

# 🧪 Testing

Run all tests:

```bash
pytest
```

---

# 🐛 Issues & Contributions

Feedback and contributions are welcome!

Please open an issue for:

* Bugs
* Feature requests
* Ideas
* UI adjustments
* TUI performance problems

Pull requests are very welcome — especially for:

* New file preview handlers
* Action menu improvements
* Recursive search enhancements
* Code cleanup / refactors

---

# 📝 License

MIT License — free to use, modify, and build upon.
