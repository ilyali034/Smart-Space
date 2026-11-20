# Smart Space Desktop — Architecture (Python / PySide6, Phase 1)

```
smart_space_desktop/
  core/   errors.py  api_client.py  settings.py  connection.py  context.py
  ui/     theme.py  widgets.py  nav.py  sidebar.py  topbar.py  main_window.py  pages/
  main.py
```

- **The UI does not make network requests directly.** HTTP goes only through `core/api_client.ApiClient` (httpx). Errors use a single `AppError` type (`core/errors.py`). Logs contain only the method, path, and error type; tokens are never logged.
- **The UI thread is never blocked.** Network calls run in `QThreadPool` (`connection.py`), and results are returned through a signal. Stale responses are discarded by generation number.
- **State.** `SettingsStore` (QSettings: URL, interval, Demo; tokens exist only in Windows Credential Manager through `keyring`) recreates `ApiClient` and restarts `ConnectionMonitor` when settings change. Each feature area has its own controller; there is no global god-state object.
- **Real-time.** Because the backend has no WebSocket, the app polls `/health` and `/devices?limit=1` at the interval from settings. `AppContext.refresh_requested` (Ctrl+R) makes pages reload.
- **Demo Mode** disables all network calls. The DEMO MODE badge appears in the topbar and sidebar.
- **Testability.** Every core component accepts a transport/token store through its constructor (`httpx.MockTransport`, `MemoryTokenStore`). The UI is tested through `pytest-qt` in offscreen mode.
- **Packaging (Phase 8):** PyInstaller or Nuitka, onedir build.
