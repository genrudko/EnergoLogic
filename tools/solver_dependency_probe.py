from __future__ import annotations

from importlib import metadata
import json
from pathlib import Path
import re
import sys

from packaging.markers import default_environment
from packaging.requirements import Requirement


def normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def distribution_size_bytes(dist: metadata.Distribution) -> int:
    total = 0
    for relative in dist.files or ():
        path = Path(dist.locate_file(relative))
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    return total


def dependency_closure(root: str) -> list[metadata.Distribution]:
    environment = default_environment()
    environment["extra"] = ""
    queue = [root]
    seen: set[str] = set()
    result: list[metadata.Distribution] = []

    while queue:
        requested = queue.pop(0)
        key = normalize_name(requested)
        if key in seen:
            continue
        seen.add(key)

        try:
            dist = metadata.distribution(requested)
        except metadata.PackageNotFoundError:
            continue
        result.append(dist)

        for raw in dist.requires or ():
            requirement = Requirement(raw)
            if requirement.marker is not None and not requirement.marker.evaluate(
                environment
            ):
                continue
            queue.append(requirement.name)

    return result


def main() -> int:
    distributions = dependency_closure("pandapower")
    rows = []
    native_files = 0
    total = 0
    for dist in distributions:
        size = distribution_size_bytes(dist)
        total += size
        for relative in dist.files or ():
            suffix = Path(str(relative)).suffix.lower()
            if suffix in {".so", ".pyd", ".dll", ".dylib"}:
                native_files += 1
        rows.append(
            {
                "name": dist.metadata["Name"],
                "version": dist.version,
                "installed_bytes": size,
            }
        )

    payload = {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "pandapower_dependency_count": len(rows),
        "installed_dependency_bytes": total,
        "native_binary_file_count": native_files,
        "distributions": sorted(rows, key=lambda item: item["name"].lower()),
    }
    print("WS8_DEPENDENCY_FOOTPRINT_JSON=" + json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
