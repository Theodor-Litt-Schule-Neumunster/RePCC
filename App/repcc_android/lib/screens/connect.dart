import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../models/device.dart';
import 'dart:math';

class ConnectScreen extends StatefulWidget {
  const ConnectScreen({super.key});

  @override
  State<ConnectScreen> createState() => _ConnectScreenState();
}

class _ConnectScreenState extends State<ConnectScreen> {
  final TextEditingController _nameController = TextEditingController();

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  void _addDevice() {
    final String name = _nameController.text.trim();
    if (name.isNotEmpty) {
      // Create a new Device object
      // Generating a simple random ID for now
      final newDevice = Device(
        id: Random().nextInt(10000).toString(),
        name: name,
        isConnected: true, // Assuming new devices are connected initially for demo
      );

      // Return the new device to the previous screen
      Navigator.pop(context, newDevice);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF151515),
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
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
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
                FloatingActionButton.extended(
                  heroTag: 'add',
                  onPressed: _addDevice,
                  label: const Text('Connect', style: TextStyle(fontFamily: 'JetBrainsMono')),
                  icon: const Icon(Icons.check),
                ),
              ],
            )
          ],
        ),
      ),
    );
  }
}