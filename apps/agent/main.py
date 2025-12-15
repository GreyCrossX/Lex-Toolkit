from __future__ import annotations

import argparse
import json
from typing import List

from .research_graph import (
    demo_research_run,
    get_synthetic_eval_scenarios,
    run_research,
    run_synthetic_eval,
)


def demo(prompt: str) -> None:
    result = demo_research_run(prompt)
    print("[research-demo] status:", result.get("status"))
    print(
        "[research-demo] briefing overview:", result.get("briefing", {}).get("overview")
    )


def synthetic_eval() -> None:
    scenarios = get_synthetic_eval_scenarios()

    def runner(p: str):
        return run_research(p)

    results = run_synthetic_eval(runner, scenarios)
    print(json.dumps(results, indent=2, ensure_ascii=False))


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Agent utilities")
    parser.add_argument("--demo", action="store_true", help="Run demo research flow.")
    parser.add_argument(
        "--synthetic-eval",
        action="store_true",
        help="Run synthetic eval scenarios (offline).",
    )
    parser.add_argument("--prompt", type=str, help="Prompt for demo run.")
    args = parser.parse_args(argv)

    if args.synthetic_eval:
        synthetic_eval()
    else:
        prompt = (
            args.prompt
            or "Cliente indica despido injustificado en CDMX sin carta de terminación."
        )
        demo(prompt)


if __name__ == "__main__":
    main()
