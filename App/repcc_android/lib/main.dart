import 'package:flutter/material.dart';
import 'package:repcc_android/screens/home.dart';

/* Primary color scheme for the app */

final ColorScheme repccMain = ColorScheme (
  brightness: Brightness.dark,
  primary: Color(0xFF353535), // ------------- What else to use? background/surface is a thing...
  onPrimary: Colors.white,
  secondary: Color(0xFF202020), // ----------- Same Problem
  onSecondary: Colors.white,
  tertiary: Color(0xFF404040),  // ------------ Same Problem
  onTertiary: Colors.white,
  error: Color(0xFFc07a7a),
  onError: Colors.black87,
  // background: Color(0xFF353535),
  // onBackground: Colors.white,
  surface: Color(0xFF353535),
  onSurface: Colors.white,
);


void main() {
  runApp(const MainApp());
}

class MainApp extends StatelessWidget {
  const MainApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: ThemeData(
        fontFamily: 'JetBrainsMono',
      ),
      debugShowCheckedModeBanner: false, // Disables the debug banner
      home: const HomeScreen(),
    );
  }
}
