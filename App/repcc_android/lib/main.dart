import 'package:flutter/material.dart';
import 'package:repcc_android/screens/home.dart';

void main() {
  runApp(const MainApp());
}

class MainApp extends StatelessWidget {
  const MainApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false, // Disables the debug banner
      home: HomeScreen(),
    );
  }
}
