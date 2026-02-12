import 'dart:convert';

class Macro {
  final String id;
  final String name;

  /// Stored as text so you can paste valid `.pcmac` JSON (or any payload for now).
  final String body;

  final int updatedAtMs;

  const Macro({
    required this.id,
    required this.name,
    required this.body,
    required this.updatedAtMs,
  });

  Macro copyWith({
    String? id,
    String? name,
    String? body,
    int? updatedAtMs,
  }) {
    return Macro(
      id: id ?? this.id,
      name: name ?? this.name,
      body: body ?? this.body,
      updatedAtMs: updatedAtMs ?? this.updatedAtMs,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'body': body,
        'updatedAtMs': updatedAtMs,
      };

  factory Macro.fromJson(Map<String, dynamic> json) {
    return Macro(
      id: (json['id'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      body: (json['body'] ?? '').toString(),
      updatedAtMs: (json['updatedAtMs'] is int)
          ? (json['updatedAtMs'] as int)
          : int.tryParse((json['updatedAtMs'] ?? '0').toString()) ?? 0,
    );
  }

  static String encodeList(List<Macro> macros) =>
      jsonEncode(macros.map((m) => m.toJson()).toList());

  static List<Macro> decodeList(String raw) {
    final decoded = jsonDecode(raw);
    if (decoded is! List) return [];
    return decoded
        .whereType<Map>()
        .map((m) => Macro.fromJson(Map<String, dynamic>.from(m)))
        .toList();
  }
}