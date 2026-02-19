import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../models/device.dart';
import 'connect.dart';
import 'macros.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  // List of devices managed by the state - now starts empty
  List<Device> devices = [];
  bool isGridStyle = false;

  @override
  Widget build(BuildContext context) {
    const String appTitle = 'RePCC';
    return Scaffold(
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              decoration: BoxDecoration(
                color: Color(0xFF202020),
              ),
              child: Stack(
                children: [
                  Align(
                    alignment: Alignment.topRight,
                    child: IconButton(
                      icon: const Icon(Icons.close, color: Colors.white),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ),
                  Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SvgPicture.asset('assets/repcclogo.svg', width: 64, height: 64),
                        const SizedBox(height: 10),
                        Text(
                          appTitle,
                          style: const TextStyle(
                            color: Colors.white,
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
                  colorFilter: ColorFilter.mode(Colors.white, BlendMode.srcIn),
                  width: 24,
                  height: 24),
              title: Text('Home', style: TextStyle(color: Colors.white)),
              onTap: () {
                Navigator.pop(context);
              },
            ),
            ListTile(
              leading: SvgPicture.asset('assets/Icons/connect.svg',
                  colorFilter: ColorFilter.mode(Colors.white, BlendMode.srcIn),
                  width: 24,
                  height: 24),
              title: Text('Connect', style: TextStyle(color: Colors.white)),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(context,
                    MaterialPageRoute(builder: (context) => ConnectScreen()));
              },
            ),
          ],
        ),
      ),
      appBar: AppBar(
        title: Center(
            child: Text(
          appTitle,
          style: TextStyle(color: Colors.white, fontSize: 35),
        )),
        actions: <Widget>[
          IconButton(
            icon: Icon(
              isGridStyle ? Icons.view_agenda : Icons.grid_view,
              color: Colors.white,
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
                colorFilter: ColorFilter.mode(Colors.white, BlendMode.srcIn),
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
                    color: Colors.white,
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
                    color: Colors.white24,
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
                      MaterialPageRoute(builder: (context) => const MacroScreen()),
                    );
                  },
                  icon: const Icon(Icons.keyboard, color: Colors.black),
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

                    if (newDevice != null && newDevice is Device) {
                      setState(() {
                        devices.add(newDevice);
                      });
                    }
                  },
                  icon: SvgPicture.asset(
                    'assets/Icons/add.svg',
                    colorFilter: const ColorFilter.mode(Colors.black, BlendMode.srcIn),
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
    return Card(
      color: device.isConnected ? Color(0xFF404040) : Color(0xFF202020),
      child: ListTile(
        leading: SvgPicture.asset(
          'assets/Icons/computer.svg',
          colorFilter: ColorFilter.mode(Colors.white, BlendMode.srcIn),
          width: 24,
          height: 24,
        ),
        title: Text(
          device.name,
          style: TextStyle(
              color: Colors.white,
              fontFamily: 'JetBrainsMono',
              fontWeight: FontWeight.normal),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text.rich(
              TextSpan(
                text: 'Status: ',
                style: TextStyle(color: Colors.white70, fontSize: 12),
                children: [
                  TextSpan(
                    text: device.isConnected ? 'Connected' : 'Disconnected',
                    style: TextStyle(
                        color:
                            device.isConnected ? Colors.green : Colors.white70),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'IP: ${device.ipAddress}',
              style: TextStyle(
                  color: Colors.white60,
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono'),
            ),
            Text(
              'MAC: ${device.macAddress}',
              style: TextStyle(
                  color: Colors.white60,
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono'),
            ),
            Text(
              'Ports: ${device.ports.join(", ")}',
              style: TextStyle(
                  color: Colors.white60,
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono'),
            ),
          ],
        ),
        trailing: IconButton(
          onPressed: onDelete,
          icon: SvgPicture.asset(
            'assets/Icons/delete.svg',
            colorFilter: ColorFilter.mode(Colors.white70, BlendMode.srcIn),
            width: 24,
            height: 24,
          ),
        ),
      ),
    );
  }

  Widget _buildDeviceGridCard(Device device, VoidCallback onDelete) {
    return Card(
      color: device.isConnected ? Color(0xFF404040) : Color(0xFF202020),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                SvgPicture.asset(
                  'assets/Icons/computer.svg',
                  colorFilter: ColorFilter.mode(Colors.white, BlendMode.srcIn),
                  width: 20,
                  height: 20,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    device.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        color: Colors.white, fontFamily: 'JetBrainsMono'),
                  ),
                ),
                IconButton(
                  onPressed: onDelete,
                  icon: SvgPicture.asset(
                    'assets/Icons/delete.svg',
                    colorFilter:
                        ColorFilter.mode(Colors.white70, BlendMode.srcIn),
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
              device.isConnected ? 'Connected' : 'Disconnected',
              style: TextStyle(
                color: device.isConnected ? Colors.green : Colors.white70,
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'IP: ${device.ipAddress}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                  color: Colors.white60,
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono'),
            ),
            Text(
              'MAC: ${device.macAddress}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                  color: Colors.white60,
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono'),
            ),
            Text(
              'Ports: ${device.ports.join(", ")}',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                  color: Colors.white60,
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono'),
            ),
          ],
        ),
      ),
    );
  }
}
