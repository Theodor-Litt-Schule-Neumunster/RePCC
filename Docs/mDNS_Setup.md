# RePCC mDNS Integration

This document explains how the mDNS service discovery works in RePCC and how to set it up.

## Overview

RePCC uses **mDNS (Multicast DNS)** to automatically discover computers on the local network. The Android app can scan for available servers, and users can connect to them without manually entering IP addresses.

## Architecture

### Client (Flutter App)
- **connect.dart**: Implements mDNS scanning using the `multicast_dns` package
- Discovers services of type `_repcc._tcp`
- Retrieves device information: IP address, MAC address, and ports
- Displays discovered devices in a list for user selection

### Server (Python Backend)
- **mdns_server.py**: Advertises the computer on the local network
- Uses the `zeroconf` package to broadcast the service
- Publishes IP address, MAC address, and available ports via TXT records

### Device Model
The `Device` class stores:
- `id`: Unique identifier (typically the IP address)
- `name`: Device hostname
- `ipAddress`: IPv4 address
- `macAddress`: MAC address
- `ports`: List of available ports
- `isConnected`: Connection status

## Setup Instructions

### Backend Server Setup

1. **Install Python dependencies**:
   ```bash
   cd Backend/windows
   pip install zeroconf
   ```

2. **Run the mDNS server**:
   ```bash
   python mdns_server.py
   ```

   The server will output:
   ```
   Registering mDNS service...
     Service Name: YOUR-COMPUTER._repcc._tcp.local.
     IP Address: 192.168.x.x
     MAC Address: xx:xx:xx:xx:xx:xx
     Port: 8080
     Additional Ports: 8080, 8081
   
   Service is now discoverable on the local network.
   Press Ctrl+C to stop...
   ```

### Flutter App Setup

1. **Install dependencies**:
   ```bash
   cd App/repcc_android
   flutter pub get
   ```

2. **Run the app**:
   ```bash
   flutter run
   ```

3. **Scan for devices**:
   - Open the app
   - Tap "Add Device"
   - Tap "Scan for Devices"
   - Select a discovered device from the list

## How It Works

### Service Discovery Process

1. **Server broadcasts**: The Python server registers a service of type `_repcc._tcp.local.` with mDNS
2. **Client scans**: The Flutter app queries for PTR records matching `_repcc._tcp`
3. **Service resolution**: For each discovered service:
   - Queries SRV records to get the port and hostname
   - Queries A records to get the IPv4 address
   - Queries TXT records to get additional info (MAC address, ports)
4. **Device creation**: Creates a `Device` object with all the information
5. **User selection**: User taps on a device to add it to their list

### mDNS Service Structure

```
Service Type: _repcc._tcp.local.
Service Name: <hostname>._repcc._tcp.local.
Port: 8080
TXT Records:
  - mac=xx:xx:xx:xx:xx:xx
  - ports=8080,8081
```

## Troubleshooting

### Devices not discovered

1. **Firewall**: Ensure your firewall allows mDNS traffic (UDP port 5353)
2. **Network**: Both devices must be on the same local network
3. **Server running**: Verify the Python server is running
4. **Permissions**: The Android app needs network permissions

### Connection issues

1. Check that the ports listed are actually open on the server
2. Verify the IP address is correct
3. Ensure no network isolation (some guest networks block device-to-device communication)

## Manual Device Entry

If mDNS discovery doesn't work, users can manually add devices by:
1. Expanding "Or Add Manually" section
2. Entering the device name
3. Tapping "Add Device"

Note: Manual entry creates a test device with placeholder information.

## Future Enhancements

- [ ] Persistent device storage (save devices between app sessions)
- [ ] Automatic reconnection to previously connected devices
- [ ] Real-time connection status updates
- [ ] Support for IPv6 addresses
- [ ] Secure pairing mechanism
- [ ] Custom service icons based on device type
