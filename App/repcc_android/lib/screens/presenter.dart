import 'dart:convert';
import 'dart:io';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';

import '../models/device.dart';

class PresenterScreen extends StatefulWidget {
  final List<Device> devices;

  const PresenterScreen({super.key, required this.devices});

  @override
  State<PresenterScreen> createState() => _PresenterScreenState();
}

class _PresenterScreenState extends State<PresenterScreen> {
  Device? _selectedDevice;
  bool _isSending = false;
  bool _isMirrorReady = false;
  int _lastLaserUpdateMs = 0;
  bool _laserUpdateInFlight = false;
  int _laserRefreshRate = 30;
  DateTime? _lastLaserErrorToastAt;
  String? _lastLaserConnectError;

  RTCPeerConnection? _peerConnection;
  RTCDataChannel? _laserDataChannel;
  bool _laserChannelOpen = false;
  Future<bool>? _laserConnectFuture;
  final RTCVideoRenderer _remoteRenderer = RTCVideoRenderer();

  @override
  void initState() {
    super.initState();
    _remoteRenderer.initialize();
    if (widget.devices.isNotEmpty) {
      _selectedDevice = widget.devices.first;
    }
  }

  @override
  void dispose() {
    _closeLaserChannel(updateUi: false);
    _remoteRenderer.dispose();
    super.dispose();
  }

