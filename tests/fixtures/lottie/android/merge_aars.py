"""Expose classes from the exact AAR dependency closure to the test JVM."""

import io
import sys
import zipfile
from pathlib import Path


def main() -> None:
    source, destination = (Path(value).resolve() for value in sys.argv[1:])
    destination.mkdir(parents=True, exist_ok=True)
    for archive in sorted(source.glob("*.aar")):
        with (
            zipfile.ZipFile(archive) as aar,
            zipfile.ZipFile(io.BytesIO(aar.read("classes.jar"))) as classes,
        ):
            for name in classes.namelist():
                if not name.endswith(".class"):
                    continue
                output = (destination / name).resolve()
                if not output.is_relative_to(destination):
                    raise ValueError("AAR class escaped the test classpath")
                data = classes.read(name)
                if output.exists() and output.read_bytes() != data:
                    raise ValueError(f"Conflicting AAR class: {name}")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(data)


if __name__ == "__main__":
    main()
