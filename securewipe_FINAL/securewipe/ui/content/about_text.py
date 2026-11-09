"""Editable copy for the About page. Change the text here, not in the view code."""

BUILD = "September 2026"

DESCRIPTION = (
    "SecureWipe is a secure data sanitization tool built for IT asset recycling and safe "
    "device disposal. It helps organizations and individuals erase sensitive data from "
    "files, folders and storage devices before they are reused, donated, sold or recycled. "
    "Every completed wipe produces a certificate and an operation log entry."
)

PURPOSE = (
    "Deleting a file or formatting a drive does not remove the data, and recovery tools can "
    "often bring it back. SecureWipe makes permanent erasure simple and trackable, reducing "
    "the risk of data leaks from discarded hardware."
)

STANDARDS = [
    "Sanitization follows NIST SP 800-88 Rev. 1 (Guidelines for Media Sanitization), "
    "\"Clear\" level.",
    "Also supports the DoD 5220.22-M and Gutmann overwrite methods.",
    "Wipe certificates are records of each operation. They are not digitally signed in this version.",
]

BUILT_WITH = "Python  ·  CustomTkinter (interface)  ·  SQLite (database)  ·  Pillow (images)"

TEAM = [
    "Foram Mitesh Shah",
    "Sarea Mathew Lopes",
    "Prajapati Durgawati Bairistar",
]
DEPARTMENT = "Department of Computer Engineering, Government Polytechnic Mumbai"
GUIDE = "Rupali Molawade"

SUPPORT_EMAIL = "teamgpm81@gmail.com"

TEAM_NAME = "Team GPM"
LICENSE_SHORT = f"© 2026 {TEAM_NAME}. Released for academic use only."
# ---- full licence page (About > View license, and the exported PDF) ------------------
LICENSE_TITLE = "Software License"
LICENSE_BADGE = "Academic Project License"
LICENSE_INTRO = (
    "Developed as an academic project at Government Polytechnic Mumbai.\n"
    "Intended for educational use and project demonstration."
)
# (heading, tone, items). Tone: "ok" = light green card, "warn" = orange card.
LICENSE_SECTIONS = [
    ("Permissions", "ok", "check", [
        "Use for learning and demonstration",
        "Review and study the source code",
        "Use within academic submissions",
    ]),
    ("Restrictions", "warn", "alert", [
        "Commercial use requires written permission",
        "Redistribution requires approval from the development team",
        "Do not remove copyright or attribution notices",
    ]),
    ("Warranty & Liability", "ok", "shield", (
        "Provided \"as is\", without warranty. The team is not responsible for data loss "
        "caused by misuse. Verify the target and keep backups before wiping."
    )),
    ("Technology acknowledgements", "ok", "code", [
        "Python", "CustomTkinter", "SQLite", "Pillow",
    ]),
]
LICENSE_TECH_NOTE = "Third-party components retain their respective licenses; refer to their official license texts."
LICENSE_EXPORT_NAME = "SecureWipe_License.pdf"

DISCLAIMER = (
    "SecureWipe permanently destroys data. The developers are not responsible for data lost "
    "through incorrect use. Confirm your target and keep backups of anything you need "
    "before wiping."
)