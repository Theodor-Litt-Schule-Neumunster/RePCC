from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

import uuid
import requests

class TestListener(ServiceListener):

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} updated")
        self._handle_Service(zc, type_, name)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} removed")

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} added")
        self._handle_Service(zc, type_, name)

    def _handle_Service(self, zc: Zeroconf, type_:str, name:str):
        info = zc.get_service_info(type_, name)

        if info and "repcc" in name.lower():
            print("Found RePCC Service!")
            print("ATTEMTING CONNECTION")

            devicemac = ':'.join(('%012X' % uuid.getnode())[i:i+2] for i in range(0, 12, 2))

            ip = info.parsed_addresses()[0]
            props = info.properties
            twofa = props[b"2fa"].decode('utf-8') # type: ignore

            addr = f"http://{ip}:15248/connect"
            print(props)

            r = requests.post(url=addr, json={
                "mac":devicemac,
                "2fa":twofa
            })

            if r.status_code == 202 or r.status_code == 200:
                print("OK!")
            else:
                print(f"Response is not 202. Code: {r.status_code}")



# Create a single Zeroconf instance to share
zeroconf = Zeroconf()
listener = TestListener()
browser = ServiceBrowser(zeroconf, "_http._tcp.local.", listener)

try:
    input("Press enter to exit...\n\n")
finally:
    zeroconf.close()