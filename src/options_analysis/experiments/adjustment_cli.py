"""Run with python -m options_analysis.experiments.adjustment_cli."""

import argparse
from pathlib import Path

from pydantic import ValidationError

from options_analysis.experiments.adjustment_report import render_adjustment_report
from options_analysis.experiments.adjustments import (
    AdjustmentComparisonRequest,
    compare_adjustments,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare hold, close, and explicit adjustment trades locally."
    )
    parser.add_argument("input", type=Path, help="comparison input JSON")
    parser.add_argument("--output-dir", type=Path, default=Path("comparison-output"))
    args = parser.parse_args()
    try:
        request = AdjustmentComparisonRequest.model_validate_json(
            args.input.read_text(encoding="utf-8")
        )
        result = compare_adjustments(request)
        html = render_adjustment_report(result)
    except (OSError, ValueError, ValidationError) as error:
        parser.error(str(error))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "comparison.json").write_text(
        result.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    report = args.output_dir / "report.html"
    report.write_text(html, encoding="utf-8")
    print(f"Report: {report.resolve()}")
    print(f"JSON: {(args.output_dir / 'comparison.json').resolve()}")


if __name__ == "__main__":
    main()
