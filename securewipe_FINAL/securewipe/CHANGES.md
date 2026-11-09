
# SecureWipe – Wiping implementation notes (20 Oct 2026)

## Wiping algorithms
- `services/algorithms/dod.py`: Implements the configured 3-pass and 7-pass DoD overwrite sequences.
- `services/algorithms/gutmann.py`: Implements the configured 35-pass Gutmann sequence.
- `services/algorithms/fill.py`: Handles overwrite operations for files, folders and whole drives.
- `services/algorithms/writer.py`: Provides the shared write logic, including fixed-pattern writes and random bytes generated using `os.urandom()`.
- `services/raw_device.py`: Handles opening raw drive targets for wiping.

Note: The current implementation does not perform read-back verification of overwritten data.



# SecureWipe – Settings now apply (12 Oct 2026, fix 2)

## Why the settings did not show
- Theme: saving only switched CustomTkinter's mode. Every screen sets its own colours, so nothing changed.
- Sign-in and sign-up: the entry fields had no text colour, so after "Dark" was saved they took CustomTkinter's dark default (white text).
- Screens were built once, so a saved setting only reached screens that happened to refresh.

## What changed
| File | Change |
|---|---|
| `config.py` | `LIGHT_COLORS` and `DARK_COLORS` (same tokens), `SIDEBAR_LIGHT` / `SIDEBAR_DARK`. `COLORS` / `SIDEBAR` are the live copies. |
| `ui/theme.py` | `apply_palette(mode, root)` switches the palette and CustomTkinter's mode, and restyles the tables. |
| `services/settings_service.py` | `resolve_theme()`: "System" reads the Windows app theme. |
| `ui/app.py` | Sign-in and sign-up always use the light palette. The user's theme is applied at sign-in. After Save Changes the signed-in screens are rebuilt (not while a wipe runs). |
| `ui/screens/dashboard.py` | Accepts a start section, so the rebuilt screen reopens on Settings. |
| `ui/views/settings_view.py` | Save reports whether the theme changed; uses the resolved theme. |
| `ui/screens/auth.py` | Entry text is always dark (`text_color`), placeholder muted. |
| `ui/views/about_view.py`, `certificate.py`, `sidebar.py`, `log_table.py`, `algorithm_view.py` | Colours read from tokens at build time. The certificate always uses the light palette. |
| Search fields | Explicit text colour. |

# SecureWipe – Settings page (12 Oct 2026)

The Settings page is built. Every option is stored once for the installation (app_settings) and
applied when Save Changes is pressed. Restore Defaults fills the page with default values; they are
saved only after Save Changes.

## New files
| File | What it does |
|---|---|
| `services/settings_service.py` | Preferences: defaults, load/save with validation, date formats, reports folder, Windows startup entry. |
| `services/notify_service.py` | Adds bell notifications for finished wipes and issued certificates, if switched on. |
| `ui/views/settings_view.py` | Settings page: General, Security, Data Wiping Defaults, Reports & Storage, Notifications; Restore Defaults and Save Changes. |
| `ui/components/password_dialogs.py` | Change password form, and the password prompt used before a wipe starts. |

## Changed files
| File | Change |
|---|---|
| `services/auth_service.py` | Password policy (Standard / Strong) read from Settings; `change_password()`, `confirm_password()`. |
| `database/users_repo.py` | `update_password()`. |
| `services/certificate.py`, `services/dashboard_service.py` | Dates shown in the chosen date format. |
| `ui/views/algorithm_view.py` | Default method from Settings; password prompt before a wipe (if on); notifications; automatic certificate and PDF save (if on). |
| `ui/views/certificate_view.py` | Save PDF dialog opens in the Reports folder. |
| `ui/app.py` | Theme applied at start; auto-lock after inactivity (never during a wipe). |
| `ui/screens/dashboard.py` | Settings section; `busy` flag for auto-lock. |
| `ui/icons.py` | Icons: shield, lock, bell, database, refresh. |

## Not included yet
- Language: English only, so the option is not shown.
- "Verify data after wiping" and "Include audit log in PDF certificates" (reference image): no verification or audit log exists yet.
- Dark and System themes switch CustomTkinter's mode only. The app's colours are fixed light tokens, so those two modes will look mixed until a dark palette is built.

# SecureWipe – Certificates and Reports (11 Oct 2026)

Generate certificate now records the wipe and shows a Certificate of Destruction, which can be
saved as PDF. Reports lists every certificate of the signed-in user (admins: all users).

