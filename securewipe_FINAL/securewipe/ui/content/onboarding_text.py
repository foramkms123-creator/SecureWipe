"""Editable copy for the introduction and permissions screens."""

INTRO_TITLE = "Before you begin"
INTRO_LEAD = (
    "SecureWipe permanently erases files, folders and whole drives by overwriting the "
    "data with established sanitization methods, so ordinary recovery tools cannot recover it. "
    "Recovery is impractical under the Clear-level threat model."
)

INTRO_SECTIONS = [
    ("What SecureWipe does", [
        "Overwrites data using Zero Fill,One Fill, Random Data, DoD 5220.22-M or Gutmann (35 passes).",
        "Lets you pick the number of passes for Zero Fill and Random Data.",
        "Starts each wipe with the default method set in Settings (DoD 5220.22-M). You choose the method for each wipe.",
        "Detects USB drives as soon as they are connected.",
        "Issues a Certificate of Destruction for a completed wipe, saved as PDF. It is a record, not a digitally signed proof.",
        "Records every operation in an audit log visible from the dashboard.",
    ]),
    ("What it needs", [
        "Windows 10/11 ",
        "Administrator (Windows) rights for drive-level wiping.",
        "Read and write access to the files, folders and devices you select.",
        "Free space for the database, audit log and certificates (about 50 MB).",
        "External devices connected(only pendrive), unlocked and not in use by another program.",
    ]),
    ("Limitations", [
        "Wiping is permanent. Wiped data cannot be restored by SecureWipe or anyone else.",
        "On USB flash overwriting cannot reach spare or remapped cells. "
        "Use the drive's built-in sanitize command for a certifiable result.",
        "File and folder wiping is best effort: file-system journals, shadow copies and cloud-sync "
        "copies may keep older versions of the data.",
        "The drive Windows running from cannot be wiped while in use.",
        "Items that cannot be read when the wipe is set up are skipped, and the wipe is reported as 'Success with limitations'. "
        "Damaged sectors may not accept new data; a write error makes the wipe fail, and it is reported as Failed.",
        "Wipe time depends on drive speed and passes. Gutmann on a large drive can take days.",
    ]),
]

REQUIRED_PERMISSIONS = [
    ("admin", "Administrator rights", "Needed to write directly to drives and external devices."),
    ("storage", "Storage read/write access", "Needed to overwrite the files, folders and drives you select."),
    ("devices", "External device detection", "Needed to list USB drives and memory cards as they connect."),
    ("audit", "Audit log and certificates", "Every wipe is recorded and certified. This cannot be turned off."),
]

OPTIONAL_PERMISSIONS = [
    ("notifications", "Desktop notifications", "Alert me when a wipe finishes or fails.", True),
    ("sound", "Completion sound", "Play a sound when a long wipe finishes.", False),
    ("autoscan", "Scan for devices at startup", "List connected external devices when the app opens.", True),
    ("remember_algo", "Remember my last method", "Pre-select the method I used last time.", False),
]

ACKNOWLEDGEMENT = "I understand wiping is permanent and grant the required permissions."
