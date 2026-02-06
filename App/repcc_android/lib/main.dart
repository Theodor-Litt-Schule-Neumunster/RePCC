import 'package:flutter/material.dart';
import 'package:repcc_android/screens/home.dart';

/* Primary color scheme for the app */

final ColorScheme repccMain = ColorScheme (
  brightness: Brightness.dark,
  primary: Color(0xFF353535), 
  onPrimary: Colors.white,
  secondary: Color(0xFF202020), 
  onSecondary: Colors.white,
  tertiary: Color(0xFF404040),  
  onTertiary: Colors.white,
  error: Color(0xFFc07a7a),
  onError: Colors.black87,
  background: Color(0xFF353535), // Background is a deprecated property in favor of surface, but we can still set it for compatibility
  onBackground: Colors.white,
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
        colorScheme: repccMain,
        fontFamily: 'JetBrainsMono',
        useMaterial3: true,
      ),
      debugShowCheckedModeBanner: false, // Disables the debug banner
      home: const HomeScreen(),
    );
  }
}
