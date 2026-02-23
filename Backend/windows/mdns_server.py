"""
RePCC mDNS Server
This script advertises the computer on the local network using mDNS
so that the RePCC Android app can discover it.
"""

from zeroconf import ServiceInfo, Zeroconf
import socket
import uuid

def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        # Create a socket to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
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
