class Device {
  final String id;
  final String name;
  final String ipAddress;
  final String macAddress;
  final List<int> ports;
  bool isConnected;

  Device({
    required this.id, 
    required this.name,
    required this.ipAddress,
    required this.macAddress,
    required this.ports,
    this.isConnected = false
  });
}
