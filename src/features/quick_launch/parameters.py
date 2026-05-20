from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

PLACEHOLDER_PATTERN = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    name: str


class MissingParameterError(ValueError):
    def __init__(self, missing: list[str]) -> None:
        self.missing = list(missing)
        super().__init__(f"缺少参数: {', '.join(self.missing)}")


def extract_parameters(*texts: str) -> list[ParameterSpec]:
    """Extract unique ${name} placeholders, preserving first-seen order."""
    seen: dict[str, None] = {}
    for text in texts:
        if not text:
            continue
        for match in PLACEHOLDER_PATTERN.finditer(text):
            seen.setdefault(match.group(1), None)
    return [ParameterSpec(name=name) for name in seen.keys()]


def substitute(
    text: str,
    values: dict[str, str],
    *,
    quote: bool,
    strict: bool = True,
) -> str:
    """Replace ${name} placeholders. Shell-quote values when quote=True."""
    if not text:
        return text
    missing: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            if strict:
                missing.append(name)
                return match.group(0)
            return ""
        raw = "" if values[name] is None else str(values[name])
        return shlex.quote(raw) if quote else raw

    result = PLACEHOLDER_PATTERN.sub(_replace, text)
    if strict and missing:
        unique_missing: list[str] = []
        for name in missing:
            if name not in unique_missing:
                unique_missing.append(name)
        raise MissingParameterError(unique_missing)
    return result


def substitute_mapping(
    mapping: dict[str, str],
    values: dict[str, str],
    *,
    quote: bool,
    strict: bool = True,
) -> dict[str, str]:
    return {
        key: substitute(str(val or ""), values, quote=quote, strict=strict)
        for key, val in (mapping or {}).items()
    }
