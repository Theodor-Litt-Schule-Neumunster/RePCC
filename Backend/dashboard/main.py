# pyinstaller --noconfirm --onefile --noconsole --add-data "assets;assets" --icon="./assets/repccBin.ico" main.py

import argparse
import sys

from PyQt5.QtWidgets import QApplication

from app_window import AppWindow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RePCC Dashboard")
    parser.add_argument("--home", action="store_true", help="Open home page")
    parser.add_argument("--settings", action="store_true", help="Open settings page")
    parser.add_argument("--macros", action="store_true", help="Open macros page")
    parser.add_argument("--devices", action="store_true", help="Open devices page")
    parser.add_argument("--credits", action="store_true", help="Open credits page")
    # Ignore extra arguments that can be injected by tray/OS launch contexts.
    args, _unknown = parser.parse_known_args()
    return args


def resolve_start_page(args: argparse.Namespace) -> str:
    if args.settings:
        return "settings"
    if args.macros:
        return "macros"
    if args.devices:
        return "devices"
    if args.credits:
        return "credits"
    return "home"


def main() -> int:
    args = parse_args()
    app = QApplication(sys.argv)
    window = AppWindow(start_page=resolve_start_page(args))
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
