import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../models/device.dart';
import 'package:multicast_dns/multicast_dns.dart';
import 'dart:async';
import 'dart:io';

class ConnectScreen extends StatefulWidget {
  const ConnectScreen({super.key});

  @override
  State<ConnectScreen> createState() => _ConnectScreenState();
}

class _ConnectScreenState extends State<ConnectScreen> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _ipController = TextEditingController();
  final List<Device> _discoveredDevices = [];
  bool _isScanning = false;
  String _statusMessage = 'Press scan to discover devices';

  @override
  void dispose() {
    _nameController.dispose();
    _ipController.dispose();
    super.dispose();
  }

  Future<List<InternetAddress>> _getActiveNetworkAddresses() async {
    final interfaces = await NetworkInterface.list(
      type: InternetAddressType.IPv4,
      includeLinkLocal: false,
      includeLoopback: false,
    );

    final addresses = <InternetAddress>[];
    for (final interface in interfaces) {
      for (final address in interface.addresses) {
        if (_isUsableNetworkIp(address.address)) {
          addresses.add(address);
        }
      }
    }
    return addresses;
  }

  bool _isUsableNetworkIp(String ip) {
    if (ip == '0.0.0.0') return false;
    return !_isLoopbackOrLinkLocal(ip);
  }

  bool _isLoopbackOrLinkLocal(String ip) {
    final parts = ip.split('.');
    if (parts.length != 4) return true;
    final first = int.tryParse(parts[0]);
    final second = int.tryParse(parts[1]);
    if (first == null || second == null) return true;
    if (first == 127) return true;
    if (first == 169 && second == 254) return true;
    return false;
  }

  bool _isSameSubnet24(String firstIp, String secondIp) {
    final firstParts = firstIp.split('.');
    final secondParts = secondIp.split('.');
    if (firstParts.length != 4 || secondParts.length != 4) return false;
    return firstParts[0] == secondParts[0] &&
        firstParts[1] == secondParts[1] &&
        firstParts[2] == secondParts[2];
  }

  bool _belongsToActiveNetwork(String discoveredIp, List<InternetAddress> localAddresses) {
    if (!_isUsableNetworkIp(discoveredIp)) return false;
    if (localAddresses.isEmpty) return true;
    return localAddresses.any((local) => _isSameSubnet24(discoveredIp, local.address));
  }

  String _scanErrorMessage(Object error) {
    if (error is SocketException) {
      final errorCode = error.osError?.errorCode;
      if (Platform.isWindows && errorCode == 10042) {
        return 'mDNS konnte unter Windows nicht gestartet werden (Socket Option nicht unterstützt). '
            'Das liegt nicht daran, dass kein Server läuft. Bitte VPN/Firewall prüfen und erneut versuchen.';
      }
      return 'Network error while scanning: ${error.message}';
    }
    return 'Error scanning: $error';
  }

  Future<void> _scanForDevices() async {
    setState(() {
      _isScanning = true;
      _statusMessage = 'Scanning for devices...';
      _discoveredDevices.clear();
    });

    try {
      final String serviceType = '_repcc._tcp';
      final MDnsClient client = MDnsClient();
      final localNetworkAddresses = await _getActiveNetworkAddresses();
      
      await client.start();

      await for (final PtrResourceRecord ptr in client.lookup<PtrResourceRecord>(
        ResourceRecordQuery.serverPointer(serviceType),
      )) {
        await for (final SrvResourceRecord srv in client.lookup<SrvResourceRecord>(
          ResourceRecordQuery.service(ptr.domainName),
        )) {
          // Get the IP address
          String? ipAddress;
          await for (final IPAddressResourceRecord ip in client.lookup<IPAddressResourceRecord>(
            ResourceRecordQuery.addressIPv4(srv.target),
          )) {
            ipAddress = ip.address.address;
            break;
          }

          // Get TXT records for additional info (MAC address, ports)
          String macAddress = 'Unknown';
          List<int> ports = [];
          
          await for (final TxtResourceRecord txt in client.lookup<TxtResourceRecord>(
            ResourceRecordQuery.text(ptr.domainName),
          )) {
            // Split the text by newline to get individual entries
            for (final String entry in txt.text.split('\n')) {
              if (entry.startsWith('mac=')) {
                macAddress = entry.substring(4);
              } else if (entry.startsWith('ports=')) {
                final portsStr = entry.substring(6);
                ports = portsStr.split(',').map((p) => int.tryParse(p.trim()) ?? 0).where((p) => p != 0).toList();
              }
            }
            break;
          }

          if (ipAddress != null && _belongsToActiveNetwork(ipAddress, localNetworkAddresses)) {
            final device = Device(
              id: ipAddress,
              name: srv.target,
              ipAddress: ipAddress,
              macAddress: macAddress,
              ports: ports.isNotEmpty ? ports : [8080],
              isConnected: false,
            );

            if (!mounted) return;
            setState(() {
              if (!_discoveredDevices.any((d) => d.id == device.id)) {
                _discoveredDevices.add(device);
              }
            });
          }
        }
      }

      client.stop();

      if (!mounted) return;
      setState(() {
        _isScanning = false;
        _statusMessage = _discoveredDevices.isEmpty
          ? (localNetworkAddresses.isEmpty
            ? 'No active network found. Please connect to Wi-Fi/LAN.'
            : 'No devices found in your current network.')
            : 'Found ${_discoveredDevices.length} device(s)';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isScanning = false;
        _statusMessage = _scanErrorMessage(e);
      });
    }
  }

  void _selectDevice(Device device) {
    Navigator.pop(context, device);
  }

  void _addDevice() {
    final String name = _nameController.text.trim();
    final String ipAddress = _ipController.text.trim();

    if (name.isNotEmpty && ipAddress.isNotEmpty) {
      // Create a new Device object manually (for testing/manual entry)
      final newDevice = Device(
        id: ipAddress,
        name: name,
        ipAddress: ipAddress,
        macAddress: 'Unknown',
        ports: [8080],
        isConnected: true,
      );

      Navigator.pop(context, newDevice);
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Bitte Name und IP-Adresse eingeben.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        width: double.infinity,
        height: double.infinity,
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(
              'Connect a new Device',
              style: TextStyle(color: Colors.white, fontSize: 20, fontFamily: 'JetBrainsMono', fontWeight: FontWeight.normal),
            ),
            const SizedBox(height: 20),
            
            // Scan button
            ElevatedButton.icon(
              onPressed: _isScanning ? null : _scanForDevices,
              icon: _isScanning 
                  ? SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : Icon(Icons.search),
              label: Text(_isScanning ? 'Scanning...' : 'Scan for Devices', style: TextStyle(fontFamily: 'JetBrainsMono')),
              style: ElevatedButton.styleFrom(
                padding: EdgeInsets.symmetric(horizontal: 20, vertical: 15),
              ),
            ),
            
            const SizedBox(height: 10),
            
            // Status message
            Text(
              _statusMessage,
              style: TextStyle(color: Colors.white70, fontSize: 14, fontFamily: 'JetBrainsMono'),
              textAlign: TextAlign.center,
            ),
            
            const SizedBox(height: 20),
            
            // List of discovered devices
            Expanded(
              child: _discoveredDevices.isEmpty
                  ? Center(
                      child: Text(
                        'No devices discovered yet',
                        style: TextStyle(color: Colors.white54, fontFamily: 'JetBrainsMono'),
                      ),
                    )
                  : ListView.builder(
                      itemCount: _discoveredDevices.length,
                      itemBuilder: (context, index) {
                        final device = _discoveredDevices[index];
                        return Card(
                          color: Color(0xFF202020),
                          child: ListTile(
                            leading: Icon(Icons.computer, color: Colors.white),
                            title: Text(
                              device.name,
                              style: TextStyle(color: Colors.white, fontFamily: 'JetBrainsMono'),
                            ),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('IP: ${device.ipAddress}', style: TextStyle(color: Colors.white70, fontSize: 12)),
                                Text('MAC: ${device.macAddress}', style: TextStyle(color: Colors.white70, fontSize: 12)),
                                Text('Ports: ${device.ports.join(", ")}', style: TextStyle(color: Colors.white70, fontSize: 12)),
                              ],
                            ),
                            trailing: Icon(Icons.arrow_forward_ios, color: Colors.white70, size: 16),
                            onTap: () => _selectDevice(device),
                          ),
                        );
                      },
                    ),
            ),
            
            const SizedBox(height: 20),
            
            // Manual entry option
            ExpansionTile(
              title: Text(
                'Or Add Manually',
                style: TextStyle(color: Colors.white70, fontFamily: 'JetBrainsMono', fontSize: 14),
              ),
              iconColor: Colors.white70,
              collapsedIconColor: Colors.white70,
              children: [
                Padding(
                  padding: const EdgeInsets.all(10),
                  child: Column(
                    children: [
                      TextField(
                        controller: _nameController,
                        style: const TextStyle(color: Colors.white, fontFamily: 'JetBrainsMono'),
                        decoration: InputDecoration(
                          hintText: 'Enter Device Name',
                          hintStyle: TextStyle(color: Colors.white54, fontFamily: 'JetBrainsMono'),
                          enabledBorder: OutlineInputBorder(
                            borderSide: BorderSide(color: Colors.white30),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderSide: BorderSide(color: Colors.white),
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: _ipController,
                        style: const TextStyle(color: Colors.white, fontFamily: 'JetBrainsMono'),
                        decoration: InputDecoration(
                          hintText: 'Enter IP Address',
                          hintStyle: TextStyle(color: Colors.white54, fontFamily: 'JetBrainsMono'),
                          enabledBorder: OutlineInputBorder(
                            borderSide: BorderSide(color: Colors.white30),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderSide: BorderSide(color: Colors.white),
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
                      ElevatedButton(
                        onPressed: _addDevice,
                        child: Text('Add Device', style: TextStyle(fontFamily: 'JetBrainsMono')),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 20),
            
            // Back button
            FloatingActionButton(
              heroTag: 'back',
              backgroundColor: Colors.grey[800],
              onPressed: () {
                Navigator.pop(context);
              }, 
              child: SvgPicture.asset(
                'assets/Icons/arrow_back.svg',
                width: 24,
                height: 24,
                colorFilter: ColorFilter.mode(Colors.white, BlendMode.srcIn),
              ),
            ),
          ],
        ),
      ),
    );
  }
}