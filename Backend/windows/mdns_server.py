"""
RePCC mDNS Server
This script advertises the computer on the local network using mDNS
so that the RePCC Android app can discover it.
"""

from zeroconf import ServiceInfo, Zeroconf
import socket
import uuid
import os

def get_local_ip():
    """Get a LAN-reachable IPv4 for mDNS advertisement."""

    forced_ip = os.getenv("REPCC_MDNS_IP", "").strip()
    if forced_ip:
        return forced_ip

    def is_usable(ip: str) -> bool:
        if ip == "127.0.0.1":
            return False
        if ip.startswith("169.254."):
            return False
        return True

    def is_preferred_private(ip: str) -> bool:
        return (
            ip.startswith("192.168.")
            or ip.startswith("10.")
            or (ip.startswith("172.") and len(ip.split(".")) > 1 and 16 <= int(ip.split(".")[1]) <= 31)
        )

    candidates = []

    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        for _, _, _, _, sockaddr in infos:
            ip = sockaddr[0]
            if is_usable(ip) and ip not in candidates:
                candidates.append(ip)
    except Exception:
        pass

    # Ask routing table for outbound interface without sending traffic.
    for target in (("10.255.255.255", 1), ("8.8.8.8", 80)):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(target)
            ip = sock.getsockname()[0]
            if is_usable(ip) and ip not in candidates:
                candidates.append(ip)
        except Exception:
            pass
        finally:
            if sock:
                sock.close()

    preferred = [ip for ip in candidates if is_preferred_private(ip)]
    if preferred:
        return preferred[0]
    if candidates:
        return candidates[0]
    return "127.0.0.1"

def get_mac_address():
    """Get the MAC address of the machine"""
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                    for elements in range(0, 2 * 6, 2)][::-1])
    return mac

def register_mdns_service():
    """Register the mDNS service for RePCC"""
    zeroconf = Zeroconf()
    
    # Get local information
    local_ip = get_local_ip()
    mac_address = get_mac_address()
    hostname = socket.gethostname()
    
    # Service details
    service_type = "_repcc._tcp.local."
    service_name = f"{hostname}.{service_type}"
    port = 8080
    
    # Additional information in TXT records
    properties = {
        'mac': mac_address.encode('utf-8'),
        'ports': '8080,8081'.encode('utf-8'),  # Comma-separated list of ports
    }
    
    # Create service info
    info = ServiceInfo(
        service_type,
        service_name,
        addresses=[socket.inet_aton(local_ip)],
        port=port,
        properties=properties,
        server=f"{hostname}.local.",
    )
    
    print(f"Registering mDNS service...")
    print(f"  Service Name: {service_name}")
    print(f"  IP Address: {local_ip}")
    print("  Tip: set REPCC_MDNS_IP=<your LAN IPv4> to force advertised address")
    print(f"  MAC Address: {mac_address}")
    print(f"  Port: {port}")
    print(f"  Additional Ports: 8080, 8081")
    print(f"\nService is now discoverable on the local network.")
    print("Press Ctrl+C to stop...")
    
    zeroconf.register_service(info)
    
    try:
        # Keep the service running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nUnregistering service...")
    finally:
        zeroconf.unregister_service(info)
        zeroconf.close()
        print("Service stopped.")

if __name__ == "__main__":
    # Check if zeroconf is installed
    try:
        import zeroconf
        register_mdns_service()
    except ImportError:
        print("Error: zeroconf package is not installed.")
        print("Please install it using: pip install zeroconf")
