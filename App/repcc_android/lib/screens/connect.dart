import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../models/device.dart';
import 'package:multicast_dns/multicast_dns.dart';
import 'dart:async';
import 'dart:io';

// TODO: Send pings every 10s to enable connection status updates (ping on connect, then start timer that pings every 10s, cancel on disconnect)

class ConnectScreen extends StatefulWidget {
  const ConnectScreen({super.key});

  @override
  State<ConnectScreen> createState() => _ConnectScreenState();
}

class _ConnectScreenState extends State<ConnectScreen> {
  final List<Device> _discoveredDevices = [];
  bool _isScanning = false;
  String _statusMessage = 'Press scan to discover devices';

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

  bool _belongsToActiveNetwork(
      String discoveredIp, List<InternetAddress> localAddresses) {
    if (!_isUsableNetworkIp(discoveredIp)) return false;
    if (localAddresses.isEmpty) return true;
    return localAddresses
        .any((local) => _isSameSubnet24(discoveredIp, local.address));
  }

  int? _extractSocketErrorCode(Object error) {
    if (error is SocketException) return error.osError?.errorCode;
    if (error is OSError) return error.errorCode;

    final match = RegExp(r'errno\s*=\s*(\d+)').firstMatch(error.toString());
    return match != null ? int.tryParse(match.group(1)!) : null;
  }

