"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Diagnose and resolve streaming service issues."""
    import json
    try:
        data = json.loads(payload)
        
        # Validate required fields
        if "service_name" not in data or not data["service_name"]:
            return json.dumps({"error": "service_name is required"}, ensure_ascii=False)
        
        service = data["service_name"]
        error_code = data.get("error_code", "").strip()
        symptom = data.get("symptom", "").strip()
        device = data.get("device_type", "unknown")
        internet_speed = data.get("internet_speed_mbps", None)
        
        # Service health check database (simulated real-world data)
        service_health = {
            "Netflix": {"status": "operational", "last_outage": None, "uptime_percent": 99.97},
            "Spotify": {"status": "operational", "last_outage": "2024-03-15", "uptime_percent": 99.82},
            "YouTube": {"status": "operational", "last_outage": None, "uptime_percent": 99.99},
            "Disney+": {"status": "operational", "last_outage": None, "uptime_percent": 99.95},
            "Hulu": {"status": "degraded", "last_outage": "2024-03-20", "uptime_percent": 98.76},
            "Amazon Prime Video": {"status": "operational", "last_outage": None, "uptime_percent": 99.88},
            "HBO Max": {"status": "operational", "last_outage": None, "uptime_percent": 99.91},
            "Apple TV+": {"status": "operational", "last_outage": None, "uptime_percent": 99.94},
            "Other": {"status": "unknown", "last_outage": None, "uptime_percent": None}
        }
        
        # Minimum internet speed requirements per service (Mbps)
        min_speed = {
            "Netflix": 5,
            "Spotify": 0.5,
            "YouTube": 5,
            "Disney+": 5,
            "Hulu": 5,
            "Amazon Prime Video": 3,
            "HBO Max": 5,
            "Apple TV+": 5,
            "Other": 3
        }
        
        health = service_health.get(service, service_health["Other"])
        required_speed = min_speed.get(service, 3)
        
        # Build troubleshooting steps based on inputs
        steps = []
        root_cause = None
        resolution_type = None
        
        # Check service health first
        if health["status"] == "degraded":
            steps.append(f"{service} is currently experiencing degraded performance. Wait for the service to recover. Last known issue: {health['last_outage']}")
            root_cause = "service_outage"
        elif health["status"] == "operational":
            steps.append(f"{service} is currently operational (uptime: {health['uptime_percent']}%). Issue is likely device-side.")
            root_cause = "device_side_issue"
        
        # Check internet speed if provided
        if internet_speed is not None:
            if internet_speed < required_speed:
                steps.append(f"Internet speed ({internet_speed} Mbps) is below the minimum requirement of {required_speed} Mbps for {service}. Upgrade your internet plan or reduce network congestion.")
                if root_cause is None:
                    root_cause = "low_bandwidth"
            elif internet_speed < required_speed * 2:
                steps.append(f"Internet speed ({internet_speed} Mbps) is at the minimum threshold. Consider upgrading for better 4K streaming and multiple simultaneous streams.")
            else:
                steps.append(f"Internet speed ({internet_speed} Mbps) is sufficient for streaming on {service}.")
        
        # Analyze error codes (simulated real error database)
        error_db = {
            "NW-2-5": {"service": "Netflix", "cause": "network connectivity issue", "fix": "Restart your router and modem. Check for Wi-Fi interference or switch to a wired connection.", "severity": "medium"},
            "NW-3-6": {"service": "Netflix", "cause": "DNS resolution failure", "fix": "Change your DNS settings to 8.8.8.8 (Google DNS) or 1.1.1.1 (Cloudflare).", "severity": "medium"},
            "auth_error": {"service": "Spotify", "cause": "authentication token expired", "fix": "Log out of the app and log back in. If issue persists, reset your password.", "severity": "low"},
            "playback_error": {"service": "YouTube", "cause": "browser cache or extension conflict", "fix": "Clear browser cache and cookies, disable ad blockers, or try incognito mode.", "severity": "low"},
            "error_code_83": {"service": "Disney+", "cause": "DRM authentication failure", "fix": "Update your device's operating system and browser. Disable hardware acceleration in browser settings.", "severity": "high"},
            "run_unexpected_error": {"service": "Hulu", "cause": "corrupted app data", "fix": "Force stop the app, clear cache (Settings -> Apps -> Hulu -> Storage -> Clear Cache), then restart the app.", "severity": "medium"}
        }
        
        if error_code and error_code in error_db:
            error_info = error_db[error_code]
            if error_info["service"] == service or error_info["service"] == "general":
                steps.append(f"Error {error_code}: {error_info['cause']}. Fix: {error_info['fix']}")
                root_cause = error_info["cause"]
                resolution_type = "specific_fix"
        
        # Device-specific recommendations
        device_tips = {
            "smart_tv": "Power cycle your TV (unplug for 30 seconds). Check for firmware updates in TV settings.",
            "mobile_phone": "Force stop the app and restart your phone. Check for app updates in the app store.",
            "tablet": "Close background apps and restart the device. Ensure the app is updated.",
            "desktop/laptop": "Clear browser cache and cookies. Try a different browser or disable VPN/proxy.",
            "streaming_stick": "Unplug the streaming stick for 30 seconds. Check HDMI connection and try a different USB power source.",
            "game_console": "Restart the console in power-saving mode. Check for system updates under Settings.",
            "other": "Restart the device and ensure all software is up to date."
        }
        
        if device != "unknown" and root_cause != "low_bandwidth":
            tip = device_tips.get(device, "Restart your device and try again.")
            steps.append(f"Device tip ({device}): {tip}")
        
        # General fallback steps
        if not steps:
            steps = [
                "Restart your device and the streaming app.",
                "Check your internet connection and restart your router.",
                f"Visit {service}'s official status page to verify service health.",
                "Contact the streaming service's customer support if the issue persists."
            ]
            root_cause = "unknown"
        
        # Build result
        result = {
            "service": service,
            "service_status": health["status"],
            "service_uptime": f"{health['uptime_percent']}%" if health["uptime_percent"] else "unknown",
            "troubleshooting_steps": steps,
            "diagnosis": {
                "root_cause": root_cause,
                "severity": "high" if root_cause == "service_outage" else "medium" if error_code else "low",
                "resolution_type": resolution_type if resolution_type else "general_guidance"
            },
            "recommendation": "Wait and try again later" if health["status"] == "degraded" else "Follow the troubleshooting steps above"
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Failed to process request: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "streaming_service_troubleshooter",
    "description": "Diagnose and resolve common streaming service issues for entertainment platforms (Netflix, Spotify, YouTube, etc.) by analyzing error codes, playback symptoms, and device status to return actionable troubleshooting steps and service health status.",
    "category": "system",
    "domain": "entertainment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "service_name": {
            "type": "string",
            "description": "The name of the streaming service experiencing issues (e.g., Netflix, Spotify, YouTube, Disney+, Hulu)",
            "enum": [
                "Netflix",
                "Spotify",
                "YouTube",
                "Disney+",
                "Hulu",
                "Amazon Prime Video",
                "HBO Max",
                "Apple TV+",
                "Other"
            ]
        },
        "error_code": {
            "type": "string",
            "description": "Optional: The specific error code shown by the streaming service (e.g., NW-2-5 for Netflix, auth_error for Spotify). Leave empty if no error code is displayed."
        },
        "symptom": {
            "type": "string",
            "description": "Optional: Description of the issue being experienced (e.g., buffering, no audio, black screen, login failure, poor video quality)",
            "enum": [
                "buffering/stuttering",
                "no audio",
                "black screen",
                "login failure",
                "poor video quality",
                "app crashes on launch",
                "subtitles not working",
                "content not loading",
                "other"
            ]
        },
        "device_type": {
            "type": "string",
            "description": "Optional: The type of device being used for streaming",
            "enum": [
                "smart_tv",
                "mobile_phone",
                "tablet",
                "desktop/laptop",
                "streaming_stick",
                "game_console",
                "other"
            ]
        },
        "internet_speed_mbps": {
            "type": "number",
            "description": "Optional: Current internet speed in Mbps. Provide if available to check minimum streaming requirements."
        }
    },
    "required": [
        "service_name"
    ]
},
}
