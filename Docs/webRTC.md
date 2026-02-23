# WebRTC & Laserpointer

## Setup der Refreshrate

Ein wichtiger Punkt beim Laserpointer ist die Refreshrate. Sie legt fest, wie schnell Laserpointer-Updates gesendet werden.

Die Refreshrate ist auf dem PC gespeichert und muss vom Client per HTTP-Request abgefragt werden, damit der Client sein eigenes Ratelimit korrekt setzen kann.

---

**Wichtig:** Der Server hat bereits ein Ratelimit für Updates eingebaut. Trotzdem muss auch der Client ein eigenes Ratelimit haben. Zwar filtert der Server zu viele Daten heraus, aber ein massiver Datenstrom kann den Datentunnel trotzdem stark verlangsamen.

Wie setzt man das um?

Die Anfrage liefert eine Refreshrate als `int` (z. B. `30`). Stelle sicher, dass Updates nur in dieser Rate gesendet werden.

```py
if currenttime - lastupdate >= 1 / refreshrate:
    ...  # SEND POS DATA INTO DATATUNNEL
```

Das ist ein einfaches Beispiel für ein Ratelimit in Python.

- `lastupdate` = Zeit des letzten Updates (in ms)
- `currenttime` = aktuelle Zeit des Sendeversuchs (in ms)

---

## DataChannels und Updates

Der Server erstellt automatisch einen Video-DataChannel mit dem Namen `video`.

Um Bildschirmdaten vom PC zu empfangen, muss die App eine PeerConnection erstellen und einen Transceiver mit `name: "video"` und `direction: "recvonly"` hinzufügen.

Dadurch werden die Bildschirmdaten über einen Stream übertragen.

Für den Laserpointer muss der Flutter-Client selbst den DataChannel `laser` erstellen.

Über diesen Kanal werden normalisierte Werte (`0.0` bis `1.0`) gesendet. Diese Werte entsprechen der Position beim Tippen bzw. Draggen.

Die gesendeten Daten werden im JSON-Format erwartet, zum Beispiel:

```json
{
  "x": 0.1512412547,
  "y": 0.5753252109
}
```

Den Rest übernimmt der Server.

## Wichtig beim Trennen der Verbindung

Wenn die Verbindung geschlossen wird (z. B. durch App-Schließen), muss über den DataChannel ein Disconnect an den WebRTC-Server gesendet werden.

Wenn das nicht passiert, kann es vorkommen, dass ein neuer Laserpointer gestartet wird und der alte WebRTC-Datentunnel während der Nutzung unerwartet geschlossen wird.