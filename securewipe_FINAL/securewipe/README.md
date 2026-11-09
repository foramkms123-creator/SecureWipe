# SecureWipe

## Run
    python -m pip install -r requirements.txt
    python main.py                  # run as Administrator for drive wiping

Optional demo data (after creating an account):
    python -m database.seed_demo

Requires Python 3.10+.

## Flow
Splash (4 s) -> Introduction -> Permissions -> Sign in / Sign up -> Dashboard
The introduction and permissions pages show only on first launch
(set `ALWAYS_SHOW_ONBOARDING = True` in config.py to always show them).

## Layout
    config.py                 all tunables: colours, fonts, tagline, nav order, DB path
    main.py                   entry point
    database/                 SQL only (connection, schema, one repo per table)
    services/                 rules: auth, password hashing, dashboard data, OS checks
    ui/app.py                 window + screen router
    ui/screens/               splash, intro, permissions, auth, dashboard shell
    ui/components/            sidebar, top bar, stat card, log table
    ui/views/                 content shown inside the dashboard shell
    ui/content/               editable onboarding text

## Multi-user notes
- The first account created becomes admin; later accounts are staff.
- Admins see every user's operations; staff see their own.
- Passwords: salted scrypt hashes. 5 failed sign-ins lock the account for 5 minutes.
- SQLite runs in WAL mode, which suits ~10 users on one machine. If several PCs must
  share one database, switch to PostgreSQL/MySQL; only the `database/` package changes.

## Algorithms page (new erasure task)
Sidebar "+" -> pick file(s) / folder / drive -> Algorithms page opens with:
1. Selected target  name, type, total size, used/free space of its drive
2. Wipe method      Zero Fill, One Fill, Random Data (1-10 passes), DoD 5220.22-M (3 or 7),
                    Gutmann (fixed 35)
3. Progress         percentage, elapsed, remaining, estimated total, current pass
4. Actions          Start, Stop, Generate certificate (unlocks only at 100 %)

## Settings
General (theme, date format, start with Windows), Security (password policy, auto-lock, password before a wipe, change password), default wiping method, reports folder and automatic PDF certificate, notifications. Stored in the app_settings table.

## Reports and certificates
Generate certificate saves the wipe as a report and shows its Certificate of Destruction.
Reports lists all certificates (newest first); View Report opens one; Download PDF saves it.

**Verification:** The current version performs overwrite operations but does not read back and verify the overwritten data. Generated certificates record the operation and do not certify verified destruction.
  


Wipe execution mode:
- SIMULATE_WIPE = True in config.py: simulated progress; no overwrite is performed.
- SIMULATE_WIPE = False in config.py: the application executes the selected overwrite algorithm through services/wipe_engine.py -> WipeJob._run_real().
- Real wiping is destructive. Test only on an explicitly selected, authorized target after verifying its identity.
- A successful application status alone does not establish that all data is unrecoverable; verification must be implemented and evaluated separately.


## Notifications
Finished, failed or stopped wipes and issued certificates add a bell entry, show a banner at the top
right and play a sound. Choose the sound for each event, or turn it off, in Settings > Notifications.
Sounds use Windows' own player (Windows only). Start-up and run-time errors are written to `data/app.log`.

## Performance notes (keep the UI smooth)
- Static text: use `Label` / `Box` from `ui/light.py`, not `CTkLabel` / transparent `CTkFrame`.
  Every CTk widget is a canvas that Windows repaints on scroll and resize.
- Scrolling pages: use `ScrollFrame` (`ui/components/scroll_frame.py`), not `CTkScrollableFrame`.
- `font()`, `icon()` and `assets.logo()` are cached; always call them instead of creating
  CTkFont / CTkImage objects directly.
- Only reconfigure a widget when its value actually changed (each configure = redraw).
