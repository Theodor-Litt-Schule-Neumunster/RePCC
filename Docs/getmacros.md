# Macros

Um die Macros von dem Benutzer zu bekommen, nutzt man die `/macro/getall` Request

Beispiel:
Der benutzer hat so eine Datenstruktur auf dem Endgerät gespreichert:

```yaml
.RePCC/macros/
 - mouseMove.pcmac
 - example.pcmac
```

Um diese zu bekommen, schicken wir eine GET-REQUEST an den Server via port 15248.

Request: 
```
http://127.0.0.1:15248/macro/getall
```
Return: 
```json
{
    "macros" : [
        "mouseMove",
        "example"
    ]
}
```
Die namen werden ohne der .PCMAC-Extension weitergeleitet, die übersetzung ob dort .pcmac ist oder nicht, übernimmt der Server.

---
### Macro check
Hin und wieder möchte man gucken, was in einem Macro ist. Z.B vor der Ausführung oder bei der Bearbeitung. Dafür gibt es den `/macro/get/$MACRONAME` Reqest, der dafür zuständig ist, den Macro zu returnen.
(Beispiel: `http://127.0.0.1:15248/macro/`)

Die Request hat 2 methoden:
- DATA
    > Hier werden alle Daten vom Macro zurückgegeben. Die genaue Struktur von einem Macro findet man in [/Backend/windows/base/structure.json](..\Backend\windows\base\structure.json)
- CHECK
    > Hier wird nur geguckt, ob der Macro exsistiert. Wenn der Macro mit dem Namen auf dem PC exsistiert, wird CODE 200 (OK) Returned, sonnst 404 (NOT FOUND).

Um die jeweiligen Requestarten zu benutzen, muss man diese im Body so hinzufügen:

```json
body = {
    "METHOD":"DATA"
}
```
oder
```json
body = {
    "METHOD":"CHECK"
}
```