# AutoConnect

Diese Dokumentation beschreibt das Feature **AutoConnect** im RePCC-Backend sowie den Verbindungsablauf für einen Flutter-Client.

Author: SMRNW

---

## Wesentliche Informationen

- Der mDNS-Service läuft auf Port `15250`.
- Der Servicename ist immer `RePCC`.
- Antworten an die IP laufen über Port `15248`.

---

Wenn ein Client gefunden wurde, sieht der Service-Eintrag so aus:

```shell
RePCC.[NAME]._http,_tcp.local.
```

Mit dem Service wird eine `textAsStringMap` als Payload übertragen (in Bytes).

Aufbau der Payload:

```json
{
    "appversion": "any.1 indev",
    "mac": "AN:NY:MA:C0:AD:DR:ES",
    "2fa": 12345678
}
```

Die App-Version wird für den Endnutzer im Connect-Banner angezeigt.

Die MAC-Adresse wird verwendet, um Geräte zu vertrauen. Wenn neue Verbindungen deaktiviert sind, werden nur gespeicherte MAC-Adressen zugelassen.

Der 2FA-Code wird sofort per HTTP-Request an den Server zurückgeschickt, um zu verifizieren, dass der Request aus mDNS stammt. Der Code ist immer 8-stellig.

## Verbindung mit dem Server

Die HTTP-Request ist wie folgt aufgebaut:

Address: `192.168.0.1:15248/connect`

Body: `{"MAC":"AN:NY:MA:C0:AD:DR:ES", "2fa":123456789}`

Wenn der Server die Verbindung annimmt und alle Informationen vorhanden sind, antwortet der Server mit `200` (`ACCEPTED`).

Der Server speichert dann die IP und benötigt bei zukünftigen Verbindungen keine 2FA mehr. Diese Verbindungen werden auch akzeptiert, wenn neue Verbindungen blockiert sind, solange die MAC-Adresse des Geräts immer mitgesendet wird.

Um ein Gerät vollständig auszuschließen, muss die gespeicherte MAC-Adresse gelöscht werden.