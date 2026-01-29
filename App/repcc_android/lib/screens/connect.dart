import 'package:flutter/material.dart';

class ConnectScreen extends StatelessWidget {
  const ConnectScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        width: double.infinity,
        height: double.infinity,
        color: const Color(0xFF151515),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(
              'Connect a new Device',
              style: TextStyle(color: Colors.white, fontSize: 20, fontFamily: 'JetBrainsMono', fontWeight: FontWeight.normal),
            ),
            FloatingActionButton(onPressed:   () {
              Navigator.pop(context);
            }, child: Icon(Icons.arrow_back))
          ],
        ),
      ),
    );
  }
}