## New files
| File | What it does |
|---|---|
| `services/certificate.py` | Records a finished wipe, draws the certificate (Pillow, A4 landscape, 200 dpi) and saves it as PDF. |
| `services/report_service.py` | Reports list (with search) and single-certificate lookup. Admins see all, staff see their own. |
| `ui/views/reports_view.py` | Reports section: Report ID, Target, Wiping method, Date & time, View Report. |
| `ui/views/certificate_view.py` | One certificate: preview, Back to reports, Download PDF. |

## Changed files
| File | Change |
|---|---|
| `database/schema.py` | `operations` gets `certificate_issued_at`, `total_size`, `items_json`. Existing databases are migrated on start. |
| `database/operations_repo.py` | `add_operation()` takes the new fields; `get_report_rows()` and `get_operation()` added. |
| `database/seed_demo.py` | Demo rows carry items, sizes and issue times. |
| `services/target_info.py` | Collects each item (file name with extension, folder, or drive) with its size before the wipe. |
| `ui/views/algorithm_view.py` | "Generate certificate" saves the report once, then opens it ("View certificate" afterwards). |
| `ui/screens/dashboard.py` | Reports section, certificate page on top of a section (Back returns to Reports). |
| `config.py` | `REPORT_ROW_LIMIT`. |

Colours: only the existing dark green (`green_dark`) and light green (`green_light`, `green_soft`) tokens.
Certificate IDs: `SW-CERT-<yyyymmdd>-<nnn>`; report IDs: `SW-<yyyymmdd>-<nnn>`.
Simulation mode (`SIMULATE_WIPE = True`) still issues a certificate, marked as a simulation.

# SecureWipe – Random Data wipe (10 Oct 2026)

Random Data is now a real overwrite for files, folders and whole drives (pendrives, disks).
Every write gets fresh random bytes from the OS (`os.urandom`), so no pattern repeats.

## New files
| File | What it does |
|---|---|
| `services/algorithms/random_data.py` | Random Data algorithm: calls the shared engine with `fill_byte=None`. |

## Changed files
| File | Change |
|---|---|
| `services/algorithms/writer.py` | `pattern_buffer(None)` returns no pattern; `fill_fd()` writes `os.urandom(n)` per write when there is no pattern. Zero/One behave exactly as before. |
| `services/algorithms/fill.py` | `run()` accepts `fill_byte=None` (random). Type hints added. Same code path for file, folder and drive. |
| `services/wipe_engine.py` | `"random"` added to `ALGORITHMS`, so the Random Data method is no longer "not implemented". |

Unchanged: UI (`algorithm_view.py`), `wipe_methods.py`, `config.py`, `target_info.py`, `raw_device.py`, database and all other files.

# SecureWipe – lag fixes (28 Sep 2026)

Behaviour and look are unchanged; only how the UI is drawn changed.

## New files
| File | What it does |
|---|---|
| `ui/light.py` | `Label` and `Box`: plain Tk text/containers that follow CTk DPI scaling. Used for all static text instead of `CTkLabel` (each CTkLabel is a canvas that Windows repaints on every scroll/resize). |
| `ui/components/scroll_frame.py` | `ScrollFrame`: replaces `CTkScrollableFrame`. Wheel ticks and scrollbar drags are merged into at most one repaint per frame (16 ms); resize updates are merged into one idle update; one wheel handler for the whole app. |

## Changed files
| File | Change | Fixes |
|---|---|---|
| `ui/theme.py` | `font()` is cached: one shared font per size/style instead of 100+ separate font objects. | Slow login, slow screen changes |
| `ui/assets.py` | `logo()` is cached and pre-shrunk once (source PNG is 1600 px; it was resized again for every screen). | Slow splash → sign in → dashboard |
| `ui/icons.py` | `icon()` returns cached images. | Slow login |
| `ui/app.py` | `_swap()` draws the new screen fully before removing the old one (no blank / piece-by-piece drawing). | Flicker between screens |
| `ui/screens/auth.py` | Sign in / Sign up widgets are built once; switching only shows/hides 2 fields. Password check runs in a background thread with "Signing in…" on the button. | Lag switching Sign in ↔ Sign up; freeze after pressing Sign in |
| `ui/views/algorithm_view.py` | Uses `ScrollFrame` + light labels. Buttons, tiles and time cells are only reconfigured when their value changes. | Scroll lag on Algorithms page, lag while wipe is running |
| `ui/views/about_view.py` | Uses `ScrollFrame` + light labels. Text re-wrap runs once after resizing stops (was on every resize event). | Scroll lag on About page, lag when maximising |
| `ui/views/dashboard_view.py` | Auto-refresh (15 s) is skipped while another page is shown; chips/table only rebuilt when data changed; duplicate first refresh removed; hero text uses light labels. | Periodic hitch on other pages, slower login |
| `ui/components/stat_card.py` | Light labels; redraw only when the number changes. | Slow login |
| `ui/components/topbar.py` | Title and clock use light labels; clock ticks on the exact second. | Constant redraw every second |
| `ui/components/drive_picker.py` | Uses `ScrollFrame` + light labels. | Consistency |
| `ui/screens/intro.py`, `ui/screens/permissions.py` | Use `ScrollFrame` + light labels. | Scroll lag on first-launch pages |
| `README.md` | Performance notes section. | – |

