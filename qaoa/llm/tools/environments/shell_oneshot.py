# QAOA category: system, domain: technology
"""Fence markers and output cleaning for one-shot bash execution."""

from __future__ import annotations

# Unique marker to isolate real command output from shell init/exit noise.
OUTPUT_FENCE = "__KAAGEKO_FENCE_a9f7b3__"

_SHELL_NOISE_SUBSTRINGS = (
    "bash: cannot set terminal process group",
    "bash: no job control in this shell",
    "no job control in this shell",
    "cannot set terminal process group",
    "tcsetattr: Inappropriate ioctl for device",
    "Restored session:",
    "Saving session...",
    "Last login:",
    "command not found:",
    "Oh My Zsh",
    "compinit:",
)


def clean_shell_noise(output: str) -> str:
    """Strip shell startup/exit warnings that leak when using -i without a TTY."""

    def _is_noise(line: str) -> bool:
        return any(noise in line for noise in _SHELL_NOISE_SUBSTRINGS)

    lines = output.split("\n")

    while lines and _is_noise(lines[0]):
        lines.pop(0)

    end = len(lines) - 1
    while end >= 0 and (not lines[end] or _is_noise(lines[end])):
        end -= 1

    if end < 0:
        return ""

    cleaned = lines[: end + 1]
    result = "\n".join(cleaned)

    if output.endswith("\n") and result and not result.endswith("\n"):
        result += "\n"
    return result


def extract_fenced_output(raw: str) -> str:
    """Return content between first and last fence markers; else noise-cleaned fallback."""
    first = raw.find(OUTPUT_FENCE)
    if first == -1:
        return clean_shell_noise(raw)

    start = first + len(OUTPUT_FENCE)
    last = raw.rfind(OUTPUT_FENCE)

    if last <= first:
        return clean_shell_noise(raw[start:])

    return raw[start:last]


def fenced_login_command(exec_command: str) -> str:
    """Wrap ``exec_command`` for ``bash -lic`` with printf fences and preserved exit code."""
    return (
        f"printf '{OUTPUT_FENCE}';"
        f" {exec_command};"
        f" __kc_rc=$?;"
        f" printf '{OUTPUT_FENCE}';"
        f" exit $__kc_rc"
    )


__all__ = [
    "OUTPUT_FENCE",
    "clean_shell_noise",
    "extract_fenced_output",
    "fenced_login_command",
]
