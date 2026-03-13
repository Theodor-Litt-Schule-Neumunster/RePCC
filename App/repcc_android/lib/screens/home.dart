import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:flutter/foundation.dart';
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import '../models/device.dart';
import 'connect.dart';
import 'macros.dart';
import 'presenter.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  static const Duration _statusPollInterval = Duration(seconds: 10);

  // List of devices managed by the state - now starts empty
  List<Device> devices = [];
  bool isGridStyle = false;
  bool _isRefreshingStatus = false;
  bool _isStatusPollInProgress = false;
  Timer? _statusPollTimer;

  final Map<String, int> _consecutivePingFailures = {};
  final Set<String> _stoppedPollingDeviceIds = {};

  @override
  void initState() {
    super.initState();
    _startStatusPolling();
  }

  @override
  void dispose() {
    _statusPollTimer?.cancel();
    super.dispose();
  }

  void _startStatusPolling() {
    _statusPollTimer?.cancel();
    _statusPollTimer = Timer.periodic(_statusPollInterval, (_) {
      _pollDeviceStatuses();
    });
  }

  void _syncStatusTrackingWithDevices() {
    final deviceIds = devices.map((device) => device.id).toSet();
    _consecutivePingFailures.removeWhere((id, _) => !deviceIds.contains(id));
    _stoppedPollingDeviceIds.removeWhere((id) => !deviceIds.contains(id));
  }

  bool _hasDeviceId(String id) {
    return devices.any((device) => device.id == id);
  }

  Future<bool> _checkDeviceConnectivity(Device device) async {
    final portsToCheck = <int>{...device.ports, 15248}.toList();

    for (final port in portsToCheck) {
      HttpClient? client;
      try {
        final host = device.ipAddress.trim();
        if (host.isEmpty) {
          continue;
        }

        final uri = Uri(
          scheme: 'http',
          host: host,
          port: port,
          path: '/ping',
        );

        client = HttpClient()
          ..connectionTimeout = const Duration(milliseconds: 1200);

        final request = await client.getUrl(uri);

        request.headers.set(HttpHeaders.acceptHeader, 'application/json');
        final response = await request.close().timeout(
              const Duration(milliseconds: 1500),
            );

        final responseBody = await response.transform(utf8.decoder).join();
        final isStatusOk =
            response.statusCode == 200 || response.statusCode == 202;
        final isRepccPayload = responseBody.contains('"message":"Success"') ||
            responseBody.contains('"message": "Success"');

        if (isStatusOk && isRepccPayload) {
          return true;
        }
      } catch (_) {
      } finally {
        client?.close(force: true);
      }
    }

    return false;
  }

  Future<void> _pollDeviceStatuses() async {
    if (_isStatusPollInProgress || devices.isEmpty) return;

    _isStatusPollInProgress = true;
    try {
      final snapshot = List<Device>.from(devices);
      for (final device in snapshot) {
        if (!_hasDeviceId(device.id)) {
          continue;
        }

        if (_stoppedPollingDeviceIds.contains(device.id)) {
          continue;
        }

        final isConnected = await _checkDeviceConnectivity(device);
        if (isConnected) {
          device.isConnected = true;
          _consecutivePingFailures[device.id] = 0;
          _stoppedPollingDeviceIds.remove(device.id);
        } else {
          final failures = (_consecutivePingFailures[device.id] ?? 0) + 1;
          _consecutivePingFailures[device.id] = failures;
          device.isConnected = false;
          if (failures >= 3) {
            _stoppedPollingDeviceIds.add(device.id);
          }
        }
      }

      if (!mounted) return;
      setState(() {});
    } finally {
      _isStatusPollInProgress = false;
    }
  }

  Future<void> _refreshAllDeviceStatuses() async {
    if (_isRefreshingStatus || devices.isEmpty) return;

    setState(() {
      _isRefreshingStatus = true;
    });

    final snapshot = List<Device>.from(devices);
    for (final device in snapshot) {
      if (!_hasDeviceId(device.id)) {
        continue;
      }

      final isConnected = await _checkDeviceConnectivity(device);
      if (isConnected) {
        device.isConnected = true;
        _consecutivePingFailures[device.id] = 0;
        _stoppedPollingDeviceIds.remove(device.id);
      } else {
        final failures = (_consecutivePingFailures[device.id] ?? 0) + 1;
        _consecutivePingFailures[device.id] = failures;
        device.isConnected = false;
        if (failures >= 3) {
          _stoppedPollingDeviceIds.add(device.id);
        }
      }
    }

    if (!mounted) return;
    setState(() {
      _isRefreshingStatus = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    const String appTitle = 'RePCC';
    final colorScheme = Theme.of(context).colorScheme;
    return Scaffold(
      key: _scaffoldKey,
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              decoration: BoxDecoration(
                color: colorScheme.tertiary,
              ),
              child: Stack(
                children: [
                  Align(
                    alignment: Alignment.topRight,
                    child: IconButton(
                      icon: SvgPicture.asset(
                        'assets/Icons/close.svg',
                        colorFilter: ColorFilter.mode(
                            colorScheme.onTertiary, BlendMode.srcIn),
                        width: 24,
                        height: 24,
                      ),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ),
                  Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SvgPicture.asset('assets/repcclogo.svg',
                            width: 64, height: 64),
                        const SizedBox(height: 10),
                        Text(
                          appTitle,
                          style: TextStyle(
                            color: colorScheme.onTertiary,
                            fontSize: 24,
                            fontFamily: 'JetBrainsMono',
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            ListTile(
              leading: SvgPicture.asset('assets/Icons/home.svg',
                  colorFilter:
                      ColorFilter.mode(colorScheme.onSurface, BlendMode.srcIn),
                  width: 24,
                  height: 24),
              title:
                  Text('Home', style: TextStyle(color: colorScheme.onSurface)),
              onTap: () {
                Navigator.pop(context);
              },
            ),
            ListTile(
              leading: SvgPicture.asset('assets/Icons/connect.svg',
                  colorFilter:
                      ColorFilter.mode(colorScheme.onSurface, BlendMode.srcIn),
                  width: 24,
                  height: 24),
              title: Text('Connect',
                  style: TextStyle(color: colorScheme.onSurface)),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(context,
                    MaterialPageRoute(builder: (context) => ConnectScreen()));
              },
            ),
            ListTile(
              leading: SvgPicture.asset('assets/Icons/arrow_forward.svg',
                colorFilter:
                  ColorFilter.mode(colorScheme.onSurface, BlendMode.srcIn),
                width: 24,
                height: 24),
              title: Text('Presenter Tools',
                style: TextStyle(color: colorScheme.onSurface)),
              onTap: () {
              Navigator.pop(context);
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => PresenterScreen(devices: devices)));
              },
            ),
            ListTile(
              leading: SvgPicture.asset('assets/Icons/keyboard.svg',
                  colorFilter:
                      ColorFilter.mode(colorScheme.onSurface, BlendMode.srcIn),
                  width: 24,
                  height: 24),
              title: Text('Macros',
                  style: TextStyle(color: colorScheme.onSurface)),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(context,
                    MaterialPageRoute(builder: (context) => const MacroScreen()));
              },
            ),
          ],
        ),
      ),
      appBar: AppBar(
        leading: IconButton(
          icon: SvgPicture.asset(
            'assets/Icons/menu.svg',
            colorFilter:
                ColorFilter.mode(colorScheme.onTertiary, BlendMode.srcIn),
            width: 24,
            height: 24,
          ),
          tooltip: 'Open navigation menu',
          onPressed: () => _scaffoldKey.currentState?.openDrawer(),
        ),
        title: Center(
            child: Text(
          appTitle,
          style: TextStyle(color: colorScheme.onTertiary, fontSize: 35),
        )),
        actions: <Widget>[
          IconButton(
            icon: _isRefreshingStatus
                ? SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: colorScheme.onTertiary,
                    ),
                  )
                : SvgPicture.asset(
                    'assets/Icons/sync.svg',
                    colorFilter: ColorFilter.mode(
                        colorScheme.onTertiary, BlendMode.srcIn),
                    width: 24,
                    height: 24,
                  ),
            tooltip: 'Refresh Status',
            onPressed: _isRefreshingStatus ? null : _refreshAllDeviceStatuses,
          ),
          IconButton(
            icon: SvgPicture.asset(
              isGridStyle ? 'assets/Icons/list.svg' : 'assets/Icons/grid.svg',
              colorFilter:
                  ColorFilter.mode(colorScheme.onTertiary, BlendMode.srcIn),
              width: 24,
              height: 24,
            ),
            tooltip: isGridStyle ? 'Einfache Liste' : 'Kachelansicht',
            onPressed: () {
              setState(() {
                isGridStyle = !isGridStyle;
              });
            },
          ),
          IconButton(
            icon: SvgPicture.asset('assets/Icons/info.svg',
                colorFilter:
                    ColorFilter.mode(colorScheme.onTertiary, BlendMode.srcIn),
                width: 24,
                height: 24),
            onPressed: () {
              showAboutDialog(
                context: context,
                applicationName: appTitle,
                applicationVersion: 'v0.1.0',
                applicationIcon: SvgPicture.asset('assets/repcclogo.svg',
                    width: 48, height: 48),
                children: [
                  Text(
                      'RePCC is a tool for managing and controlling your devices remotely.'),
                  SizedBox(height: 10),
                  Text('Developed by Nerds'),
                ],
              );
            },
          ),
        ],
      ),
      body: Center(
        child: Container(
          padding: EdgeInsets.all(10),
          child: Column(
            children: [
              Text(
                'Added Devices',
                style: TextStyle(
                    color: colorScheme.onSurface,
                    fontSize: 24,
                    fontFamily: 'JetBrainsMono'),
              ),
              const SizedBox(height: 8),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Container(
                  width: double.infinity,
                  height: 4,
                  decoration: BoxDecoration(
                    color: colorScheme.onSurface.withOpacity(0.24),
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: isGridStyle
                    ? GridView.builder(
                        itemCount: devices.length,
                        gridDelegate:
                            const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 2,
                          crossAxisSpacing: 8,
                          mainAxisSpacing: 8,
                          childAspectRatio: 1,
                        ),
                        itemBuilder: (context, index) {
                          return _buildDeviceGridCard(devices[index], () {
                            setState(() {
                              devices.removeAt(index);
                              _syncStatusTrackingWithDevices();
                            });
                          });
                        },
                      )
                    : ListView.builder(
                        itemCount: devices.length,
                        itemBuilder: (context, index) {
                          return _buildDeviceCard(devices[index], () {
                            setState(() {
                              devices.removeAt(index);
                              _syncStatusTrackingWithDevices();
                            });
                          });
                        },
                      ),
              ),
            ],
          ),
        ),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
      floatingActionButton: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6),
        child: Row(
          children: [
            Expanded(
              child: SizedBox(
                height: 56,
                child: FloatingActionButton.extended(
                  heroTag: 'macrosFab',
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (context) => const MacroScreen()),
                    );
                  },
                  icon: SvgPicture.asset(
                    'assets/Icons/keyboard.svg',
                    colorFilter:
                        const ColorFilter.mode(Colors.black, BlendMode.srcIn),
                    width: 24,
                    height: 24,
                  ),
                  label: const Text('Macros'),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: SizedBox(
                height: 56,
                child: FloatingActionButton.extended(
                  heroTag: 'addDeviceFab',
                  onPressed: () async {
                    final newDevice = await Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => ConnectScreen()),
                    );

                    if (!mounted) return;

                    if (newDevice != null && newDevice is Device) {
                      try {
                        newDevice.isConnected =
                            await _checkDeviceConnectivity(newDevice);
                        _consecutivePingFailures[newDevice.id] =
                            newDevice.isConnected ? 0 : 1;
                        if (newDevice.isConnected) {
                          _stoppedPollingDeviceIds.remove(newDevice.id);
                        } else if (_consecutivePingFailures[newDevice.id]! >= 3) {
                          _stoppedPollingDeviceIds.add(newDevice.id);
                        }
                        if (!mounted) return;
                        setState(() {
                          devices.add(newDevice);
                          _syncStatusTrackingWithDevices();
                        });
                      } catch (error, stackTrace) {
                        if (kDebugMode) {
                          debugPrint('Add device flow failed: $error');
                          debugPrintStack(stackTrace: stackTrace);
                        }
                        if (!mounted) return;
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              kDebugMode
                                  ? 'Failed to add device: ${error.toString()}'
                                  : 'Failed to add device. Please try again.',
                            ),
                          ),
                        );
                      }
                    }
                  },
                  icon: SvgPicture.asset(
                    'assets/Icons/add.svg',
                    colorFilter:
                        const ColorFilter.mode(Colors.black, BlendMode.srcIn),
                    width: 24,
                    height: 24,
                  ),
                  label: const Text('Add Device'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDeviceCard(Device device, VoidCallback onDelete) {
    final colorScheme = Theme.of(context).colorScheme;
    return Card(
      color: device.isConnected ? colorScheme.tertiary : colorScheme.surface,
      child: ListTile(
        leading: SvgPicture.asset(
          'assets/Icons/computer.svg',
          colorFilter: ColorFilter.mode(colorScheme.onSurface, BlendMode.srcIn),
          width: 24,
          height: 24,
        ),
        title: Text(
          device.name.replaceAll(RegExp(r'\.local$'), ''),
          style: TextStyle(
              color: colorScheme.onSurface,
              fontFamily: 'JetBrainsMono',
              fontWeight: FontWeight.normal),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text.rich(
              TextSpan(
                text: 'Status: ',
                style: TextStyle(
                    color: colorScheme.onSurface.withOpacity(0.7),
                    fontSize: 12),
                children: [
                  TextSpan(
                    text: device.isConnected ? 'Online' : 'Offline',
                    style: TextStyle(
                        color: device.isConnected
                            ? colorScheme.primary
                            : colorScheme.onSurface.withOpacity(0.7)),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'IP: ${device.ipAddress}',
              style: TextStyle(
                  color: colorScheme.onSurface.withOpacity(0.6),
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono'),
            ),
            Text(
              'MAC: ${device.macAddress}',
              style: TextStyle(
                  color: colorScheme.onSurface.withOpacity(0.6),
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono'),
            ),
            Text(
              'Ports: ${device.ports.join(", ")}',
              style: TextStyle(
                  color: colorScheme.onSurface.withOpacity(0.6),
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono'),
            ),
          ],
        ),
        trailing: IconButton(
          onPressed: onDelete,
          icon: SvgPicture.asset(
            'assets/Icons/delete.svg',
            colorFilter: ColorFilter.mode(
                colorScheme.onSurface.withOpacity(0.7), BlendMode.srcIn),
            width: 24,
            height: 24,
          ),
        ),
      ),
    );
  }

  Widget _buildDeviceGridCard(Device device, VoidCallback onDelete) {
    final colorScheme = Theme.of(context).colorScheme;
    return Card(
      color: device.isConnected ? colorScheme.tertiary : colorScheme.surface,
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                SvgPicture.asset(
                  'assets/Icons/computer.svg',
                  colorFilter:
                      ColorFilter.mode(colorScheme.onSurface, BlendMode.srcIn),
                  width: 20,
                  height: 20,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    device.name.replaceAll(RegExp(r'\.local$'), ''),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        color: colorScheme.onSurface,
                        fontFamily: 'JetBrainsMono'),
                  ),
                ),
                IconButton(
                  onPressed: onDelete,
                  icon: SvgPicture.asset(
                    'assets/Icons/delete.svg',
                    colorFilter: ColorFilter.mode(
                        colorScheme.onSurface.withOpacity(0.7),
                        BlendMode.srcIn),
                    width: 18,
                    height: 18,
                  ),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              device.isConnected ? 'Online' : 'Offline',
              style: TextStyle(
                color: device.isConnected
                    ? colorScheme.primary
                    : colorScheme.onSurface.withOpacity(0.7),
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'IP: ${device.ipAddress}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                  color: colorScheme.onSurface.withOpacity(0.6),
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono'),
            ),
            Text(
              'MAC: ${device.macAddress}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                  color: colorScheme.onSurface.withOpacity(0.6),
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono'),
            ),
            Text(
              'Ports: ${device.ports.join(", ")}',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                  color: colorScheme.onSurface.withOpacity(0.6),
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono'),
            ),
          ],
        ),
      ),
    );
  }
}
