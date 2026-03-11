import 'package:flutter/material.dart';
import 'package:repcc_android/screens/home.dart';
import 'dart:ui';
import 'dart:async';
import 'package:flutter/foundation.dart';

/* Primary color scheme for the app */

final ColorScheme repccMain = ColorScheme (
  brightness: Brightness.dark,
  primary: Color(0xFFd9d9d9), 
  onPrimary: Colors.black,
  secondary: Color(0xFF9a9a9a), 
  onSecondary: Colors.white,
  tertiary: Color(0xFF404040),  
  onTertiary: Colors.white,
  error: Color(0xFFc07a7a),
  onError: Colors.black87,
  surface: Color(0xFF353535),
  onSurface: Colors.white,
);

void main() {
  if (kDebugMode) {
    FlutterError.onError = (FlutterErrorDetails details) {
      FlutterError.presentError(details);
      debugPrint('FlutterError: ${details.exceptionAsString()}');
      debugPrintStack(stackTrace: details.stack);
    };

    PlatformDispatcher.instance.onError = (error, stack) {
      debugPrint('PlatformDispatcher error: $error');
      debugPrintStack(stackTrace: stack);
      return true;
    };

    runZonedGuarded(
      () => runApp(const MainApp()),
      (error, stack) {
        debugPrint('runZonedGuarded error: $error');
        debugPrintStack(stackTrace: stack);
      },
    );
    return;
  }

  runApp(const MainApp());
}

class MainApp extends StatelessWidget {
  const MainApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: repccMain,
        fontFamily: 'JetBrainsMono',
        scaffoldBackgroundColor: repccMain.surface,
        appBarTheme: AppBarTheme(
          backgroundColor: repccMain.tertiary,
          foregroundColor: repccMain.onTertiary,
        ),
        cardTheme: CardThemeData(
          color: repccMain.tertiary,
        ),
        floatingActionButtonTheme: FloatingActionButtonThemeData(
          backgroundColor: repccMain.primary,
          foregroundColor: repccMain.onPrimary,
        ),
      ),
      debugShowCheckedModeBanner: false, // Disables the debug banner
      home: const HomeScreen(),
    );
  }
}
