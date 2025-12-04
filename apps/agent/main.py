from __future__ import annotations

from .research_graph import demo_research_run


def main() -> None:
    prompt = "Cliente indica despido injustificado en CDMX sin carta de terminación."
    result = demo_research_run(prompt)
    print("[research-demo] status:", result.get("status"))
    print("[research-demo] briefing overview:", result.get("briefing", {}).get("overview"))


if __name__ == "__main__":
    main()
