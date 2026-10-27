"""Keep the published result table and conclusions tied to metrics.csv."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "own-project"
REPORT = ROOT / "Итоговый отчет.md"
TABLE_HEADER = (
    "| Метод | Шагов за период | Макс. ошибка положения | Макс. дрейф энергии | "
    "Время, мс | Память, KiB |"
)
CONCLUSIONS_HEADER = "### Выводы по результатам"
SOURCE_LINE = re.compile(
    r"Проверенный commit кода и тестов: \[[0-9a-f]{40}\]"
    r"\(https://github\.com/st115592/ML_task_zero/commit/[0-9a-f]{40}\)\. "
    r"SHA-256 кода симулятора: `[0-9a-f]{64}`."
)


def _inputs(root: Path):
    project = root / "own-project"
    with (project / "results" / "metrics.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    metadata = json.loads(
        (project / "results" / "metadata.json").read_text(encoding="utf-8")
    )
    return rows, metadata


def _table(rows: list[dict[str, str]]) -> str:
    lines = [
        TABLE_HEADER,
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        time_ms = float(row["median_runtime_s"]) * 1000
        time_text = f"{time_ms:.3f}" if time_ms < 1 else f"{time_ms:.2f}"
        memory_kib = int(row["peak_traced_memory_bytes"]) / 1024
        lines.append(
            f"| {row['method']} | {row['steps_per_orbit']} | "
            f"{float(row['max_relative_position_error']):.3g} | "
            f"{float(row['max_relative_energy_drift']):.3g} | "
            f"{time_text} | {memory_kib:.1f} |"
        )
    return "\n".join(lines)


def _conclusions(rows: list[dict[str, str]]) -> str:
    indexed = {(row["method"], int(row["steps_per_orbit"])): row for row in rows}
    steps = sorted({int(row["steps_per_orbit"]) for row in rows})
    lo, hi = steps[0], steps[-1]
    rk4_lo, rk4_hi = indexed[("rk4", lo)], indexed[("rk4", hi)]
    vv_lo, vv_hi = indexed[("verlet", lo)], indexed[("verlet", hi)]
    euler, rk4, verlet = (
        indexed[("euler", hi)],
        indexed[("rk4", hi)],
        indexed[("verlet", hi)],
    )
    rk4_gain = float(rk4_lo["max_relative_position_error"]) / float(
        rk4_hi["max_relative_position_error"]
    )
    vv_gain = float(vv_lo["max_relative_position_error"]) / float(
        vv_hi["max_relative_position_error"]
    )
    factors = hi / lo
    times = {
        key: float(row["median_runtime_s"]) * 1000
        for key, row in (("rk4", rk4), ("verlet", verlet), ("euler", euler))
    }
    return "\n".join(
        [
            CONCLUSIONS_HEADER,
            "",
            f"- При увеличении числа шагов с {lo} до {hi} (в {factors:.0f} раза) "
            f"ошибка положения RK4 уменьшилась примерно в {rk4_gain:.3g} раза "
            "— это согласуется с четвёртым порядком метода.",
            f"- Для velocity Verlet ошибка положения уменьшилась примерно в "
            f"{vv_gain:.3g} раза. При {hi} шагах максимальный дрейф энергии "
            f"составил {float(verlet['max_relative_energy_drift']):.3g}, "
            f"момента импульса — "
            f"{float(verlet['max_relative_angular_momentum_drift']):.3g}.",
            f"- Явный Эйлер при {hi} шагах дал ошибку положения "
            f"{float(euler['max_relative_position_error']):.3g} начального радиуса "
            f"и дрейф энергии {float(euler['max_relative_energy_drift']):.3g}; "
            "на выбранных шагах точности недостаточно.",
            f"- При {hi} шагах медианное время составило "
            f"{times['rk4']:.2f} мс для RK4, {times['verlet']:.3f} мс для Verlet "
            f"и {times['euler']:.3f} мс для Эйлера. Это короткие замеры на одной "
            "платформе, а не универсальный рейтинг производительности.",
            "- В этой круговой двухтельной задаче RK4 дал наименьшую ошибку "
            "траектории, а Verlet хорошо сохранил инварианты. Вывод ограничен "
            "одним периодом и идеализированной моделью.",
        ]
    )


def render(root: Path = ROOT) -> str:
    rows, metadata = _inputs(root)
    code = (root / "own-project" / "orbit_sim.py").read_text(encoding="utf-8")
    checksum = hashlib.sha256(code.encode("utf-8")).hexdigest()
    if metadata.get("source_sha256") != checksum:
        raise ValueError("metadata source_sha256 does not match orbit_sim.py")
    commit = metadata.get("source_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("metadata source_commit must be a 40-character Git SHA")

    report = (root / "Итоговый отчет.md").read_text(encoding="utf-8")
    table_start = report.index(TABLE_HEADER)
    conclusions_start = report.index(CONCLUSIONS_HEADER, table_start)
    report = report[:table_start] + _table(rows) + "\n\n" + report[conclusions_start:]
    conclusions_start = report.index(CONCLUSIONS_HEADER)
    source_start = report.index("Исходная таблица —", conclusions_start)
    report = (
        report[:conclusions_start] + _conclusions(rows) + "\n\n" + report[source_start:]
    )
    source_line = (
        f"Проверенный commit кода и тестов: [{commit}]"
        f"(https://github.com/st115592/ML_task_zero/commit/{commit}). "
        f"SHA-256 кода симулятора: `{checksum}`."
    )
    report, count = SOURCE_LINE.subn(source_line, report)
    if count != 1:
        raise ValueError("report must contain exactly one source/checksum line")
    return report


def validate(root: Path = ROOT) -> list[str]:
    try:
        expected = render(root)
        actual = (root / "Итоговый отчет.md").read_text(encoding="utf-8")
    except (OSError, KeyError, ValueError, json.JSONDecodeError, csv.Error) as exc:
        return [str(exc)]
    return (
        []
        if actual == expected
        else ["report table/conclusions are stale; run python report_tools.py --write"]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="regenerate table and conclusions from metrics.csv",
    )
    args = parser.parse_args()
    if args.write:
        (ROOT / "Итоговый отчет.md").write_text(render(ROOT), encoding="utf-8")
    errors = validate()
    if errors:
        print("Report check failed: " + "; ".join(errors), file=sys.stderr)
        return 1
    print("Report table, conclusions and source checksum match saved results.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
