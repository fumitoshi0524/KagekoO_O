"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import subprocess
    import pwd
    import grp
    try:
        data = json.loads(payload)
        op = data.get('operation')
        username = data.get('username', '')
        groups = data.get('groups', [])
        full_name = data.get('full_name', '')

        if op == 'list':
            result = []
            for user in pwd.getpwall():
                if user.pw_uid >= 1000:  # regular users
                    try:
                        lastlog = subprocess.check_output(['lastlog', '-u', user.pw_name], text=True).split('\n')[1].strip()
                    except:
                        lastlog = 'never'
                    result.append({
                        'username': user.pw_name,
                        'uid': user.pw_uid,
                        'gid': user.pw_gid,
                        'full_name': user.pw_gecos,
                        'home': user.pw_dir,
                        'shell': user.pw_shell,
                        'last_login': lastlog
                    })
            return json.dumps({'accounts': result}, ensure_ascii=False)

        if not username:
            return 'error: username required for this operation'

        if op == 'create':
            cmd = ['useradd', '-m', username]
            if full_name:
                cmd.extend(['-c', full_name])
            subprocess.check_call(cmd)
            if groups:
                subprocess.check_call(['usermod', '-aG', ','.join(groups), username])
            return json.dumps({'status': 'created', 'username': username}, ensure_ascii=False)

        elif op == 'disable':
            subprocess.check_call(['usermod', '-L', '-e', '1', username])
            return json.dumps({'status': 'disabled', 'username': username}, ensure_ascii=False)

        elif op == 'delete':
            subprocess.check_call(['userdel', '-r', username])
            return json.dumps({'status': 'deleted', 'username': username}, ensure_ascii=False)

        elif op == 'update_groups':
            current_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
            subprocess.check_call(['usermod', '-G', ','.join(groups), username])
            return json.dumps({'status': 'groups_updated', 'username': username, 'old_groups': current_groups, 'new_groups': groups}, ensure_ascii=False)

        else:
            return 'error: unknown operation'

    except subprocess.CalledProcessError as e:
        return f'error: command failed with exit code {e.returncode}: {e.stderr}'
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "user_account_manager",
    "description": "Manage user accounts in the system: create, disable, or delete accounts, update group memberships, and list accounts with status and last login time. Returns operation status or account details.",
    "category": "system",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "description": "Operation to perform: create, disable, delete, update_groups, or list",
            "enum": [
                "create",
                "disable",
                "delete",
                "update_groups",
                "list"
            ]
        },
        "username": {
            "type": "string",
            "description": "Username for the target account (lowercase, alphanumeric, 3-32 characters)"
        },
        "groups": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Optional: List of group names for group membership update"
        },
        "full_name": {
            "type": "string",
            "description": "Optional: Full display name for new account creation"
        }
    },
    "required": [
        "operation"
    ]
},
}
