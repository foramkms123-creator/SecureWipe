"""SecureWipe entry point:  python main.py

Any error during start-up is written to data/app.log and shown in a message box, so a launch
that fails is never silent."""
import sys
import tkinter as tk
from tkinter import messagebox

from database.schema import init_db
from services import app_log, settings_service


def main() -> None:
    try:
        init_db()
        settings_service.sync_startup_entry()     # Windows: keep 'start with Windows' correct
        from ui.app import SecureWipeApp
        app = SecureWipeApp()
        app.mainloop()
    except Exception:
        app_log.log_exception("SecureWipe stopped with an error")
        _show_error()
        sys.exit(1)


def _show_error() -> None:
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "SecureWipe",
            "SecureWipe could not start or stopped with an error.\n\n"
            f"Details were saved to:\n{app_log.LOG_FILE}")
        root.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    main()
