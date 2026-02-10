# WebRTC & Laserpointer

### Setup der Refreshrate

Ein wichtiger Punkt vom Laserpointer ist die Refreshrate, welche sagt, wie schnell die Laserpointer Updates geschickt werden.
Diese sind auf den PC gespeichert, und muss per HTTP request vom client gefragt werden, um selber einen Ratelimit einstellen zu können.

---
WICHTIG - Der Server hat selber einen Ratelimit für die Updates eingebaut. JEDOCH muss der Client auch eins haben. Auch wenn der Server rausfiltert, welche Daten veratbeitet werden, wird ein massiver Stream an Daten den Datentunnel extrem verlangsamen.

"Wie bekomme ich das hin?"

Ganz einfach. Durch die Request bekommt man ein refreshrate als INT (z. b. 30). Stell einfach sicher, dass die Requests in diesem Rate geschickt wird.

```py
if currenttime - lastupdate >= 1/refreshrate: 
    ... # SEND POS DATA INTO DATATUNNEL
```
Das ist ein einfacher beispiel, wie man so ein Ratelimit in PY einbauen kann.

- lastupdate = zeit des letzen updates, mit MS
- currenttime = jetzige zeit vom versuch, mit MS

---

### DataChannels und Updates

Der Server erstellt von selbst ein video DataChannel, dieser ist auch passend "video" genannt.
Um Bildschirmdaten vom PC zu bekommen, musst du eine PeerConnection erstellen, einen Transceiver hinzufügen (name "video", direction, "recvonly" (Recievie only))
Dadurch werden dann die Bildschirmdaten durch einen Stream geschickt.

Für den Laserpointer, musst der Flutter-Client selbst den DataChannel "laser" erstellen.
Dadurch werden dann normalisierte Werde (0.0 - 1.0) geschickt. Das ist die Position des Tippens / Drag ist.

Die geschickten Daten werden in einen JSON format erwartet. Ungefair so:
```json
{
    "x":0.1512412547,
    "y":0.5753252109
}
```

Der Server übernimmt den Rest.