  String _scanErrorMessage(Object error) {
    final errorCode = _extractSocketErrorCode(error);

    if (Platform.isWindows && errorCode == 10042) {
      return 'mDNS konnte unter Windows nicht gestartet werden (Socket-Option nicht unterstützt, errno 10042). '
          'Häufige Ursache: VPN/virtuelle Netzwerkadapter oder Firewall. Bitte diese kurz deaktivieren und erneut scannen.';
    }

    if (error is SocketException) {
      return 'Network error while scanning: ${error.message}';
    }

    if (error is OSError) {
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
      final String serviceType = '_repcc._tcp.local.';
      final MDnsClient client = MDnsClient();
      final localNetworkAddresses = await _getActiveNetworkAddresses();

      await client.start();

      await for (final PtrResourceRecord ptr
          in client.lookup<PtrResourceRecord>(
        ResourceRecordQuery.serverPointer(serviceType),
      )) {
        await for (final SrvResourceRecord srv
            in client.lookup<SrvResourceRecord>(
          ResourceRecordQuery.service(ptr.domainName),
        )) {
          // Get the IP address
          String? ipAddress;
          await for (final IPAddressResourceRecord ip
              in client.lookup<IPAddressResourceRecord>(
            ResourceRecordQuery.addressIPv4(srv.target),
          )) {
            ipAddress = ip.address.address;
            break;
          }

          // Get TXT records for additional info (MAC address, ports)
          String macAddress = 'Unknown';
          List<int> ports = [];

          await for (final TxtResourceRecord txt
              in client.lookup<TxtResourceRecord>(
            ResourceRecordQuery.text(ptr.domainName),
          )) {
            // Split the text by newline to get individual entries
            for (final String entry in txt.text.split('\n')) {
              if (entry.startsWith('mac=')) {
                macAddress = entry.substring(4);
              } else if (entry.startsWith('ports=')) {
                final portsStr = entry.substring(6);
                ports = portsStr
                    .split(',')
                    .map((p) => int.tryParse(p.trim()) ?? 0)
                    .where((p) => p != 0)
                    .toList();
              }
            }
            break;
          }

          if (ipAddress != null &&
              _belongsToActiveNetwork(ipAddress, localNetworkAddresses)) {
            final device = Device(
              id: ipAddress,
              name: srv.target.replaceAll(RegExp(r'\.local$'), ''),
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

  Future<void> _showManualAddDialog() async {
    final nameController = TextEditingController();
    final ipController = TextEditingController();

    final newDevice = await showDialog<Device>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Add Device Manually'),
        content: SizedBox(
          width: 420,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                style: TextStyle(
                    color: Theme.of(context).colorScheme.onSurface,
                    fontFamily: 'JetBrainsMono'),
                decoration: const InputDecoration(
                  labelText: 'Device Name',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: ipController,
                style: TextStyle(
                    color: Theme.of(context).colorScheme.onSurface,
                    fontFamily: 'JetBrainsMono'),
                decoration: const InputDecoration(
                  labelText: 'IP Address',
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          FilledButton.icon(
            onPressed: () {
              final name = nameController.text.trim();
              final ipAddress = ipController.text.trim();
              if (name.isEmpty || ipAddress.isEmpty) return;

              Navigator.pop(
                dialogContext,
                Device(
                  id: ipAddress,
                  name: name,
                  ipAddress: ipAddress,
                  macAddress: 'Unknown',
                  ports: [8080],
                  isConnected: false,
                ),
              );
            },
            icon: SvgPicture.asset(
              'assets/Icons/add.svg',
              colorFilter: ColorFilter.mode(
                  Theme.of(context).colorScheme.onPrimary, BlendMode.srcIn),
              width: 18,
              height: 18,
            ),
            label: const Text('Add Device'),
          ),
        ],
      ),
    );

    nameController.dispose();
    ipController.dispose();

    if (newDevice == null || !mounted) return;
    Navigator.pop(context, newDevice);
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: () => Navigator.pop(context),
          icon: SvgPicture.asset(
            'assets/Icons/home.svg',
            colorFilter:
                ColorFilter.mode(colorScheme.onTertiary, BlendMode.srcIn),
            width: 24,
            height: 24,
          ),
        ),
        title: const Text('Connect'),
      ),
      body: Container(
        width: double.infinity,
        height: double.infinity,
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 110),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(
              'Connect a new Device',
              style: TextStyle(
                  color: colorScheme.onSurface,
                  fontSize: 20,
                  fontFamily: 'JetBrainsMono',
                  fontWeight: FontWeight.normal),
            ),
            const SizedBox(height: 20),

            // Status message
            Text(
              _statusMessage,
              style: TextStyle(
                  color: colorScheme.onSurface.withOpacity(0.7),
                  fontSize: 14,
                  fontFamily: 'JetBrainsMono'),
              textAlign: TextAlign.center,
            ),

            const SizedBox(height: 20),

            // List of discovered devices
            Expanded(
              child: _discoveredDevices.isEmpty
                  ? Center(
                      child: Text(
                        'No devices discovered yet',
                        style: TextStyle(
                            color: colorScheme.onSurface.withOpacity(0.54),
                            fontFamily: 'JetBrainsMono'),
                      ),
                    )
                  : ListView.builder(
                      itemCount: _discoveredDevices.length,
                      itemBuilder: (context, index) {
                        final device = _discoveredDevices[index];
                        return Card(
                          color: colorScheme.tertiary,
                          child: ListTile(
                            leading: SvgPicture.asset(
                              'assets/Icons/computer.svg',
                              colorFilter: ColorFilter.mode(
                                  colorScheme.onTertiary, BlendMode.srcIn),
                              width: 24,
                              height: 24,
                            ),
                            title: Text(
                              device.name,
                              style: TextStyle(
                                  color: colorScheme.onTertiary,
                                  fontFamily: 'JetBrainsMono'),
                            ),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('IP: ${device.ipAddress}',
                                    style: TextStyle(
                                        color: colorScheme.onTertiary
                                            .withOpacity(0.7),
                                        fontSize: 12)),
                                Text('MAC: ${device.macAddress}',
                                    style: TextStyle(
                                        color: colorScheme.onTertiary
                                            .withOpacity(0.7),
                                        fontSize: 12)),
                                Text('Ports: ${device.ports.join(", ")}',
                                    style: TextStyle(
                                        color: colorScheme.onTertiary
                                            .withOpacity(0.7),
                                        fontSize: 12)),
                              ],
                            ),
                            trailing: SvgPicture.asset(
                              'assets/Icons/arrow_forward.svg',
                              colorFilter: ColorFilter.mode(
                                  colorScheme.onTertiary.withOpacity(0.7),
                                  BlendMode.srcIn),
                              width: 16,
                              height: 16,
                            ),
                            onTap: () => _selectDevice(device),
                          ),
                        );
                      },
                    ),
            ),

            const SizedBox(height: 20),
          ],
        ),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Row(
          mainAxisSize: MainAxisSize.max,
          children: [
            Expanded(
              child: SizedBox(
                height: 56,
                child: FloatingActionButton.extended(
                  heroTag: 'connectManualAddFab',
                  onPressed: _showManualAddDialog,
                  icon: SvgPicture.asset(
                    'assets/Icons/add.svg',
                    colorFilter: ColorFilter.mode(
                        colorScheme.onPrimary, BlendMode.srcIn),
                    width: 20,
                    height: 20,
                  ),
                  label: const Text(
                    'Add Manually',
                    style: TextStyle(fontFamily: 'JetBrainsMono'),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: SizedBox(
                height: 56,
                child: FloatingActionButton.extended(
                  heroTag: 'connectScanFab',
                  onPressed: _isScanning ? null : _scanForDevices,
                  icon: _isScanning
                      ? SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: colorScheme.onPrimary,
                          ),
                        )
                      : SvgPicture.asset(
                          'assets/Icons/search.svg',
                          colorFilter: ColorFilter.mode(
                              colorScheme.onPrimary, BlendMode.srcIn),
                          width: 20,
                          height: 20,
                        ),
                  label: Text(
                    _isScanning ? 'Scanning...' : 'Scan',
                    style: const TextStyle(fontFamily: 'JetBrainsMono'),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
