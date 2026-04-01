from __future__ import annotations

import importlib.util
import pathlib
import py_compile
import sys
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"


@dataclass
class ImportTarget:
    label: str
    path: pathlib.Path
    extra_sys_path: pathlib.Path | None = None


def compile_all_python_files() -> list[str]:
    errors: list[str] = []
    for py_file in sorted(TEMPLATES.rglob("*.py")):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"[SYNTAX] {py_file.relative_to(ROOT)} :: {exc.msg}")
    return errors


def try_import(target: ImportTarget) -> str | None:
    path = target.path
    if not path.exists():
        return f"[MISSING] {target.label} :: {path.relative_to(ROOT)} not found"

    original_sys_path = list(sys.path)
    try:
        if target.extra_sys_path is not None:
            sys.path.insert(0, str(target.extra_sys_path))
        spec = importlib.util.spec_from_file_location(target.label, path)
        if spec is None or spec.loader is None:
            return f"[IMPORT] {target.label} :: unable to create module spec"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return None
    except ModuleNotFoundError as exc:
        return f"[DEPENDENCY] {target.label} :: missing module '{exc.name}'"
    except Exception as exc:  # noqa: BLE001
        return f"[RUNTIME] {target.label} :: {type(exc).__name__}: {exc}"
    finally:
        sys.path[:] = original_sys_path


def main() -> int:
    issues: list[str] = []
    issues.extend(compile_all_python_files())

    targets = [
        ImportTarget(
            "fastapi.main",
            ROOT / "templates/backends/fastapi/main.py",
            ROOT / "templates/backends/fastapi",
        ),
        ImportTarget(
            "flask.run",
            ROOT / "templates/backends/flask/run.py",
            ROOT / "templates/backends/flask",
        ),
        ImportTarget(
            "django.manage",
            ROOT / "templates/backends/django/manage.py",
            ROOT / "templates/backends/django",
        ),
        ImportTarget(
            "rag.pipeline",
            ROOT / "templates/ml_llm/langchain-rag/rag_pipeline.py",
            ROOT / "templates/ml_llm/langchain-rag",
        ),
        ImportTarget(
            "multi.graph",
            ROOT / "templates/ml_llm/multi-agent/graph.py",
            ROOT / "templates/ml_llm/multi-agent",
        ),
        ImportTarget(
            "fine_tune.train",
            ROOT / "templates/ml_llm/fine-tuning/train.py",
            ROOT / "templates/ml_llm/fine-tuning",
        ),
        ImportTarget(
            "streamlit.app",
            ROOT / "templates/dashboards/streamlit/app.py",
            ROOT / "templates/dashboards/streamlit",
        ),
        ImportTarget(
            "tableau.server",
            ROOT / "templates/dashboards/tableau-embed/server_config.py",
            ROOT / "templates/dashboards/tableau-embed",
        ),
        ImportTarget(
            "fs.fastapi_react.backend",
            ROOT / "templates/fullstack/fastapi-react/backend/main.py",
            ROOT / "templates/fullstack/fastapi-react/backend",
        ),
        ImportTarget(
            "fs.flask_nextjs.backend",
            ROOT / "templates/fullstack/flask-nextjs/backend/run.py",
            ROOT / "templates/fullstack/flask-nextjs/backend",
        ),
    ]

    for target in targets:
        result = try_import(target)
        if result:
            issues.append(result)

    if issues:
        print("SANITY CHECK: ISSUES FOUND")
        for issue in issues:
            print(issue)
        return 1

    print("SANITY CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
