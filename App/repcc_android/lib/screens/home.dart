import 'package:flutter/material.dart';
import 'connect.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const String appTitle = 'RePCC';
    return Scaffold(
      backgroundColor: Color(0xFF151515),
      appBar: AppBar(
        backgroundColor: Color(0xFF121212),
        title: Center(child: Text(appTitle, style: TextStyle(color: Colors.white, fontSize: 35),)),
      ),
      body: Center(
        child: Container(
          color: Color(0xFF353535),
          padding: EdgeInsets.all(10),
          child: Column(
            children: [
              Text(
                'Added Devices',
                style: TextStyle(color: Colors.white, fontSize: 24),
              ),
              Card(
                color: Color(0xFF252525),
                child: ListTile(
                  leading: Icon(Icons.devices, color: Colors.white),
                  title: Text(
                    'Device 1',
                    style: TextStyle(color: Colors.white),
                  ),
                  subtitle: Text(
                    'Status: Connected',
                    style: TextStyle(color: Colors.white70),
                  ),

                ),
              ),
              Card(
                color: Color(0xFF252525),
                child: ListTile(
                  leading: Icon(Icons.devices, color: Colors.white),
                  title: Text(
                    'Device 2',
                    style: TextStyle(color: Colors.white),
                  ),
                  subtitle: Text(
                    'Status: Disconnected',
                    style: TextStyle(color: Colors.white70),
                  ),
                ),
          )],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          Navigator.push(context, MaterialPageRoute(builder: (context) =>  ConnectScreen()));
        }, 
        label: Text('Add Device')
      ),
    );
  }
}