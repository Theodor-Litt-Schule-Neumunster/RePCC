class Device {
  final String id;
  final String name;
  bool isConnected;

  Device({
    required this.id, 
    required this.name, 
    this.isConnected = false
  });
}
