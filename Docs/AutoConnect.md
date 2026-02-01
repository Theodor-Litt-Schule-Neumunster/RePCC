# AutoConnect.md

Das ist eine Dokumentation des "AutoConnect" Features vom RePCC backend, sowie eine detalierte erklärung wie ein Flutter client sich verbinden kann.

Author: SMRNW

---

Die wesentlichen Informationen sind:
- Der mDNS Serivce ist auf dem Port 15250.
- Der Servicename ist immer "RePCC".
- Antworten an die IP verlaufen über den Port 15248.

---

Wenn ein Client gefunden wurde, kommt am ende das Folgene raus:

```Shell
RePCC.[NAME]._http,_tcp.local.
```
Mit dem Service kommt ein Payload als eine textAsStringMap mit. Diese Payload ist in bytes.

Diese ist so aufgebaut:


```json

{
    "appversion":"any.1 indev",
    "mac":"AN:NY:MA:C0:AD:DR:ES",
    "2fa":12345678
}

```
Die App version wird dann für den Endnutzer im Connect-Banner angezeigt.

Die MAC wird benutzt um geräte zu vertrauen. Wenn neue verbindungen ausgeschaltet werden, werden nur die gespeicherten MACs erlaubt.

Der 2FA code wird sofort zurück an den server per HTTP request zurückgeschickt, zur verifizierung, dass es aus einer mDNS request kommt. Diese sind immer 8 stellig.

Um mit den Server sich zu verbinden muss die HTTP Request so aufgebaut werden:

Address:    `192.168.0.1:15248/connect`

Body:       `{"MAC":"AN:NY:MA:C0:AD:DR:ES", "2fa":123456789}`

Wenn der Server die verbindung annimmt und alle Information da sind, wird der server mit 202 (ACCEPTED) antworten. Der Server speichert die IP und brauch bei zukünftigen verbindungen keine 2FA. Diese verbundungen werden auch akzeptiert wenn neue verbindungen geblockt werden, solange die MAC-Adresse des Gerätes immer mitgeteielt wird.

Um eine komplette ausschließung von den Geräten zu gewährleisten, muss die gespeicherte MAC-Adresse gelöscht werden. 