# Macros

Um die Macros eines Benutzers zu erhalten, wird die Request `/macro/getall` verwendet.

Beispiel:
Der Benutzer hat folgende Datenstruktur auf dem Endgerät gespeichert:

```yaml
.RePCC/macros/
 - mouseMove.pcmac
 - example.pcmac
```

Um diese zu erhalten, wird eine GET-Request an den Server über Port `15248` gesendet.

Request: 
```text
http://127.0.0.1:15248/macro/getall
```
Return: 
```json
{
    "macros": [
        "mouseMove",
        "example"
    ]
}
```

Die Namen werden ohne `.pcmac`-Extension zurückgegeben. Die Zuordnung übernimmt der Server.

---
## Macro Check

Manchmal möchte man prüfen, was in einem Macro enthalten ist, z. B. vor der Ausführung oder während der Bearbeitung.

Dafür gibt es die Request `/macro/get/$MACRONAME`, die das gewünschte Macro zurückliefert.

(Beispiel: `http://127.0.0.1:15248/macro/`)

Die Request kennt zwei Methoden:

- `DATA`
    - Gibt alle Daten des Macros zurück.
    - Die genaue Struktur eines Macros steht in `/Backend/windows/base/structure.json`.
- `CHECK`
    - Prüft nur, ob das Macro existiert.
    - Wenn ein Macro mit diesem Namen vorhanden ist, wird `200` (`OK`) zurückgegeben, sonst `404` (`NOT FOUND`).

Um die jeweilige Request-Art zu verwenden, wird sie im Body gesetzt:

```json
body = {
    "METHOD": "DATA"
}
```
oder
```json
body = {
    "METHOD": "CHECK"
}
```