  Future<void> _disconnectWebRtc({bool showFeedback = true}) async {
    await _closeLaserChannel(updateUi: true);
    if (!mounted || !showFeedback) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('WebRTC connection closed.')),
    );
  }

  void _leavePresenterScreen() {
    if (!mounted) return;
    Navigator.of(context).maybePop();
  }

  Future<void> _closeLaserChannel({bool updateUi = true}) async {
    final channel = _laserDataChannel;
    final connection = _peerConnection;

    _laserDataChannel = null;
    _peerConnection = null;
    _laserChannelOpen = false;
    _laserConnectFuture = null;
    _remoteRenderer.srcObject = null;
    if (updateUi && mounted) {
      setState(() {
        _isMirrorReady = false;
      });
    }

    try {
      await channel?.close();
    } catch (_) {}

    try {
      await connection?.close();
    } catch (_) {}
  }

  Future<bool> _sendPresenterCommand(String direction) async {
    final device = _selectedDevice;
    if (device == null || _isSending) return false;

    setState(() => _isSending = true);

    const port = 15248;
    String? lastError;
    HttpClient? client;
    try {
      client = HttpClient()
        ..connectionTimeout = const Duration(milliseconds: 1300);

      final uri = Uri(
        scheme: 'http',
        host: device.ipAddress.trim(),
        port: port,
        path: '/macro/presenter/$direction',
      );

      final request = await client.getUrl(uri);
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      final response = await request.close().timeout(
            const Duration(milliseconds: 1700),
          );

      final body = await response.transform(utf8.decoder).join();

      if (response.statusCode == 200 || response.statusCode == 202) {
        return true;
      }

      if (response.statusCode == 405) {
        lastError =
            'Device rejected presenter command (405). Pair the phone with /connect first.';
      } else {
        lastError =
            'Command failed on port $port (HTTP ${response.statusCode}): $body';
      }
    } catch (error) {
      lastError = 'Port $port failed: $error';
    } finally {
      client?.close(force: true);
      if (mounted) {
        setState(() => _isSending = false);
      }
    }

    if (!mounted) return false;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(lastError ?? 'Presenter command failed.')),
    );
    return false;
  }

  Future<Map<String, dynamic>?> _postJson({
    required String host,
    required int port,
    required String path,
    required Map<String, dynamic> body,
  }) async {
    HttpClient? client;
    try {
      client = HttpClient()
        ..connectionTimeout = const Duration(milliseconds: 1800);

      final uri = Uri(
        scheme: 'http',
        host: host,
        port: port,
        path: path,
      );

      final request = await client.postUrl(uri);
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      request.headers
          .set(HttpHeaders.contentTypeHeader, 'application/json; charset=utf-8');
      request.write(jsonEncode(body));

      final response = await request.close().timeout(
        const Duration(seconds: 12),
          );

      final payload = await response.transform(utf8.decoder).join();
      if (response.statusCode != 200 && response.statusCode != 202) {
        try {
          final decodedError = jsonDecode(payload);
          if (decodedError is Map && decodedError['error'] != null) {
            _lastLaserConnectError =
                'HTTP ${response.statusCode}: ${decodedError['error']}';
          } else {
            _lastLaserConnectError =
                'HTTP ${response.statusCode}: ${payload.isEmpty ? 'No body' : payload}';
          }
        } catch (_) {
          _lastLaserConnectError =
              'HTTP ${response.statusCode}: ${payload.isEmpty ? 'No body' : payload}';
        }
        return null;
      }

      final decoded = jsonDecode(payload);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
      _lastLaserConnectError = 'Unexpected JSON payload from server.';
      return null;
    } catch (error) {
      _lastLaserConnectError = 'Request failed: $error';
      return null;
    } finally {
      client?.close(force: true);
    }
  }

  Future<int?> _fetchRefreshRate(String host) async {
    HttpClient? client;
    try {
      client = HttpClient()
        ..connectionTimeout = const Duration(milliseconds: 1300);

      final uri = Uri(
        scheme: 'http',
        host: host,
        port: 15249,
        path: '/refreshrate',
      );

      final request = await client.getUrl(uri);
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      final response = await request.close().timeout(
            const Duration(milliseconds: 1800),
          );

      if (response.statusCode != 200 && response.statusCode != 202) {
        return null;
      }

      final payload = await response.transform(utf8.decoder).join();
      final decoded = jsonDecode(payload);

      if (decoded is List && decoded.isNotEmpty && decoded.first is num) {
        return (decoded.first as num).toInt();
      }
      if (decoded is Map && decoded['refreshrate'] is num) {
        return (decoded['refreshrate'] as num).toInt();
      }
      return null;
    } catch (_) {
      return null;
    } finally {
      client?.close(force: true);
    }
  }

  Future<bool> _ensureLaserChannel() async {
    final state = _laserDataChannel?.state;
    if (_peerConnection != null &&
        _laserDataChannel != null &&
        state == RTCDataChannelState.RTCDataChannelOpen) {
      return true;
    }

    if (_laserConnectFuture != null) {
      return _laserConnectFuture!;
    }

    final future = _connectLaserChannel();
    _laserConnectFuture = future;
    final ok = await future;
    if (identical(_laserConnectFuture, future)) {
      _laserConnectFuture = null;
    }
    return ok;
  }

  Future<bool> _connectLaserChannel() async {
    final device = _selectedDevice;
    if (device == null) return false;

    try {
      _lastLaserConnectError = null;
      await _closeLaserChannel();

      final refreshRate = await _fetchRefreshRate(device.ipAddress.trim());
      if (refreshRate != null && refreshRate > 0) {
        _laserRefreshRate = refreshRate;
      }

      final connection = await createPeerConnection(
        {
          'iceServers': <Map<String, dynamic>>[],
        },
      );

      final channel = await connection.createDataChannel(
        'laser',
        RTCDataChannelInit(),
      );
      channel.onDataChannelState = (RTCDataChannelState state) {
        _laserChannelOpen = state == RTCDataChannelState.RTCDataChannelOpen;
      };

      connection.onConnectionState = (RTCPeerConnectionState state) {
        if (state == RTCPeerConnectionState.RTCPeerConnectionStateClosed ||
            state == RTCPeerConnectionState.RTCPeerConnectionStateFailed ||
            state == RTCPeerConnectionState.RTCPeerConnectionStateDisconnected) {
          _remoteRenderer.srcObject = null;
          if (mounted) {
            setState(() {
              _isMirrorReady = false;
            });
          }
        }
      };

      // Mirror the browser reference flow: explicitly request recvonly video.
      await connection.addTransceiver(
        kind: RTCRtpMediaType.RTCRtpMediaTypeVideo,
        init: RTCRtpTransceiverInit(direction: TransceiverDirection.RecvOnly),
      );

      connection.onTrack = (RTCTrackEvent event) {
        if (event.track.kind != 'video') return;

        final stream = event.streams.isNotEmpty ? event.streams.first : null;
        if (stream == null) return;

        _remoteRenderer.srcObject = stream;
        if (mounted) {
          setState(() {
            _isMirrorReady = true;
          });
        }
      };

      connection.onAddStream = (MediaStream stream) {
        _remoteRenderer.srcObject = stream;
        if (mounted) {
          setState(() {
            _isMirrorReady = true;
          });
        }
      };

      final offer = await connection.createOffer(
        {
          'offerToReceiveAudio': false,
          'offerToReceiveVideo': true,
        },
      );

      await connection.setLocalDescription(offer);

      final answerJson = await _postJson(
        host: device.ipAddress.trim(),
        port: 15249,
        path: '/offer',
        body: {
          'sdp': offer.sdp,
          'type': offer.type,
        },
      );
      if (answerJson == null ||
          answerJson['sdp'] is! String ||
          answerJson['type'] is! String) {
        _lastLaserConnectError ??= 'Invalid /offer response from server.';
        await connection.close();
        return false;
      }

      await connection.setRemoteDescription(
        RTCSessionDescription(
          answerJson['sdp'] as String,
          answerJson['type'] as String,
        ),
      );

      _peerConnection = connection;
      _laserDataChannel = channel;
      _laserChannelOpen =
          channel.state == RTCDataChannelState.RTCDataChannelOpen;
      return true;
    } catch (error) {
      _lastLaserConnectError = 'WebRTC setup failed: $error';
      await _closeLaserChannel();
      return false;
    }
  }

  Future<void> _sendLaserUpdate(Offset localPosition, Size trackpadSize) async {
    if (_selectedDevice == null || _laserUpdateInFlight) return;

    final ready = await _ensureLaserChannel();
    if (!ready) {
      if (mounted) {
        final now = DateTime.now();
        final shouldToast = _lastLaserErrorToastAt == null ||
            now.difference(_lastLaserErrorToastAt!) >
                const Duration(seconds: 2);
        if (shouldToast) {
          _lastLaserErrorToastAt = now;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(_lastLaserConnectError == null
                  ? 'Unable to establish WebRTC laser channel.'
                  : 'Unable to establish WebRTC laser channel: ${_lastLaserConnectError!}'),
            ),
          );
        }
      }
      return;
    }

    final nowMs = DateTime.now().millisecondsSinceEpoch;
    final intervalMs = (1000 / (_laserRefreshRate <= 0 ? 30 : _laserRefreshRate))
        .round()
        .clamp(8, 200);
    if (nowMs - _lastLaserUpdateMs < intervalMs) {
      return;
    }
    _lastLaserUpdateMs = nowMs;

    final width = trackpadSize.width <= 0 ? 1.0 : trackpadSize.width;
    final height = trackpadSize.height <= 0 ? 1.0 : trackpadSize.height;

    final normalizedX = (localPosition.dx / width).clamp(0.0, 1.0);
    final normalizedY = (localPosition.dy / height).clamp(0.0, 1.0);

    _laserUpdateInFlight = true;
    try {
      if (!_laserChannelOpen) {
        return;
      }

      final message = jsonEncode({'x': normalizedX, 'y': normalizedY});
      _laserDataChannel?.send(RTCDataChannelMessage(message));
    } catch (_) {
      await _closeLaserChannel();
    } finally {
      _laserUpdateInFlight = false;
    }
  }

  Future<void> _handleTrackpadPanStart(
      DragStartDetails details, Size trackpadSize) async {
    if (_selectedDevice == null) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Select a target device first.')),
      );
      return;
    }

    await _sendLaserUpdate(details.localPosition, trackpadSize);
  }

  Future<void> _handleTrackpadPanUpdate(
      DragUpdateDetails details, Size trackpadSize) async {
    await _sendLaserUpdate(details.localPosition, trackpadSize);
  }

  Future<void> _handleTrackpadPanEnd() async {
    // Keep the channel alive across gestures for smoother pointer control.
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return WillPopScope(
      onWillPop: () async {
        await _disconnectWebRtc(showFeedback: false);
        return true;
      },
      child: Scaffold(
        appBar: AppBar(
          leading: IconButton(
            onPressed: _leavePresenterScreen,
            icon: SvgPicture.asset(
              'assets/Icons/home.svg',
              colorFilter: ColorFilter.mode(colorScheme.onTertiary, BlendMode.srcIn),
              width: 24,
              height: 24,
            ),
          ),
          title: const Text('Presenter Tools'),
          actions: [
            IconButton(
              tooltip: 'Disconnect WebRTC',
              onPressed: () {
                _disconnectWebRtc();
              },
              icon: SvgPicture.asset(
                'assets/Icons/close.svg',
                colorFilter:
                    ColorFilter.mode(colorScheme.onTertiary, BlendMode.srcIn),
                width: 20,
                height: 20,
              ),
            ),
          ],
        ),
        body: Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 92),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Target Device',
              style: TextStyle(
                fontFamily: 'JetBrainsMono',
                fontSize: 18,
                color: colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 10),
            if (widget.devices.isEmpty)
              Text(
                'No devices added yet. Add one in Connect first.',
                style: TextStyle(
                  color: colorScheme.onSurface.withOpacity(0.7),
                  fontFamily: 'JetBrainsMono',
                ),
              )
            else
              DropdownButtonFormField<Device>(
                value: _selectedDevice,
                items: widget.devices
                    .map(
                      (device) => DropdownMenuItem<Device>(
                        value: device,
                        child: Text(
                          device.name.replaceAll(RegExp(r'\.local$'), ''),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    )
                    .toList(),
                onChanged: (value) {
                  setState(() {
                    _selectedDevice = value;
                  });
                  _disconnectWebRtc(showFeedback: false);
                },
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  labelText: 'Device',
                ),
              ),
            const SizedBox(height: 22),
            Text(
              'Screen Mirror',
              style: TextStyle(
                fontFamily: 'JetBrainsMono',
                fontSize: 16,
                color: colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 10),
            AspectRatio(
              aspectRatio: 16 / 9,
              child: Container(
                decoration: BoxDecoration(
                  color: Colors.black,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: colorScheme.onSurface.withOpacity(0.25),
                    width: 1,
                  ),
                ),
                clipBehavior: Clip.antiAlias,
                child: _isMirrorReady
                    ? RTCVideoView(
                        _remoteRenderer,
                        objectFit:
                            RTCVideoViewObjectFit.RTCVideoViewObjectFitContain,
                      )
                    : Center(
                        child: Text(
                          'Mirror connects automatically when you use the trackpad.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.75),
                            fontFamily: 'JetBrainsMono',
                            fontSize: 12,
                          ),
                        ),
                      ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Laser Trackpad',
              style: TextStyle(
                fontFamily: 'JetBrainsMono',
                fontSize: 16,
                color: colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 10),
            Expanded(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final trackpadSize =
                      Size(constraints.maxWidth, constraints.maxHeight);

                  return GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onPanStart: (details) {
                      _handleTrackpadPanStart(details, trackpadSize);
                    },
                    onPanUpdate: (details) {
                      _handleTrackpadPanUpdate(details, trackpadSize);
                    },
                    onPanEnd: (_) {
                      _handleTrackpadPanEnd();
                    },
                    onPanCancel: _handleTrackpadPanEnd,
                    child: Container(
                      decoration: BoxDecoration(
                        color:
                            colorScheme.surfaceContainerHighest.withOpacity(0.35),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                          color: colorScheme.onSurface.withOpacity(0.25),
                          width: 1,
                        ),
                      ),
                      child: Center(
                        child: Text(
                          'Drag your finger to move the laser pointer',
                          style: TextStyle(
                            color: colorScheme.onSurface.withOpacity(0.72),
                            fontFamily: 'JetBrainsMono',
                            fontSize: 12,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
        floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
        floatingActionButton: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6),
        child: Row(
          children: [
            Expanded(
              child: SizedBox(
                height: 56,
                child: FloatingActionButton.extended(
                  heroTag: 'presenterBackFab',
                  onPressed: _selectedDevice == null
                      ? null
                      : () => _sendPresenterCommand('backward'),
                  icon: SvgPicture.asset(
                    'assets/Icons/arrow_back.svg',
                    colorFilter:
                        const ColorFilter.mode(Colors.black, BlendMode.srcIn),
                    width: 22,
                    height: 22,
                  ),
                  label: const Text('Previous'),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: SizedBox(
                height: 56,
                child: FloatingActionButton.extended(
                  heroTag: 'presenterNextFab',
                  onPressed: _selectedDevice == null
                      ? null
                      : () => _sendPresenterCommand('forward'),
                  icon: SvgPicture.asset(
                    'assets/Icons/arrow_forward.svg',
                    colorFilter:
                        const ColorFilter.mode(Colors.black, BlendMode.srcIn),
                    width: 22,
                    height: 22,
                  ),
                  label: const Text('Next'),
                ),
              ),
            ),
          ],
        ),
        ),
      ),
    );
  }
}
