import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../models/device.dart';
import 'connect.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  // List of devices managed by the state - now starts empty
  List<Device> devices = [];

  @override
  Widget build(BuildContext context) {
    const String appTitle = 'RePCC';
    return Scaffold(
      appBar: AppBar(
        title: Center(child: Text(appTitle, style: TextStyle(color: Colors.white, fontSize: 35),)),
        actions: <Widget>[
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
                applicationIcon: SvgPicture.asset('assets/repcclogo.svg', width: 48, height: 48),
                children: [
                  Text('RePCC is a tool for managing and controlling your devices remotely.'),
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
                style: TextStyle(color: Colors.white, fontSize: 24, fontFamily: 'JetBrainsMono'),
              ),
              Expanded(
                child: ListView.builder(
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
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          // Wait for the result from the ConnectScreen
          final newDevice = await Navigator.push(
            context, 
            MaterialPageRoute(builder: (context) =>  ConnectScreen())
          );

          // If a device was returned (not null), add it to the list
          if (newDevice != null && newDevice is Device) {
            setState(() {
              devices.add(newDevice);
            });
          }
        },
        icon: SvgPicture.asset('assets/Icons/add.svg',
            colorFilter: ColorFilter.mode(Colors.black, BlendMode.srcIn),
            width: 24,
            height: 24),
        label: Text('Add Device')
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
          style: TextStyle(color: Colors.white, fontFamily: 'JetBrainsMono', fontWeight: FontWeight.normal),
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
                    style: TextStyle(color: device.isConnected ? Colors.green : Colors.white70),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'IP: ${device.ipAddress}',
              style: TextStyle(color: Colors.white60, fontSize: 11, fontFamily: 'JetBrainsMono'),
            ),
            Text(
              'MAC: ${device.macAddress}',
              style: TextStyle(color: Colors.white60, fontSize: 11, fontFamily: 'JetBrainsMono'),
            ),
            Text(
              'Ports: ${device.ports.join(", ")}',
              style: TextStyle(color: Colors.white60, fontSize: 11, fontFamily: 'JetBrainsMono'),
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
}