"""Show a tk.Menu under a widget (grab_release avoids a stuck grab on Windows)."""


def popup_below(menu, widget, dx: int = 0) -> None:
    x = widget.winfo_rootx() + dx
    y = widget.winfo_rooty() + widget.winfo_height() + 4
    try:
        menu.tk_popup(x, y)
    finally:
        menu.grab_release()
