"""Launch the unified Aadi voice and gesture command center."""

from aadi_ai.runtime import RuntimeOptions, run_command_center


def main() -> int:
    return run_command_center(RuntimeOptions(speak=True))


if __name__ == "__main__":
    raise SystemExit(main())
