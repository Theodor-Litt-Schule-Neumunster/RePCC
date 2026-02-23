# GUI Requests

## Status

Dieses Feature ist noch in der Entwicklungsphase.

## Beschreibung

Der Server kann den Client über bestimmte Interaktionen auffordern, ein GUI-Fenster zu öffnen.

Aktuell ist dafür vorgesehen:

- Öffnen über das Tray-Icon (`Settings`, `Macroübersicht`, `Homepage`)

Dafür muss die Desktop-App per Argument gestartet werden können.

---

```bash
App.exe --settings
App.exe --home
App.exe --macros
```

---