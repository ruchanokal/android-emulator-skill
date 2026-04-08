#!/usr/bin/env python3
"""Build Android projects and run tests using Gradle."""

import argparse
import json
import sys
import os
import subprocess
import time


class AndroidBuilder:
    def __init__(self, project_dir=None):
        self.project_dir = project_dir or os.getcwd()
        self.gradlew = os.path.join(self.project_dir, "gradlew")
        if not os.path.exists(self.gradlew):
            # Try parent directory
            parent = os.path.dirname(self.project_dir)
            self.gradlew = os.path.join(parent, "gradlew")

    def _run_gradle(self, tasks, extra_args=None, timeout=600):
        """Run gradle tasks."""
        cmd = [self.gradlew] + tasks
        if extra_args:
            cmd.extend(extra_args)

        start = time.time()
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout, cwd=self.project_dir
            )
            elapsed = time.time() - start
            return {
                "success": result.returncode == 0,
                "elapsed": f"{elapsed:.1f}s",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Build timed out", "elapsed": f"{timeout}s"}
        except FileNotFoundError:
            return {"success": False, "error": f"gradlew not found at {self.gradlew}"}

    def build(self, module=None, variant="debug", clean=False):
        """Build the project."""
        tasks = []
        if clean:
            tasks.append("clean")

        if module:
            tasks.append(f":{module}:assemble{variant.capitalize()}")
        else:
            tasks.append(f"assemble{variant.capitalize()}")

        return self._run_gradle(tasks)

    def test(self, module=None, variant="debug"):
        """Run unit tests."""
        if module:
            task = f":{module}:test{variant.capitalize()}UnitTest"
        else:
            task = f"test{variant.capitalize()}UnitTest"
        return self._run_gradle([task])

    def connected_test(self, module=None, variant="debug"):
        """Run instrumented tests on connected device."""
        if module:
            task = f":{module}:connected{variant.capitalize()}AndroidTest"
        else:
            task = f"connected{variant.capitalize()}AndroidTest"
        return self._run_gradle([task])

    def install(self, module=None, variant="debug"):
        """Install app on connected device."""
        if module:
            task = f":{module}:install{variant.capitalize()}"
        else:
            task = f"install{variant.capitalize()}"
        return self._run_gradle([task])

    def lint(self, module=None):
        """Run lint checks."""
        if module:
            task = f":{module}:lint"
        else:
            task = "lint"
        return self._run_gradle([task])

    def parse_errors(self, build_output):
        """Extract errors and warnings from build output."""
        errors = []
        warnings = []
        for line in build_output.split("\n"):
            if "error:" in line.lower() or "FAILURE" in line:
                errors.append(line.strip())
            elif "warning:" in line.lower() or "w:" in line[:3]:
                warnings.append(line.strip())
        return {"errors": errors[:20], "warnings": warnings[:20]}


def main():
    parser = argparse.ArgumentParser(description="Build and test Android projects")
    parser.add_argument("--project", help="Project directory (default: cwd)")
    parser.add_argument("--module", help="Module name (e.g., androidApp)")
    parser.add_argument("--build", action="store_true", help="Build the project")
    parser.add_argument("--test", action="store_true", help="Run unit tests")
    parser.add_argument("--connected-test", action="store_true", help="Run instrumented tests")
    parser.add_argument("--install", action="store_true", help="Install on device")
    parser.add_argument("--lint", action="store_true", help="Run lint")
    parser.add_argument("--variant", default="debug", help="Build variant (default: debug)")
    parser.add_argument("--clean", action="store_true", help="Clean before building")
    parser.add_argument("--verbose", action="store_true", help="Show full output")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    builder = AndroidBuilder(project_dir=args.project)

    if args.build:
        result = builder.build(module=args.module, variant=args.variant, clean=args.clean)
    elif args.test:
        result = builder.test(module=args.module, variant=args.variant)
    elif args.connected_test:
        result = builder.connected_test(module=args.module, variant=args.variant)
    elif args.install:
        result = builder.install(module=args.module, variant=args.variant)
    elif args.lint:
        result = builder.lint(module=args.module)
    else:
        parser.print_help()
        sys.exit(1)

    if args.json:
        output = {
            "success": result["success"],
            "elapsed": result.get("elapsed", ""),
        }
        if not result["success"]:
            parsed = builder.parse_errors(result.get("stdout", "") + result.get("stderr", ""))
            output["errors"] = parsed["errors"]
            output["warnings"] = parsed["warnings"]
        print(json.dumps(output, indent=2))
    else:
        if result["success"]:
            print(f"BUILD SUCCEEDED [{result.get('elapsed', '')}]")
        else:
            print(f"BUILD FAILED [{result.get('elapsed', '')}]")
            if result.get("error"):
                print(f"Error: {result['error']}")
            else:
                parsed = builder.parse_errors(result.get("stdout", "") + result.get("stderr", ""))
                if parsed["errors"]:
                    print("\nErrors:")
                    for err in parsed["errors"][:10]:
                        print(f"  {err}")
            if args.verbose:
                print("\n--- Full Output ---")
                print(result.get("stdout", ""))
                print(result.get("stderr", ""))

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
