import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';
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
  static const MethodChannel _networkChannel = MethodChannel('repcc/network');
  final List<Device> _discoveredDevices = [];
  bool _isScanning = false;
  String _statusMessage = 'Press scan to discover devices';
  final bool _enableMdnsLogging = true;

  void _logMdns(String message) {
    if (!_enableMdnsLogging) return;
    debugPrint('[mDNS] $message');
  }

  Future<void> _acquireAndroidMulticastLock() async {
    if (!Platform.isAndroid) return;
    try {
      final acquired =
          await _networkChannel.invokeMethod<bool>('acquireMulticastLock');
      _logMdns('Android multicast lock acquired: ${acquired == true}');
    } catch (e) {
      _logMdns('Failed to acquire Android multicast lock: $e');
    }
  }

  Future<void> _releaseAndroidMulticastLock() async {
    if (!Platform.isAndroid) return;
    try {
      await _networkChannel.invokeMethod<bool>('releaseMulticastLock');
      _logMdns('Android multicast lock released');
    } catch (e) {
      _logMdns('Failed to release Android multicast lock: $e');
    }
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

  List<int>? _parseIpv4Parts(String ip) {
    final parts = ip.split('.');
    if (parts.length != 4) return null;

    final values = <int>[];
    for (final part in parts) {
      final parsed = int.tryParse(part);
      if (parsed == null || parsed < 0 || parsed > 255) {
        return null;
      }
      values.add(parsed);
    }
    return values;
  }

  bool _isSameSubnet24(String ipA, String ipB) {
    final a = _parseIpv4Parts(ipA);
    final b = _parseIpv4Parts(ipB);
    if (a == null || b == null) return false;
    return a[0] == b[0] && a[1] == b[1] && a[2] == b[2];
  }

  bool _belongsToActiveNetwork(
      String discoveredIp, List<InternetAddress> localAddresses) {
    if (!_isUsableNetworkIp(discoveredIp)) return false;
    if (localAddresses.isEmpty) {
      // If local interfaces cannot be determined, keep previous behavior.
      return true;
    }

    return localAddresses
        .any((local) => _isSameSubnet24(discoveredIp, local.address));
  }

  Iterable<String> _txtEntries(String text) {
    return text
        .split(RegExp(r'[\n;,]+'))
        .map((entry) => entry.trim())
        .where((entry) => entry.isNotEmpty);
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

    MDnsClient? client;

    try {
      final String serviceType = '_repcc._tcp.local';
      client = MDnsClient();
      final localNetworkAddresses = await _getActiveNetworkAddresses();

      _logMdns('Starting scan for service type "$serviceType"');
      _logMdns(
          'Active local IPv4 addresses: ${localNetworkAddresses.map((a) => a.address).join(', ')}');

      await _acquireAndroidMulticastLock();
      await client.start();
      _logMdns('mDNS client started');

      await for (final PtrResourceRecord ptr
          in client.lookup<PtrResourceRecord>(
        ResourceRecordQuery.serverPointer(serviceType),
      )) {
        _logMdns('PTR found: ${ptr.domainName}');

        await for (final SrvResourceRecord srv
            in client.lookup<SrvResourceRecord>(
          ResourceRecordQuery.service(ptr.domainName),
        )) {
          _logMdns(
              'SRV found: target=${srv.target}, port=${srv.port}, priority=${srv.priority}, weight=${srv.weight}');

          final normalizedTarget = srv.target.replaceFirst(RegExp(r'\.$'), '');

          // Get the IP address
          String? ipAddress;
          await for (final IPAddressResourceRecord ip
              in client.lookup<IPAddressResourceRecord>(
            ResourceRecordQuery.addressIPv4(srv.target),
          )) {
            ipAddress = ip.address.address;
            _logMdns('A record found for ${srv.target}: $ipAddress');
            break;
          }

          if (ipAddress == null && normalizedTarget != srv.target) {
            await for (final IPAddressResourceRecord ip
                in client.lookup<IPAddressResourceRecord>(
              ResourceRecordQuery.addressIPv4(normalizedTarget),
            )) {
              ipAddress = ip.address.address;
              _logMdns(
                  'A record fallback found for $normalizedTarget: $ipAddress');
              break;
            }
          }

          if (ipAddress == null) {
            _logMdns('No IPv4 A record found for ${srv.target}; skipping');
            continue;
          }

          // Get TXT records for additional info (MAC address, ports)
          String macAddress = 'Unknown';
          List<int> ports = [];

          await for (final TxtResourceRecord txt
              in client.lookup<TxtResourceRecord>(
            ResourceRecordQuery.text(ptr.domainName),
          )) {
            _logMdns('TXT found for ${ptr.domainName}: ${txt.text}');

            for (final String entry in _txtEntries(txt.text)) {
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

          _logMdns(
              'Parsed TXT data for ${srv.target}: mac=$macAddress, ports=$ports');

          if (_belongsToActiveNetwork(ipAddress, localNetworkAddresses)) {
            final device = Device(
              id: ipAddress,
              name: normalizedTarget.replaceAll(RegExp(r'\.local\.?$'), ''),
              ipAddress: ipAddress,
              macAddress: macAddress,
              ports: ports.isNotEmpty ? ports : [8080],
              isConnected: false,
            );

            if (!mounted) return;
            setState(() {
              if (!_discoveredDevices.any((d) => d.id == device.id)) {
                _discoveredDevices.add(device);
                _logMdns(
                    'Device accepted: name=${device.name}, ip=${device.ipAddress}, mac=${device.macAddress}, ports=${device.ports.join(', ')}');
              } else {
                _logMdns('Duplicate device ignored for ip=${device.ipAddress}');
              }
            });
          } else {
            _logMdns(
                'Device filtered out (not in active network): ip=$ipAddress, local=${localNetworkAddresses.map((a) => a.address).join(', ')}');
          }
        }
      }

      if (!mounted) return;
      setState(() {
        _isScanning = false;
        _statusMessage = _discoveredDevices.isEmpty
            ? (localNetworkAddresses.isEmpty
                ? 'No active network found. Please connect to Wi-Fi/LAN.'
                : 'No devices found in your current network.')
            : 'Found ${_discoveredDevices.length} device(s)';
      });

      _logMdns('Scan finished. Found ${_discoveredDevices.length} device(s).');
    } catch (e) {
      _logMdns('Scan error: $e');
      if (!mounted) return;
      setState(() {
        _isScanning = false;
        _statusMessage = _scanErrorMessage(e);
      });
    } finally {
      if (client != null) {
        try {
          client.stop();
          _logMdns('mDNS client stopped');
        } catch (stopError) {
          _logMdns('Error while stopping mDNS client: $stopError');
        }
      }
      await _releaseAndroidMulticastLock();
    }
  }

  @override
  void dispose() {
    _releaseAndroidMulticastLock();
    super.dispose();
  }

  void _selectDevice(Device device) {
    if (!mounted) return;

    final navigator = Navigator.maybeOf(context);
    if (navigator == null || !navigator.canPop()) {
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        const SnackBar(
          content: Text('Unable to return selected device right now.'),
        ),
      );
      return;
    }

    navigator.pop(device);
  }

  bool _isValidHostname(String value) {
    if (value.toLowerCase() == 'localhost') return false;

    // Accept simple LAN hostnames like "office-pc" or "office-pc.local".
    final hostnameRegex = RegExp(
      r'^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$',
    );
    return hostnameRegex.hasMatch(value);
  }

  bool _isValidIpv4(String value) {
    final parts = value.split('.');
    if (parts.length != 4) return false;
    for (final part in parts) {
      final segment = int.tryParse(part);
      if (segment == null || segment < 0 || segment > 255) {
        return false;
      }
    }

    // Reject unroutable/manual-invalid addresses for device targets.
    if (!_isUsableNetworkIp(value)) return false;

    return true;
  }

  ({String host, int? port})? _parseManualAddress(String input) {
    final trimmed = input.trim();
    if (trimmed.isEmpty) return null;

    // Supports "host" and "host:port" (IPv4 or hostname).
    final separatorIndex = trimmed.lastIndexOf(':');
    if (separatorIndex > 0 && separatorIndex < trimmed.length - 1) {
      final host = trimmed.substring(0, separatorIndex).trim();
      final portRaw = trimmed.substring(separatorIndex + 1).trim();
      final port = int.tryParse(portRaw);
      if (port == null || port < 1 || port > 65535) {
        return null;
      }
      if (!_isValidIpv4(host) && !_isValidHostname(host)) {
        return null;
      }
      return (host: host, port: port);
    }

    if (!_isValidIpv4(trimmed) && !_isValidHostname(trimmed)) {
      return null;
    }

    return (host: trimmed, port: null);
  }

  Future<void> _showManualAddDialog() async {
    final nameController = TextEditingController();
    final ipController = TextEditingController();
    final rootMessenger = ScaffoldMessenger.maybeOf(context);

    Device? newDevice;
    try {
      newDevice = await showDialog<Device>(
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
                try {
                  final name = nameController.text.trim();
                  final rawAddress = ipController.text.trim();
                  if (name.isEmpty || rawAddress.isEmpty) {
                    (ScaffoldMessenger.maybeOf(dialogContext) ?? rootMessenger)
                        ?.showSnackBar(
                      const SnackBar(
                        content: Text('Name and IP/hostname are required.'),
                      ),
                    );
                    return;
                  }

                  final parsedAddress = _parseManualAddress(rawAddress);
                  if (parsedAddress == null) {
                    (ScaffoldMessenger.maybeOf(dialogContext) ?? rootMessenger)
                        ?.showSnackBar(
                      const SnackBar(
                        content: Text(
                            'Enter a valid IPv4/hostname, optionally with :port.'),
                      ),
                    );
                    return;
                  }

                  final ports = <int>[parsedAddress.port ?? 8080];
                  Navigator.pop(
                    dialogContext,
                    Device(
                      id: parsedAddress.host,
                      name: name,
                      ipAddress: parsedAddress.host,
                      macAddress: 'Unknown',
                      ports: ports,
                      isConnected: false,
                    ),
                  );
                } catch (error, stackTrace) {
                  if (kDebugMode) {
                    debugPrint('Manual add failed: $error');
                    debugPrintStack(stackTrace: stackTrace);
                  }
                  (ScaffoldMessenger.maybeOf(dialogContext) ?? rootMessenger)
                      ?.showSnackBar(
                    SnackBar(
                      content: Text(
                        kDebugMode
                            ? 'Manual add failed: ${error.toString()}'
                            : 'Manual add failed. Please check your input.',
                      ),
                    ),
                  );
                }
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
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Manual add dialog failed: $error');
        debugPrintStack(stackTrace: stackTrace);
      }
      rootMessenger?.showSnackBar(
        SnackBar(
          content: Text(
            kDebugMode
                ? 'Manual add dialog failed: ${error.toString()}'
                : 'Unable to open manual add dialog right now.',
          ),
        ),
      );
    } finally {
      // Dispose controllers after the dialog teardown frame to avoid
      // "TextEditingController used after dispose" during route animations.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        nameController.dispose();
        ipController.dispose();
      });
    }

    if (newDevice == null || !mounted) return;
    try {
      _selectDevice(newDevice);
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('Selecting manual device failed: $error');
        debugPrintStack(stackTrace: stackTrace);
      }
      rootMessenger?.showSnackBar(
        SnackBar(
          content: Text(
            kDebugMode
                ? 'Failed to add selected device: ${error.toString()}'
                : 'Failed to add selected device.',
          ),
        ),
      );
    }
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
