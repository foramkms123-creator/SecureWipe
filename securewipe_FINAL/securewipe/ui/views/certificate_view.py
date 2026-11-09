"""One Certificate of Destruction: preview, Back, and Download as PDF.

Opened from Reports ("View Report") or right after a certificate is generated on the
Algorithms page."""
from tkinter import filedialog, messagebox

import customtkinter as ctk

from services import certificate, report_service
from services import settings_service as sp
from services.auth_service import User
from ui.components.scroll_frame import ScrollFrame
from ui.icons import icon
from ui.light import Box, Label
from ui.theme import C, font

PREVIEW_WIDTH = 940


class CertificateView(ctk.CTkFrame):
    title = "Certificate"

    def __init__(self, master, user: User, op_id: int, on_back):
        super().__init__(master, fg_color="transparent")
        self._cert = report_service.get_certificate(user, op_id)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        bar = Box(self)
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        bar.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(bar, text="←  Back to reports", height=40, corner_radius=10,
                      font=font(13, bold=True), fg_color=C["surface"], text_color=C["green_dark"],
                      border_width=1, border_color=C["green_dark"],
                      hover_color=C["green_light"], command=on_back
                      ).grid(row=0, column=0, sticky="w")
        if self._cert is not None:
            Label(bar, text=self._cert.certificate_id, size=13, bold=True, color=C["muted"],
                  bg=C["bg"]).grid(row=0, column=1, sticky="w", padx=16)
            ctk.CTkButton(bar, text="  Download PDF", image=icon("document", "#FFFFFF", 18),
                          compound="left", height=40, corner_radius=10, font=font(13, bold=True),
                          fg_color=C["green_dark"], hover_color=C["green_dark_hover"],
                          command=self._download).grid(row=0, column=2, sticky="e")

        scroll = ScrollFrame(self, bg=C["bg"])
        scroll.grid(row=1, column=0, sticky="nsew")
        if self._cert is None:
            Label(scroll.inner, text="This certificate is not available for your account.",
                  size=14, italic=True, color=C["muted"]).pack(pady=60)
            return
        width = PREVIEW_WIDTH
        img = certificate.preview(self._cert, width)
        self._image = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        card = Box(scroll.inner, bg=C["surface"])
        card.pack(pady=(0, 16), padx=6)
        ctk.CTkLabel(card, text="", image=self._image).pack(padx=16, pady=16)

    def refresh(self) -> None:
        """Nothing changes on a certificate once it is issued."""

    def _download(self) -> None:
        if self._cert is None:
            return
        folder = sp.reports_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            folder = None                           # fall back to the dialog's default folder
        path = filedialog.asksaveasfilename(
            title="Save certificate as PDF", defaultextension=".pdf",
            initialdir=str(folder) if folder else None,
            initialfile=f"{self._cert.certificate_id}.pdf",
            filetypes=[("PDF document", "*.pdf")])
        if not path:
            return
        try:
            certificate.save_pdf(self._cert, path)
        except OSError as exc:
            messagebox.showerror("Could not save the certificate", str(exc))
            return
        messagebox.showinfo("Certificate saved", f"Saved as:\n{path}")
