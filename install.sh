#!/usr/bin/env bash

set -e

echo "🚀 Installing ShellPilot..."

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3.10+ required!"
    exit 1
fi

# Create venv if missing
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate it
echo "🔧 Activating environment..."
source .venv/bin/activate

# Install requirements
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✨ Installation complete!"
echo "Run ShellPilot with:  source .venv/bin/activate && python main.py"
echo "Happy coding! 💻"