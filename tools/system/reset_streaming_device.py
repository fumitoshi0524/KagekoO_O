"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Reset a streaming media device on the local network."""
    import json
    import socket
    import time
    import re

    try:
        data = json.loads(payload)
        device_ip = data.get('device_ip')
        device_type = data.get('device_type')
        auth_token = data.get('auth_token', '')

        if not device_ip or not device_type:
            return json.dumps({"error": "device_ip and device_type are required"}, ensure_ascii=False)

        # Validate IP format
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', device_ip):
            return json.dumps({"error": "Invalid IP address format"}, ensure_ascii=False)

        # Validate IP is not a reserved/broadcast address
        octets = [int(o) for o in device_ip.split('.')]
        if octets[0] == 0 or octets[0] >= 224 or any(o > 255 for o in octets):
            return json.dumps({"error": "IP address is not a valid host address"}, ensure_ascii=False)

        # Build reset command based on device type
        if device_type == 'roku':
            # Roku ECP protocol - send keypress for reboot
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect((device_ip, 8060))
                # Send keydown for the 'Home' key five times (Roku trick to get to settings)
                for _ in range(5):
                    sock.sendall(b'POST /keypress/Home HTTP/1.1\r\nHost: ' + device_ip.encode() + b':8060\r\n\r\n')
                    time.sleep(0.1)
                # Send keydown for 'Power' (System Reboot on some models)
                sock.sendall(b'POST /keypress/Power HTTP/1.1\r\nHost: ' + device_ip.encode() + b':8060\r\n\r\n')
                sock.close()
                return json.dumps({"status": "ok", "detail": f"Reset command sent to Roku at {device_ip}"}, ensure_ascii=False)
            except socket.timeout:
                return json.dumps({"error": "Connection timed out - Roku not reachable on port 8060"}, ensure_ascii=False)
            except ConnectionRefusedError:
                return json.dumps({"error": "Connection refused - Roku web server not enabled on this device"}, ensure_ascii=False)

        elif device_type == 'fire_tv':
            # Fire TV uses ADB (Android Debug Bridge) over network
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3.0)
                sock.connect((device_ip, 5555))
                # ADB connect message
                sock.sendall(b'CNXN\x00\x00\x00\x01\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
                response = sock.recv(1024)
                if b'CNXN' in response:
                    # Send reboot command via ADB
                    sock.sendall(b'OPEN\x00\x00\x00\x01\x00\x00\x00\x09shell:reboot\x00')
                    time.sleep(0.3)
                    sock.close()
                    return json.dumps({"status": "ok", "detail": f"Reset command sent to Fire TV at {device_ip}"}, ensure_ascii=False)
                else:
                    sock.close()
                    return json.dumps({"error": "Fire TV ADB handshake failed - ensure ADB debugging is enabled"}, ensure_ascii=False)
            except socket.timeout:
                return json.dumps({"error": "Connection timed out - Fire TV ADB not reachable on port 5555"}, ensure_ascii=False)
            except ConnectionRefusedError:
                return json.dumps({"error": "Connection refused - ADB debugging not enabled on Fire TV"}, ensure_ascii=False)

        elif device_type == 'apple_tv':
            # Apple TV uses HomeKit IP protocol for reboot (simplified version)
            if not auth_token:
                return json.dumps({"error": "auth_token is required for Apple TV reset"}, ensure_ascii=False)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3.0)
                sock.connect((device_ip, 3689))
                # Simplified reboot sequence (actual HomeKit implementation would be more complex)
                sock.sendall(b'\x12\x00\x00\x00\x00\x00\x00\x00' + auth_token.encode()[:16].ljust(16, b'\x00'))
                response = sock.recv(1024)
                sock.close()
                if b'\x12' in response:
                    return json.dumps({"status": "ok", "detail": f"Reset command sent to Apple TV at {device_ip}"}, ensure_ascii=False)
                else:
                    return json.dumps({"error": "Apple TV did not acknowledge reset command - check auth token"}, ensure_ascii=False)
            except socket.timeout:
                return json.dumps({"error": "Connection timed out - Apple TV not reachable on port 3689"}, ensure_ascii=False)

        elif device_type == 'chromecast':
            # Chromecast uses Cast v2 protocol (simplified restart)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect((device_ip, 8009))
                # Cast protocol: send a simplified reboot message
                sock.sendall(b'GET /setup/reboot HTTP/1.1\r\nHost: ' + device_ip.encode() + b':8009\r\n\r\n')
                response = sock.recv(1024)
                sock.close()
                if b'200 OK' in response:
                    return json.dumps({"status": "ok", "detail": f"Reset command sent to Chromecast at {device_ip}"}, ensure_ascii=False)
                else:
                    return json.dumps({"error": "Chromecast did not accept reset command"}, ensure_ascii=False)
            except socket.timeout:
                return json.dumps({"error": "Connection timed out - Chromecast not reachable on port 8009"}, ensure_ascii=False)

        elif device_type == 'nvidia_shield':
            # NVIDIA Shield uses ADB similar to Fire TV
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3.0)
                sock.connect((device_ip, 5555))
                # Same ADB handshake as Fire TV
                sock.sendall(b'CNXN\x00\x00\x00\x01\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
                response = sock.recv(1024)
                if b'CNXN' in response:
                    sock.sendall(b'OPEN\x00\x00\x00\x01\x00\x00\x00\x09shell:reboot\x00')
                    time.sleep(0.3)
                    sock.close()
                    return json.dumps({"status": "ok", "detail": f"Reset command sent to NVIDIA Shield at {device_ip}"}, ensure_ascii=False)
                else:
                    sock.close()
                    return json.dumps({"error": "Shield ADB handshake failed - ensure ADB debugging is enabled"}, ensure_ascii=False)
            except socket.timeout:
                return json.dumps({"error": "Connection timed out - NVIDIA Shield not reachable on port 5555"}, ensure_ascii=False)
            except ConnectionRefusedError:
                return json.dumps({"error": "Connection refused - ADB debugging not enabled on Shield"}, ensure_ascii=False)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON payload: {str(e)}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, ensure_ascii=False)



TOOL_SPEC = {
    "name": "reset_streaming_device",
    "description": "Reset a streaming media device (e.g., Roku, Fire TV, Apple TV) by sending a restart command through the local network. Returns a status message indicating whether the reset command was accepted or encountered an error.",
    "category": "system",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "device_ip": {
            "type": "string",
            "description": "IP address of the streaming device on the local network (e.g., '192.168.1.100')",
            "examples": [
                "192.168.1.100",
                "10.0.0.50"
            ]
        },
        "device_type": {
            "type": "string",
            "description": "Type of streaming device to reset",
            "enum": [
                "roku",
                "fire_tv",
                "apple_tv",
                "chromecast",
                "nvidia_shield"
            ]
        },
        "auth_token": {
            "type": "string",
            "description": "Optional: Authentication token if required by the device API (e.g., Roku DCP token or Apple TV HomeKit code)"
        }
    },
    "required": [
        "device_ip",
        "device_type"
    ]
},
}
