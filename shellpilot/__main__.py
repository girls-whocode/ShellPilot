# shellpilot/__main__.py
from shellpilot.ui.app import ShellPilotApp  # or whatever your App class is called

def main() -> None:
    app = ShellPilotApp()
    app.run()

if __name__ == "__main__":
    main()
