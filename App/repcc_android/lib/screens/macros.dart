import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../models/macro.dart';
import '../models/macro_store.dart';
import 'macro_builder.dart';

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
                    hintText:
                        'Paste your .pcmac JSON here (or any text for now)',
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
          workspace: '',
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

  Future<void> _openMacroBuilder({Macro? existing}) async {
    final result = await Navigator.of(context).push<MacroBuilderResult>(
      MaterialPageRoute(
        builder: (_) => MacroBuilderScreen(existing: existing),
      ),
    );

    if (result == null) return;

    final nowMs = DateTime.now().millisecondsSinceEpoch;
    final next = [..._macros];
    if (existing == null) {
      next.insert(
        0,
        Macro(
          id: DateTime.now().microsecondsSinceEpoch.toString(),
          name: result.name,
          body: result.compiledMacroJson,
          workspace: result.workspaceJson,
          updatedAtMs: nowMs,
        ),
      );
    } else {
      final idx = next.indexWhere((m) => m.id == existing.id);
      final updated = existing.copyWith(
        name: result.name,
        body: result.compiledMacroJson,
        workspace: result.workspaceJson,
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
    final colorScheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: () => Navigator.pop(context),
          icon: SvgPicture.asset(
            'assets/Icons/home.svg',
            colorFilter:
                ColorFilter.mode(colorScheme.onTertiary, BlendMode.srcIn),
            width: 24,
            height: 24,
          ),
        ),
        title: const Text('Macros'),
        actions: [
          IconButton(
            tooltip: 'Open Blockly Macro Builder',
            onPressed: () => _openMacroBuilder(),
            icon: SvgPicture.asset(
              'assets/Icons/grid.svg',
              colorFilter:
                  ColorFilter.mode(colorScheme.onTertiary, BlendMode.srcIn),
              width: 22,
              height: 22,
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _upsertMacro(),
        icon: SvgPicture.asset(
          'assets/Icons/add.svg',
          colorFilter: ColorFilter.mode(colorScheme.onPrimary, BlendMode.srcIn),
          width: 24,
          height: 24,
        ),
        label: const Text('Add Macro'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _macros.isEmpty
              ? Center(
                  child: Text(
                    'No macros yet.\nTap “Add Macro” to create one.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                        color: colorScheme.onSurface.withOpacity(0.7)),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(10),
                  itemCount: _macros.length,
                  itemBuilder: (context, index) {
                    final macro = _macros[index];
                    return Card(
                      color: colorScheme.tertiary,
                      child: ListTile(
                        title: Text(
                          macro.name,
                          style: TextStyle(
                            color: colorScheme.onTertiary,
                            fontFamily: 'JetBrainsMono',
                          ),
                        ),
                        subtitle: Text(
                          macro.body.trim().isEmpty
                              ? '(empty body)'
                              : macro.body.trim().split('\n').first,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                              color: colorScheme.onTertiary.withOpacity(0.6)),
                        ),
                        onTap: () => _upsertMacro(existing: macro),
                        trailing: SizedBox(
                          width: 96,
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              IconButton(
                                tooltip: 'Edit in Blockly Builder',
                                onPressed: () =>
                                    _openMacroBuilder(existing: macro),
                                icon: SvgPicture.asset(
                                  'assets/Icons/grid.svg',
                                  colorFilter: ColorFilter.mode(
                                      colorScheme.onTertiary.withOpacity(0.75),
                                      BlendMode.srcIn),
                                  width: 22,
                                  height: 22,
                                ),
                              ),
                              IconButton(
                                onPressed: () => _deleteMacro(macro),
                                icon: SvgPicture.asset(
                                  'assets/Icons/delete.svg',
                                  colorFilter: ColorFilter.mode(
                                      colorScheme.onTertiary.withOpacity(0.7),
                                      BlendMode.srcIn),
                                  width: 22,
                                  height: 22,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
