import 'package:flutter/material.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const String appTitle = 'RePCC';
    return Scaffold(
      backgroundColor: Color(0xFF151515),
      appBar: AppBar(
        backgroundColor: Color(0xFF121212),
        title: Center(child: Text(appTitle, style: TextStyle(fontFamily: 'JetBrainsMono', color: Colors.white),)),
      ),
      body: Center(
        child: Container(
          color: Color(0xFF353535),
          ),
      ),

    );
  }
}