Unchanged: `config.py`, `main.py`, `database/*`, `services/*`, `ui/screens/dashboard.py`, `ui/screens/splash.py`, `ui/components/sidebar.py`, `log_table.py`, `popup.py`, content files.

# SecureWipe – notifications, date and startup fixes (V9)

## Notifications (new)
- When a wipe finishes, fails or is stopped, and when a certificate is issued, SecureWipe now:
  1. adds the bell entry (as before),
  2. shows a banner at the top right of the window (up to three, closes after 7 seconds or with ×),
  3. plays a short sound chosen for that event.
- Settings > Notifications: master switch, banner switch, one switch per event (wipe completed,
  wipe stopped or failed, certificate issued), a sound list per event (Chime, Success, Alert,
  No sound) and a Test sound button.
- Sounds are generated once as WAV files in `data/sounds` and played with Windows' own player
  (`winsound`). On other systems they are silent.

| File | Change |
|---|---|
| `services/sound_service.py` | New: generates and plays the built-in tones. |
| `services/notify_service.py` | Rewritten: `notify(user, event, message)` with per-event flags, banner and sound; `set_listener()` for the window. |
| `ui/components/toast.py` | New: banner stack, top right. |
| `ui/app.py` | Banner stack above every screen; notification listener registered when signed in. |
| `ui/views/algorithm_view.py` | Calls `notify()` for wipe completed, wipe failed or stopped, and certificate issued. |
| `ui/views/settings_view.py` | Notifications card rebuilt (banner, per-event switch and sound, Test sound). |
| `services/settings_service.py` | New keys: `notify_banner`, `notify_wipe_failed`, `sound_wipe_done`, `sound_wipe_failed`, `sound_certificate` (validated). |

## Dates
- The top bar date and clock now use the Date format setting (before they always showed
  day/month/year in British order). The format is read on every tick, so a change applies at once.
- Notification times in the bell menu use the same setting.

## Start with Windows
- Windows also keeps an on/off flag per startup entry (Task Manager > Startup apps). Turning
  SecureWipe off there silently blocked the launch. The setting now also writes that flag as
  enabled.
- `sync_startup_entry()` runs at every start: it re-writes the entry while the setting is on
  (fixes a moved install folder or a disabled flag) and removes a leftover entry when it is off.

## Crash log
- `main.py` writes any start-up or run-time error to `data/app.log` and shows a message box that
  gives the log location.

# SecureWipe – licence page, full detailed log (V10)

## Detailed log shows every wipe
- A wipe is now written to the detailed log as soon as it finishes (success, failed or stopped).
  Before, a row only appeared after a certificate was generated.
- Report column: "No" until the certificate is generated, then "Yes" (the row is updated, not added again).
- Reports section still lists only wipes that have a certificate.

## About > View license
- Opens a Software License window (reference layout): header with logo, title and ×; the
  Academic Project License badge; app summary; cards for Permissions, Restrictions, Warranty &
  Liability and Technology acknowledgements; footer with the project guide, Close and Export License.
- Export License saves `SecureWipe_License.pdf` (A4, one page) in the reports folder from
  Settings > Reports & Storage, or the default reports folder if none was chosen.

| File | Change |
|---|---|
| `services/certificate.py` | `record_wipe()` logs a finished wipe (Report = No); `issue(op_id)` marks it as reported. |
| `database/operations_repo.py` | `mark_certificate()`. |
| `ui/views/algorithm_view.py` | Logs the wipe when it finishes; generating a certificate updates that row. |
| `services/license_service.py` | New: draws and exports the licence PDF. |
| `ui/components/license_dialog.py` | New: the Software License window. |
| `ui/views/about_view.py` | View license opens the window. |
| `ui/content/about_text.py` | Licence text moved here as structured sections. |
| `ui/icons.py` | New icons: check, alert, code, cap, download. |
