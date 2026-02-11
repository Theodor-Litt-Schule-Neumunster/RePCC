# Save Macros

Um ein neuen Macro zu speichern, kann man den Request `127.0.0.1:15248/macro/save`, als POST request, nutzen.

Die Request brauch ein JSON, die so aufgebaut werden sollte:

```json
{
    "macro":{
        // Macro daten, struktur in backend/windows/struktur
    },
    "name":"MacroName"
}
```

Wenn die zwei Sachen in der Request vorhanden sind, übernimmt der Server die Speicherung und schickt ein Code 200 zurück.

Wenn der Macro nicht gespeichert werden kann, weil die Macro-Stuktur nicht supported wird, wird ein Code 405 (NOT ALLOWED) zurückgeschickt.

Wenn der name ein Duplikat ist, wird ein (1) am ende hinzugefügt. Wenn das auch ein Duplikat ist, wird diese Zahl am ende iterativ erhöht.