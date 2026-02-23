# Save Macros

Um ein neues Macro zu speichern, kann folgende POST-Request verwendet werden:

`127.0.0.1:15248/macro/save`

Die Request benötigt ein JSON mit folgendem Aufbau:

```json
{
    "macro": {
        // Macro-Daten, Struktur in backend/windows/struktur
    },
    "name": "MacroName"
}
```

Wenn beide Felder in der Request vorhanden sind, übernimmt der Server die Speicherung und antwortet mit Statuscode `200`.

Wenn das Macro nicht gespeichert werden kann, weil die Macro-Struktur nicht unterstützt wird, antwortet der Server mit Statuscode `405` (`NOT ALLOWED`).

Wenn der Name bereits existiert, wird am Ende `(1)` ergänzt. Falls auch dieser Name bereits vergeben ist, wird die Zahl am Ende iterativ erhöht.