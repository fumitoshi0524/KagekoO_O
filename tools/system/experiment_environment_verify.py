"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import os
    import platform
    import psutil
    import subprocess
    import sys
    from importlib.metadata import distributions, version as get_version
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version

    try:
        data = json.loads(payload)
        report = {}
        issues = []

        # Check RAM
        system_ram_gb = psutil.virtual_memory().total / (1024**3)
        req_ram = data.get('min_ram_gb', 0)
        report['ram_gb'] = {'required': req_ram, 'actual': round(system_ram_gb, 2), 'pass': system_ram_gb >= req_ram}
        if not report['ram_gb']['pass']:
            issues.append(f"Insufficient RAM: {round(system_ram_gb, 2)} GB < {req_ram} GB")

        # Check CPU cores
        system_cpu = psutil.cpu_count(logical=True)
        req_cpu = data.get('min_cpu_cores', 0)
        report['cpu_cores'] = {'required': req_cpu, 'actual': system_cpu, 'pass': system_cpu >= req_cpu}
        if not report['cpu_cores']['pass']:
            issues.append(f"Insufficient CPU cores: {system_cpu} < {req_cpu}")

        # Check disk space
        disk_path = '/'
        if platform.system() == 'Windows':
            disk_path = 'C:\\'
        free_disk_gb = psutil.disk_usage(disk_path).free / (1024**3)
        req_disk = data.get('min_disk_gb', 0)
        report['disk_gb'] = {'required': req_disk, 'actual': round(free_disk_gb, 2), 'pass': free_disk_gb >= req_disk}
        if not report['disk_gb']['pass']:
            issues.append(f"Insufficient disk space: {round(free_disk_gb, 2)} GB < {req_disk} GB")

        # Check OS family
        system_os = platform.system().lower()
        req_os = data.get('os_family', 'any')
        if req_os != 'any':
            report['os_family'] = {'required': req_os, 'actual': system_os, 'pass': system_os == req_os}
            if not report['os_family']['pass']:
                issues.append(f"Unsupported OS: {system_os} != {req_os}")
        else:
            report['os_family'] = {'required': 'any', 'actual': system_os, 'pass': True}

        # Check required packages
        required_pkgs = data.get('required_packages', [])
        pkg_report = {}
        for pkg_spec in required_pkgs:
            if '>=' in pkg_spec or '==' in pkg_spec or '<=' in pkg_spec or '>' in pkg_spec or '<' in pkg_spec:
                # parse version constraint
                import re
                match = re.match(r'^([a-zA-Z0-9_\-]+)([><=!]+.*)$', pkg_spec)
                if match:
                    pkg_name = match.group(1).lower().replace('-', '_')
                    constraint_str = match.group(2)
                    spec = SpecifierSet(constraint_str)
                else:
                    pkg_name = pkg_spec.lower().replace('-', '_')
                    spec = None
            else:
                pkg_name = pkg_spec.lower().replace('-', '_')
                spec = None
            try:
                installed_version = get_version(pkg_name)
                if spec:
                    satisfied = spec.contains(Version(installed_version))
                else:
                    satisfied = True
                pkg_report[pkg_name] = {'required': pkg_spec, 'installed': installed_version, 'pass': satisfied}
                if not satisfied:
                    issues.append(f"Package {pkg_name}: version {installed_version} does not satisfy {pkg_spec}")
            except Exception as e:
                pkg_report[pkg_name] = {'required': pkg_spec, 'installed': None, 'pass': False}
                issues.append(f"Package {pkg_name} not installed")
        report['packages'] = pkg_report

        report['overall_pass'] = len(issues) == 0
        report['issues'] = issues
        return json.dumps(report, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'



TOOL_SPEC = {
    "name": "experiment_environment_verify",
    "description": "Verify that the current system environment meets the minimum requirements to reproduce a scientific experiment by checking available RAM, CPU cores, disk space, installed software packages, and Python library versions, returning a compliance report with pass/fail status for each requirement.",
    "category": "system",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "experiment_id": {
            "type": "string",
            "description": "Unique identifier for the experiment or project, used to reference stored or documented requirements."
        },
        "min_ram_gb": {
            "type": "number",
            "description": "Minimum required RAM in gigabytes."
        },
        "min_cpu_cores": {
            "type": "integer",
            "description": "Minimum number of CPU cores required."
        },
        "min_disk_gb": {
            "type": "number",
            "description": "Minimum free disk space in gigabytes."
        },
        "required_packages": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of required Python package names (e.g., numpy, pandas, scipy) with optional version constraints like 'numpy>=1.21.0'."
        },
        "os_family": {
            "type": "string",
            "enum": [
                "linux",
                "windows",
                "darwin",
                "any"
            ],
            "description": "Required operating system family. Use 'any' for no restriction."
        }
    },
    "required": [
        "min_ram_gb",
        "min_cpu_cores",
        "min_disk_gb"
    ]
},
}
