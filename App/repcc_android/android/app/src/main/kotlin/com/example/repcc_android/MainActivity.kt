package com.example.repcc_android

import android.content.Context
import android.net.wifi.WifiManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
	private var multicastLock: WifiManager.MulticastLock? = null

	override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
		super.configureFlutterEngine(flutterEngine)

		MethodChannel(
			flutterEngine.dartExecutor.binaryMessenger,
			"repcc/network"
		).setMethodCallHandler { call, result ->
			when (call.method) {
				"acquireMulticastLock" -> result.success(acquireMulticastLock())
				"releaseMulticastLock" -> result.success(releaseMulticastLock())
				else -> result.notImplemented()
			}
		}
	}

	private fun acquireMulticastLock(): Boolean {
		val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
			?: return false

		if (multicastLock?.isHeld == true) {
			return true
		}

		multicastLock = wifiManager.createMulticastLock("repcc_mdns_lock").apply {
			setReferenceCounted(false)
			acquire()
		}

		return multicastLock?.isHeld == true
	}

	private fun releaseMulticastLock(): Boolean {
		val lock = multicastLock ?: return true
		if (lock.isHeld) {
			lock.release()
		}
		multicastLock = null
		return true
	}

	override fun onDestroy() {
		releaseMulticastLock()
		super.onDestroy()
	}
}
