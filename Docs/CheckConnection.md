Gefolgt ist wie der Flutter-Client guckt, ob der Server noch lebendig ist.

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

Bei regestrierten IPs wird der ping request den code 200 zurück.
Jedoch, wenn die IP regestriert ist, wird der Ping-Request ein 202 zurückschicken.
Dieser Statuscode sollte benutzt werden um zu gucken, ob der Server das Gerät regestriert hat.