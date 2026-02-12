import 'package:shared_preferences/shared_preferences.dart';
import 'macro.dart';

class MacroStore {
  static const String _key = 'repcc_macros_v1';

  Future<List<Macro>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.trim().isEmpty) return [];
    try {
      return Macro.decodeList(raw);
    } catch (_) {
      return [];
    }
  }

  Future<void> save(List<Macro> macros) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, Macro.encodeList(macros));
  }
}