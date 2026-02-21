# Settings

Natürlich sollen Benutzer einige RePCC-Einstellungen selbst anpassen können.

Folgende Dateien werden als Einstellungen verwendet:

- `debug` (Debug-Einstellungen, z. B. externe Verbindungen erlauben)
- `presentationTools` (Einstellungen für Clicker-Buttons und Laserpointer)
- `webrtc` (Einstellungen für Bildschirmspiegelung wie Videoqualität und FPS)

## Load Settings

Der Server stellt folgende Request-URL bereit, um Einstellungen abzurufen:

```text
http://ip:15248/settins/get/{arg}
```

`{arg}` steht für den Namen einer bestimmten Einstellung oder für `all`, um alle verfügbaren Einstellungsdateien zu erhalten.

Beispiel:

```text
http://ip:15248/settins/get/all
```

Return:

```text
[debug, presentationTools, webrtc]
```

Wenn statt `all` ein einzelner Name als `{arg}` verwendet wird, werden die zugehörigen Einstellungen als JSON zurückgegeben.

Beispiel:

```text
http://ip:15248/settins/get/presentationTools
```

Return:

```json
{
    "laserpointer": {
        "style": "trail",
        "fadetime": 1000,
        "corecolor": [255, 0, 0, 255],
        "refreshrate": 30,
        "traillength": 100,
        "size": 10
    },
    "buttons": {
        "forward": "right",
        "backward": "left"
    }
}
```

## Save Settings

Beispiel: Die Präsentationstools sollen aktualisiert werden.
Der Benutzer ändert die Laserpointer-Größe von `10` auf `30`.

Der neue JSON-Block sieht dann so aus:

```json
{
    "laserpointer": {
        "style": "trail",
        "fadetime": 1000,
        "corecolor": [255, 0, 0, 255],
        "refreshrate": 30,
        "traillength": 100,
        "size": 30
    },
    "buttons": {
        "forward": "right",
        "backward": "left"
    }
}
```

Diesen Block sendest du im Body einer POST-Request (mit JSON-Header) an:

`http://ip:15248/settins/post/{NAME}`

In diesem Beispiel also:

`http://ip:15248/settins/post/presentationTools`

`{NAME}` ist der Dateiname der Einstellung.

Die Datei wird vollständig durch den neuen Block ersetzt. Deshalb muss immer der komplette Einstellungsblock gesendet werden.

Bei erfolgreichem Ablauf antwortet der Server mit Statuscode `200`.