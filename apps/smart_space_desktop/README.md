# Smart Space Desktop (Python / PySide6)

A Windows client for the existing Smart Space FastAPI backend. The backend is the single source of truth;
confirmed API contracts are documented in `../../docs/desktop/api-mapping.md`.

## Run (Windows 10/11, Python 3.11+)

```powershell
cd apps\smart_space_desktop
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m smart_space_desktop
```

In the application: open **Settings → Backend URL** (default: `http://localhost:8000`), enter the API token `ss_…`,
and select **Save and Check**. Enable **Demo Mode** when the backend is unavailable.

## Tests

```powershell
pytest
```

Tests run in Qt offscreen mode (without opening windows) and do not access the network: HTTP is replaced with `httpx.MockTransport`.

## Phase 1 — completed

JARVIS theme (QSS), sidebar/topbar, navigation, smooth page transitions, keyboard shortcuts
(Ctrl+1…4, Ctrl+, , Ctrl+R), Settings (URL, token in Windows Credential Manager, polling interval, Demo Mode),
connection status (`/health` + token validation without blocking the UI), centralized API client, and error mapping.
Module pages are intentional placeholders that identify their data sources (Phase 2+).
