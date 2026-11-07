"""Replay the reference manifest with official Lottie Android and native graphics.

Requires existing JDK 21 and Maven 3.9+, plus the Python development environment.
Maven resolves the pinned test dependencies; no Android SDK or device is used.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image
from scripts.check_lottie_fidelity import assess


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maven", type=Path, required=True)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True, help="Web check's cases.json")
    parser.add_argument("--output", type=Path, required=True, help="New artifact directory")
    parser.add_argument(
        "--settings", type=Path, help="Existing Maven settings, including mirrors/proxy"
    )
    parser.add_argument("--runtime-home", type=Path, help="Writable Robolectric SDK cache")
    parser.add_argument(
        "--trust-store", type=Path, help="Existing Java CA store for a managed proxy"
    )
    args = parser.parse_args()
    if not args.maven.is_file() or not (args.java_home / "bin/javac").is_file():
        parser.error("existing Maven and a full JDK are required")
    if not args.cases.is_file() or args.settings and not args.settings.is_file():
        parser.error("cases.json and any supplied Maven settings must exist")
    cases = json.loads(args.cases.read_text())["cases"]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    runtime_home = (args.runtime_home or output / ".runtime-home").resolve()
    runtime_home.mkdir(parents=True, exist_ok=True)
    fixture = Path(__file__).resolve().parents[1] / "tests/fixtures/lottie/android"
    with tempfile.TemporaryDirectory(prefix="quickthumb-android-") as temporary:
        project = Path(temporary) / "project"
        shutil.copytree(fixture, project)
        command = [str(args.maven.resolve()), "-B", "-f", str(project / "pom.xml")]
        if args.settings:
            command.extend(["-s", str(args.settings.resolve())])
        command.extend(
            [
                f"-Dcases={args.cases.resolve()}",
                f"-Doutput={output}",
                f"-Dpython.executable={sys.executable}",
                f"-Druntime.home={runtime_home}",
            ]
        )
        # Robolectric's SDK resolver runs in the test JVM, outside Maven's proxy config.
        proxy = urlsplit(os.environ.get("https_proxy", os.environ.get("HTTPS_PROXY", "")))
        if proxy.hostname:
            command.extend(
                [
                    f"-Drobolectric.dependency.proxy.host={proxy.hostname}",
                    f"-Drobolectric.dependency.proxy.port={proxy.port or 80}",
                ]
            )
        if args.trust_store:
            command.append(f"-Djavax.net.ssl.trustStore={args.trust_store.resolve()}")
        command.append("test")
        environment = {**os.environ, "JAVA_HOME": str(args.java_home.resolve())}
        with (output / "maven.log").open("w") as log:
            completed = subprocess.run(
                command, env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=600
            )
    execution = output / "execution.json"
    if not execution.is_file():
        detail = (output / "maven.log").read_text(errors="replace")[-8000:]
        raise RuntimeError(f"Android harness did not complete; maven.log tail:\n{detail}")
    observed = json.loads(execution.read_text())
    results = []
    for case, row in zip(cases, observed.pop("cases"), strict=True):
        if case["name"] != row["name"]:
            raise RuntimeError("Android capture order mismatch")
        if "error" in row:
            results.append({**case, **row, "passed": False})
            continue
        with Image.open(row["screenshot"]) as actual:
            measurements = assess(case, actual)
        expected_frame = 0 if case["control"] == "frozen" else case["frame"]
        matches = row["frame"] == expected_frame
        results.append(
            {
                **case,
                **row,
                **measurements,
                "renderer": "lottie-android",
                "frame_matches": matches,
                "passed": measurements["passed"] and matches,
            }
        )
    passed = (
        completed.returncode == 0
        and observed["native_runtime_loaded"]
        and all(row["passed"] for row in results)
    )
    report = {
        **observed,
        "maven_returncode": completed.returncode,
        "cases": results,
        "passed": passed,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(f"Android native graphics: {sum(row['passed'] for row in results)}/{len(results)} passed")
    if not passed:
        for row in results:
            if not row["passed"]:
                print(
                    json.dumps(
                        {
                            key: row[key]
                            for key in ("name", "error", "regions", "probes")
                            if key in row
                        }
                    )
                )
        raise SystemExit(f"Android comparisons failed; inspect {output / 'report.json'}")


if __name__ == "__main__":
    main()
