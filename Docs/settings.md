# Settings

Natürlich wollen wir, dass der Benutzer manche sachen von RePCC einstellen kann.

Wir haben folgene Dateien, die als Einstellungen agieren:

- debug (Debug einstellungen wie externe Verbindungen erlauben u.s.w)
- presentationTools (Einstellungen von den Clicker-Buttons und Laserpointer)
- webrtc (Einstellung der Bildschirmspiegelung wie Videoqualität und FPS)

### Load settings
---

Der Server hat folgene Requests um die Einstellungen zu returnen:

```
http://ip:15248/settins/get/{arg}
```

Hier steht ARG für die möglichkeit, eine bestimmte Einstellung zu bekommen oder alle möglichen Einstellungen in einer liste

also,

```
http://ip:15248/settins/get/all
```
Return:
```
[debug, presentationTools, webrtc]
```
---
Wenn wir nun einer der namen als ARG nehmen, werden alle einstellungen als JSON zurückgesendet.

also,

```
http://ip:15248/settins/get/presentationTools
```
Return:
```json
{
    "laserpointer": {
        "style":"trail",
        "fadetime":1000,
        "corecolor":[255,0,0,255],
        "refreshrate":30,
        "traillength":100,
        "size":10
    },
    "buttons": {
        "forward":"right",
        "backward":"left"
    }
}
```
---

### Save Settings

Sagen wir, wir möchten die Präsentationstools updaten.
Der user hat die Einstellung geändert und möchte, dass die Größe 30 ist, statt 10.

So würde dann der neue EinstellJSONBlock aussehen:

```json
{
    "laserpointer": {
        "style":"trail",
        "fadetime":1000,
        "corecolor":[255,0,0,255],
        "refreshrate":30,
        "traillength":100,
        "size":30
    },
    "buttons": {
        "forward":"right",
        "backward":"left"
    }
}
```

Diese schicken wir im Body von der Post-Request zu der URL (mit JSON header, natürlich.) `http://ip:15248/settins/post/{NAME}`, also in unserem Fall: `http://ip:15248/settins/post/presentationTools`. NAME in der URL ist der DateiName der Einstellung.

Die Datei wird mit dem neuen Block ersetzt, also MUSS UNBEDINGT der GANZE einstellblock mitgesendet werden.

Danach gibts ein schnönen Code 200, wenn alles sauber verläuft.