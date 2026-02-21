So prüft der Flutter-Client, ob der Server noch erreichbar ist.

```
        Client              Server
          |   Ping to server  |
          |------------------>|
          |                   |
          | Response, im good |
          |<------------------|

            Device set to online
               Loop, 10 sec
        
          |                  |
          |                 end
          |
          |   Ping to server
          |---------------------->
          |
          |
          |  100-500 MS timeout

            Device set to offline
          Ping only w/ refresh button 
```

Der Ping-Request liefert je nach Registrierungsstatus unterschiedliche Codes:

- `200` für nicht registrierte IPs
- `202` für registrierte IPs

Der Statuscode `202` sollte verwendet werden, um zu prüfen, ob der Server das Gerät bereits registriert hat.