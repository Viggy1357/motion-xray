"""Resolve third-party dependencies for each isolated container environment."""

from pathlib import Path
import subprocess
import tomllib


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    targets = {
        "api": ("contracts", "providers", "benchmarks"),
        "test": ("contracts", "providers", "benchmarks", "movement", "scoring"),
        "worker": ("contracts", "providers", "benchmarks", "movement", "scoring"),
    }
    output = root / "infra/requirements"
    output.mkdir(exist_ok=True)
    for name, packages in targets.items():
        requirements = {"hatchling==1.25.0"}
        for package in packages:
            config = tomllib.loads((root / f"packages/{package}/pyproject.toml").read_text())
            requirements.update(dep for dep in config["project"]["dependencies"] if not dep.startswith("motion-xray-"))
            if package == "providers":
                extras = ("llm", "search") if name == "api" else ("pose", "llm") if name == "worker" else ()
                for extra in extras:
                    requirements.update(config["project"]["optional-dependencies"][extra])
        if name in ("api", "test"):
            api = tomllib.loads((root / "services/api/pyproject.toml").read_text())
            requirements.update(dep for dep in api["project"]["dependencies"] if not dep.startswith("motion-xray-"))
        if name == "test":
            requirements.update(["ruff==0.6.9", "mypy==1.11.2", "pytest==8.3.3", "pyyaml==6.0.2", "httpx==0.27.2"])
        source = output / f"{name}.in"
        source.write_text("\n".join(sorted(requirements)) + "\n")
        subprocess.run(["uv", "pip", "compile", str(source), "--generate-hashes", "--output-file", str(output / f"{name}.lock")], check=True)


if __name__ == "__main__":
    main()
