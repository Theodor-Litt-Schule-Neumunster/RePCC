import 'package:flutter/material.dart';
import '../models/macro.dart';
import '../models/macro_store.dart';

class MacroScreen extends StatefulWidget {
  const MacroScreen({super.key});

  @override
  State<MacroScreen> createState() => _MacroScreenState();
}

class _MacroScreenState extends State<MacroScreen> {
  final MacroStore _store = MacroStore();

  bool _loading = true;
  List<Macro> _macros = const [];

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    setState(() => _loading = true);
    final macros = await _store.load();
    if (!mounted) return;
    setState(() {
      _macros = macros;
      _loading = false;
    });
  }

  Future<void> _upsertMacro({Macro? existing}) async {
    final nameController = TextEditingController(text: existing?.name ?? '');
    final bodyController = TextEditingController(text: existing?.body ?? '');

    final saved = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(existing == null ? 'Add Macro' : 'Edit Macro'),
          content: SizedBox(
            width: 520,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameController,
                  decoration: const InputDecoration(
                    labelText: 'Name',
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: bodyController,
                  minLines: 6,
                  maxLines: 10,
                  decoration: const InputDecoration(
                    labelText: 'Macro JSON / Body',
                    hintText: 'Paste your .pcmac JSON here (or any text for now)',
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                final name = nameController.text.trim();
                if (name.isEmpty) return;
                Navigator.pop(context, true);
              },
              child: const Text('Save'),
            ),
          ],
        );
      },
    );

    if (saved != true) return;

    final nowMs = DateTime.now().millisecondsSinceEpoch;
    final name = nameController.text.trim();
    final body = bodyController.text;

    final next = [..._macros];
    if (existing == null) {
      next.insert(
        0,
        Macro(
          id: DateTime.now().microsecondsSinceEpoch.toString(),
          name: name,
          body: body,
          updatedAtMs: nowMs,
        ),
      );
    } else {
      final idx = next.indexWhere((m) => m.id == existing.id);
      final updated = existing.copyWith(
        name: name,
        body: body,
        updatedAtMs: nowMs,
      );
      if (idx >= 0) {
        next[idx] = updated;
      } else {
        next.insert(0, updated);
      }
    }

    await _store.save(next);
    if (!mounted) return;
    setState(() => _macros = next);
  }

  Future<void> _deleteMacro(Macro macro) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Macro?'),
        content: Text('Delete "${macro.name}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (ok != true) return;

    final next = _macros.where((m) => m.id != macro.id).toList();
    await _store.save(next);

    if (!mounted) return;
    setState(() => _macros = next);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF353535),
      appBar: AppBar(
        backgroundColor: const Color(0xFF121212),
        title: const Text('Macros', style: TextStyle(color: Colors.white)),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _upsertMacro(),
        icon: const Icon(Icons.add, color: Colors.black),
        label: const Text('Add Macro'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _macros.isEmpty
              ? const Center(
                  child: Text(
                    'No macros yet.\nTap “Add Macro” to create one.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.white70),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(10),
                  itemCount: _macros.length,
                  itemBuilder: (context, index) {
                    final macro = _macros[index];
                    return Card(
                      color: const Color(0xFF202020),
                      child: ListTile(
                        title: Text(
                          macro.name,
                          style: const TextStyle(
                            color: Colors.white,
                            fontFamily: 'JetBrainsMono',
                          ),
                        ),
                        subtitle: Text(
                          macro.body.trim().isEmpty
                              ? '(empty body)'
                              : macro.body.trim().split('\n').first,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: Colors.white60),
                        ),
                        onTap: () => _upsertMacro(existing: macro),
                        trailing: IconButton(
                          onPressed: () => _deleteMacro(macro),
                          icon: const Icon(Icons.delete_outline,
                              color: Colors.white70),
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}