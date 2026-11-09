"""Editable copy for the Help page. Change the text here, not in the view code."""

INTRO = (
    "Quick answers to common questions about SecureWipe. "
    "If your question is not listed here, contact our team by email."
)

SUPPORT_EMAIL = "teamgpm81@gmail.com"

FAQS = [
    (
        "What is SecureWipe?",
        "SecureWipe permanently erases files, folders and drives so the data cannot be "
        "recovered with common recovery tools. Each completed wipe produces a certificate "
        "that you can open from Reports.",
    ),
    (
        "How do I wipe a file, folder or drive?",
        "Click \"+ New Erasure Task\" in the left menu and choose File, Folder or Drive. "
        "Pick a method and the number of passes, then start the wipe. Keep the computer "
        "on until the wipe finishes.",
    ),
    (
        "Which wipe method should I choose?",
        "Zero Fill writes zeros, One Fill writes ones and Random Data writes random bytes. "
        "Use more passes for more overwriting, but note that more passes take longer.",
    ),
    (
        "Can I stop a wipe after it has started?",
        "Yes. Press \"Stop\" on the Algorithms page and confirm. The target is then "
        "only partly wiped, and the wipe is recorded as Cancelled in Reports.",
    ),
    (
        "Where can I find my wipe certificates?",
        "Open Reports in the left menu. Each finished wipe is listed there, and you can "
        "open its certificate from the list.",
    ),
    (
        "Why does an SSD need extra care?",
        "On SSDs, USB flash drives and memory cards, overwriting may not reach every stored "
        "copy of the data. SecureWipe does not detect these drive types yet, so it cannot warn you "
        "about them. For the most reliable "
        "result, use the drive manufacturer's secure erase tool.",
    ),
    (
        "How do I change my password?",
        "Open Settings and use the change password option. Enter your current password, "
        "then the new one.",
    ),
]
