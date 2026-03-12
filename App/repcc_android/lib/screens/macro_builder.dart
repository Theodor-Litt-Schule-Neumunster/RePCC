import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_blockly/flutter_blockly.dart' hide Theme;

import '../models/macro.dart';

class MacroBuilderResult {
  final String name;
  final String workspaceJson;
  final String compiledMacroJson;

  const MacroBuilderResult({
    required this.name,
    required this.workspaceJson,
    required this.compiledMacroJson,
  });
}

class MacroBuilderScreen extends StatefulWidget {
  final Macro? existing;

  const MacroBuilderScreen({super.key, this.existing});

  @override
  State<MacroBuilderScreen> createState() => _MacroBuilderScreenState();
}

class _MacroBuilderScreenState extends State<MacroBuilderScreen> {
  late final TextEditingController _nameController;

  Map<String, dynamic>? _workspaceJson;
  String _compiledJson = '';
  List<String> _warnings = const [];

  final BlocklyOptions _workspaceConfiguration = BlocklyOptions.fromJson(const {
    'grid': {
      'spacing': 20,
      'length': 3,
      'colour': '#D6D6D6',
      'snap': true,
    },
    'toolbox': {
      'kind': 'categoryToolbox',
      'contents': [
        {
          'kind': 'category',
          'name': 'Macro Commands',
          'colour': 210,
          'contents': [
            {
              'kind': 'block',
              'blockxml':
                  '<block type="text_print"><value name="TEXT"><shadow type="text"><field name="TEXT">key:a</field></shadow></value></block>',
            },
            {
              'kind': 'block',
              'blockxml':
                  '<block type="text_print"><value name="TEXT"><shadow type="text"><field name="TEXT">keys:ctrl+shift+p</field></shadow></value></block>',
            },
            {
              'kind': 'block',
              'blockxml':
                  '<block type="text_print"><value name="TEXT"><shadow type="text"><field name="TEXT">click:left</field></shadow></value></block>',
            },
            {
              'kind': 'block',
              'blockxml':
                  '<block type="text_print"><value name="TEXT"><shadow type="text"><field name="TEXT">move:0.50,0.50</field></shadow></value></block>',
            },
            {
              'kind': 'block',
              'type': 'controls_repeat_ext',
            },
            {
              'kind': 'block',
              'type': 'math_number',
            },
            {
              'kind': 'block',
              'type': 'text',
            },
          ],
        },
      ],
    },
  });

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.existing?.name ?? '');
    _initFromExisting();
  }

  void _initFromExisting() {
    final existing = widget.existing;
    if (existing == null) return;

    if (existing.workspace.trim().isNotEmpty) {
      try {
        final decoded = jsonDecode(existing.workspace);
        if (decoded is Map<String, dynamic>) {
          _workspaceJson = decoded;
        }
      } catch (_) {
        // Keep editor empty if stored workspace is invalid.
      }
    }

    if (existing.body.trim().isNotEmpty) {
      _compiledJson = existing.body;
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  void _onBlocklyChange(BlocklyData data) {
    final result = compileWorkspaceToMacro(data.json ?? const {});
    setState(() {
      _workspaceJson = data.json;
      _warnings = result.warnings;
      _compiledJson = const JsonEncoder.withIndent('  ').convert(result.macro);
    });
  }

  Future<void> _saveAndClose() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a macro name.')),
      );
      return;
    }

    if (_compiledJson.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content:
                Text('Add at least one valid command block before saving.')),
      );
      return;
    }

    final workspaceJson = _workspaceJson == null
        ? ''
        : const JsonEncoder.withIndent('  ').convert(_workspaceJson);

    if (!mounted) return;
    Navigator.of(context).pop(
      MacroBuilderResult(
        name: name,
        workspaceJson: workspaceJson,
        compiledMacroJson: _compiledJson,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Macro Builder'),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Center(
              child: SizedBox(
                width: 240,
                child: TextField(
                  controller: _nameController,
                  decoration: const InputDecoration(
                    labelText: 'Macro name',
                    isDense: true,
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: FilledButton.icon(
              onPressed: _saveAndClose,
              icon: const Icon(Icons.save_outlined),
              label: const Text('Save'),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            flex: 7,
            child: BlocklyEditorWidget(
              workspaceConfiguration: _workspaceConfiguration,
              initial: _workspaceJson,
              onChange: _onBlocklyChange,
              onError: (err) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Blockly error: $err')),
                );
              },
            ),
          ),
          Expanded(
            flex: 4,
            child: Container(
              width: double.infinity,
              color:
                  theme.colorScheme.surfaceContainerHighest.withOpacity(0.35),
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Command format in text_print block:',
                    style: TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                      'key:a | keys:ctrl+shift+p | click:left | move:0.4,0.6'),
                  if (_warnings.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    Text(
                      _warnings.join('\n'),
                      style: TextStyle(
                        color: theme.colorScheme.error,
                        fontSize: 12,
                      ),
                    ),
                  ],
                  const SizedBox(height: 10),
                  const Text(
                    'Compiled .pcmac JSON',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  Expanded(
                    child: SingleChildScrollView(
                      child: SelectableText(
                        _compiledJson.isEmpty ? '{}' : _compiledJson,
                        style: const TextStyle(fontFamily: 'JetBrainsMono'),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CompileResult {
  final Map<String, dynamic> macro;
  final List<String> warnings;

  const _CompileResult({required this.macro, required this.warnings});
}

_CompileResult compileWorkspaceToMacro(Map<String, dynamic> workspaceJson) {
  final actions = <Map<String, dynamic>>[];
  final warnings = <String>[];

  Map<String, dynamic>? asMap(dynamic value) {
    if (value is Map<String, dynamic>) return value;
    if (value is Map) return Map<String, dynamic>.from(value);
    return null;
  }

  List<Map<String, dynamic>> asMapList(dynamic value) {
    if (value is! List) return const [];
    return value
        .map(asMap)
        .whereType<Map<String, dynamic>>()
        .toList(growable: false);
  }

  Map<String, dynamic>? inputBlock(
      Map<String, dynamic> block, String inputName) {
    final inputs = asMap(block['inputs']);
    final input = asMap(inputs?[inputName]);
    return asMap(input?['block']);
  }

  Map<String, dynamic>? statementBlock(
      Map<String, dynamic> block, String statementName) {
    final inputs = asMap(block['inputs']);
    final input = asMap(inputs?[statementName]);
    return asMap(input?['block']);
  }

  Map<String, dynamic>? nextBlock(Map<String, dynamic> block) {
    final next = asMap(block['next']);
    return asMap(next?['block']);
  }

  String? textFromBlock(Map<String, dynamic> block) {
    final fields = asMap(block['fields']);
    final textField = fields?['TEXT'];
    if (textField is String && textField.trim().isNotEmpty) {
      return textField.trim();
    }
    return null;
  }

  int? numberFromBlock(Map<String, dynamic> block) {
    final fields = asMap(block['fields']);
    final n = fields?['NUM'];
    if (n is num) return n.round();
    if (n is String) return int.tryParse(n.trim());
    return null;
  }

  Map<String, dynamic>? parseCommandText(String commandText) {
    final cmd = commandText.trim();
    if (cmd.isEmpty) return null;

    if (cmd.startsWith('key:')) {
      final key = cmd.substring(4).trim();
      if (key.isEmpty) return null;
      return {
        'type': 'keyboard',
        'actiontype': 'singlekey',
        'actiondata': [key],
        'sleep': 100,
        'presssleep': 10,
      };
    }

    if (cmd.startsWith('keys:')) {
      final keys = cmd
          .substring(5)
          .split('+')
          .map((k) => k.trim())
          .where((k) => k.isNotEmpty)
          .toList(growable: false);
      if (keys.length < 2) return null;
      return {
        'type': 'keyboard',
        'actiontype': 'multikey',
        'actiondata': keys,
        'sleep': 100,
        'presssleep': 10,
      };
    }

    if (cmd.startsWith('click:')) {
      final target = cmd.substring(6).trim().toLowerCase();
      if (target == 'left') {
        return {
          'type': 'mouse',
          'actiontype': 'click',
          'actiondata': [0],
          'sleep': 100,
          'presssleep': 10,
        };
      }
      if (target == 'right') {
        return {
          'type': 'mouse',
          'actiontype': 'click',
          'actiondata': [1],
          'sleep': 100,
          'presssleep': 10,
        };
      }
      return null;
    }

    if (cmd.startsWith('move:')) {
      final raw = cmd.substring(5).trim();
      final parts = raw.split(',').map((p) => p.trim()).toList(growable: false);
      if (parts.length != 2) return null;
      final x = double.tryParse(parts[0]);
      final y = double.tryParse(parts[1]);
      if (x == null || y == null) return null;

      return {
        'type': 'mouse',
        'actiontype': 'move',
        'actiondata': [x, y],
        'sleep': 100,
        'transition': 'linear',
        'transitiontime': 500,
      };
    }

    return null;
  }

  void compileChain(Map<String, dynamic>? first) {
    var cursor = first;
    while (cursor != null) {
      final type = (cursor['type'] ?? '').toString();

      if (type == 'controls_repeat_ext') {
        final timesBlock = inputBlock(cursor, 'TIMES');
        final times =
            (timesBlock == null ? null : numberFromBlock(timesBlock)) ?? 1;
        final loopBody = statementBlock(cursor, 'DO');
        if (loopBody == null) {
          warnings.add('Repeat block has no DO statement body.');
        } else {
          for (var i = 0; i < times; i++) {
            compileChain(loopBody);
          }
        }
        cursor = nextBlock(cursor);
        continue;
      }

      if (type == 'text_print') {
        final textBlock = inputBlock(cursor, 'TEXT');
        final command = textBlock == null ? null : textFromBlock(textBlock);
        if (command == null) {
          warnings.add('text_print block is missing command text.');
        } else {
          final action = parseCommandText(command);
          if (action == null) {
            warnings.add('Unsupported command "$command".');
          } else {
            actions.add(action);
          }
        }
        cursor = nextBlock(cursor);
        continue;
      }

      warnings.add('Block type "$type" is ignored by compiler.');
      cursor = nextBlock(cursor);
    }
  }

  final rootBlocks = asMapList(asMap(workspaceJson['blocks'])?['blocks']);
  for (final root in rootBlocks) {
    compileChain(root);
  }

  final macro = <String, dynamic>{
    r'$data': {
      'isLoop': false,
      'amtLoops': 1,
    },
  };

  for (var i = 0; i < actions.length; i++) {
    macro['${i + 1}'] = actions[i];
  }

  return _CompileResult(macro: macro, warnings: warnings);
}
