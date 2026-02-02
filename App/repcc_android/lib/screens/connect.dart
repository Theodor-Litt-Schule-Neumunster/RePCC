import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

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
            }, child: SvgPicture.asset(
                    'assets/Icons/arrow_back.svg',
                    width: 24,
                    height: 24,
                    colorFilter: ColorFilter.mode(Colors.black, BlendMode.srcIn), // Adjust color as needed, often FAB icons are black or white
              ))
          ],
        ),
      ),
    );
  }
}