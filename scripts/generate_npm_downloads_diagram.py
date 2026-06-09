from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_PACKAGE = "lumynax-marama-route"
NPM_REGISTRY = "https://registry.npmjs.org"
NPM_DOWNLOADS = "https://api.npmjs.org"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an npm downloads SVG for README pages.")
    parser.add_argument("--package", default=DEFAULT_PACKAGE)
    parser.add_argument("--output", type=Path, default=Path("docs/marama-route-npm-downloads.svg"))
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--today", default="", help="Override end date in YYYY-MM-DD format.")
    args = parser.parse_args()

    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(dt.UTC).date()
    data = collect_download_data(args.package, today=today)
    svg = render_svg(data)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8", newline="\n")
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {args.output}")
    return 0


def collect_download_data(package: str, *, today: dt.date) -> dict[str, Any]:
    escaped = urllib.parse.quote(package, safe="@")
    packument = _get_json(f"{NPM_REGISTRY}/{escaped}")
    times = packument.get("time", {})
    versions = [
        {"version": version, "published": times.get(version, "")}
        for version in packument.get("versions", {})
        if version in times
    ]
    versions.sort(key=lambda item: item["published"])
    if not versions:
        raise RuntimeError(f"No published versions found for {package}")

    first_day = _date_from_iso(str(versions[0]["published"]))
    range_payload = _get_json(f"{NPM_DOWNLOADS}/downloads/range/{first_day.isoformat()}:{today.isoformat()}/{escaped}")
    daily = [
        {"day": str(row["day"]), "downloads": int(row.get("downloads") or 0)}
        for row in range_payload.get("downloads", [])
    ]
    monthly: dict[str, int] = {}
    for row in daily:
        month = row["day"][:7]
        monthly[month] = monthly.get(month, 0) + row["downloads"]

    version_payload = _get_json(f"{NPM_DOWNLOADS}/versions/{escaped}/last-week")
    last_week = {str(key): int(value or 0) for key, value in version_payload.get("downloads", {}).items()}
    for item in versions:
        item["last_week_downloads"] = last_week.get(str(item["version"]), 0)
        item["published_day"] = _date_from_iso(str(item["published"])).isoformat()

    return {
        "package": package,
        "generated_at": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "first_publish_day": first_day.isoformat(),
        "last_day": today.isoformat(),
        "total_downloads": sum(row["downloads"] for row in daily),
        "last_week_version_downloads": sum(item["last_week_downloads"] for item in versions),
        "monthly": [{"month": month, "downloads": downloads} for month, downloads in sorted(monthly.items())],
        "versions": versions,
        "notes": [
            "npm exposes package downloads by day/range.",
            "npm exposes per-version download counts for the previous 7 days only.",
            "The chart therefore shows monthly package totals plus current per-version last-week split.",
        ],
    }


def render_svg(data: dict[str, Any]) -> str:
    width = 1180
    height = 760
    margin = 34
    left_x = 56
    left_y = 198
    left_w = 470
    left_h = 300
    right_x = 580
    right_y = 198
    right_w = 540
    row_h = 21

    monthly = data["monthly"]
    versions = data["versions"]
    max_month = max([item["downloads"] for item in monthly] or [1])
    max_version = max([item["last_week_downloads"] for item in versions] or [1])
    version_area_h = min(490, max(240, len(versions) * row_h + 42))
    note_y = max(left_y + left_h + 44, right_y + version_area_h + 24)
    height = max(height, note_y + 92)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        "<title id=\"title\">npm download history for lumynax-marama-route</title>",
        "<desc id=\"desc\">Monthly package downloads since first publish and last-week per-version download split.</desc>",
        "<style>",
        "text{font-family:Inter,Segoe UI,Arial,sans-serif;fill:#17202a}",
        ".muted{fill:#5c6670}.tiny{font-size:11px}.small{font-size:13px}.label{font-size:14px;font-weight:650}.title{font-size:28px;font-weight:800}",
        ".panel{fill:#ffffff;stroke:#d9e1e8;stroke-width:1}.grid{stroke:#e8edf2;stroke-width:1}.axis{stroke:#9aa8b5;stroke-width:1}",
        ".bar{fill:#e08a2c}.bar2{fill:#2f6f88}.chip{fill:#f6f8fa;stroke:#d9e1e8;stroke-width:1}.note{fill:#fff8eb;stroke:#e8c07a;stroke-width:1}",
        "</style>",
        '<rect x="0" y="0" width="1180" height="' + str(height) + '" fill="#f7f9fb"/>',
        f'<rect x="{margin}" y="26" width="{width - margin * 2}" height="{height - 52}" rx="14" class="panel"/>',
        f'<text x="{left_x}" y="70" class="title">{_esc(data["package"])} npm downloads</text>',
        f'<text x="{left_x}" y="98" class="muted small">Monthly package totals since first publish, with all released versions shown together in the last-7-days split.</text>',
    ]

    chips = [
        ("first publish", data["first_publish_day"]),
        ("total downloads", _fmt_int(data["total_downloads"])),
        ("versions", str(len(versions))),
        ("version split", f'{_fmt_int(data["last_week_version_downloads"])} last 7d'),
    ]
    chip_x = left_x
    for label, value in chips:
        chip_w = 128 + len(str(value)) * 7
        parts.append(f'<rect x="{chip_x}" y="116" width="{chip_w}" height="32" rx="7" class="chip"/>')
        parts.append(f'<text x="{chip_x + 12}" y="136" class="tiny muted">{_esc(label)}</text>')
        parts.append(f'<text x="{chip_x + 12}" y="144" class="tiny">{_esc(str(value))}</text>')
        chip_x += chip_w + 10

    parts.extend(
        [
            f'<text x="{left_x}" y="{left_y - 28}" class="label">Downloads by month</text>',
            f'<rect x="{left_x}" y="{left_y}" width="{left_w}" height="{left_h}" rx="10" fill="#fbfcfd" stroke="#d9e1e8"/>',
        ],
    )
    for i in range(5):
        y = left_y + 24 + i * ((left_h - 62) / 4)
        value = max_month - round(i * max_month / 4)
        parts.append(f'<line x1="{left_x + 48}" y1="{y:.1f}" x2="{left_x + left_w - 24}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{left_x + 12}" y="{y + 4:.1f}" class="tiny muted">{_fmt_int(value)}</text>')
    chart_x = left_x + 58
    chart_y = left_y + 24
    chart_w = left_w - 92
    chart_h = left_h - 72
    bar_gap = 20
    bar_w = max(34, (chart_w - max(0, len(monthly) - 1) * bar_gap) / max(1, len(monthly)))
    for idx, item in enumerate(monthly):
        value = int(item["downloads"])
        bar_h = 0 if max_month == 0 else chart_h * value / max_month
        x = chart_x + idx * (bar_w + bar_gap)
        y = chart_y + chart_h - bar_h
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="5" class="bar"/>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{y - 7:.1f}" text-anchor="middle" class="tiny">{_fmt_int(value)}</text>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{left_y + left_h - 24}" text-anchor="middle" class="tiny muted">{_esc(item["month"])}</text>')
    parts.append(f'<line x1="{chart_x}" y1="{chart_y + chart_h}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h}" class="axis"/>')

    parts.extend(
        [
            f'<text x="{right_x}" y="{right_y - 28}" class="label">All versions: downloads in the last 7 days</text>',
            f'<rect x="{right_x}" y="{right_y}" width="{right_w}" height="{version_area_h}" rx="10" fill="#fbfcfd" stroke="#d9e1e8"/>',
        ],
    )
    bar_x = right_x + 152
    bar_max_w = right_w - 224
    row_y = right_y + 30
    for idx, item in enumerate(versions):
        y = row_y + idx * row_h
        value = int(item["last_week_downloads"])
        bar_w_v = 0 if max_version == 0 else max(2 if value else 0, bar_max_w * value / max_version)
        parts.append(f'<text x="{right_x + 16}" y="{y + 4}" class="tiny">{_esc(item["version"])}</text>')
        parts.append(f'<text x="{right_x + 84}" y="{y + 4}" class="tiny muted">{_esc(item["published_day"][5:])}</text>')
        if value:
            parts.append(f'<rect x="{bar_x}" y="{y - 9}" width="{bar_w_v:.1f}" height="12" rx="3" class="bar2"/>')
        else:
            parts.append(f'<circle cx="{bar_x + 2}" cy="{y - 3}" r="2" fill="#9aa8b5"/>')
        parts.append(f'<text x="{bar_x + bar_max_w + 12}" y="{y + 4}" class="tiny">{_fmt_int(value)}</text>')

    parts.extend(
        [
            f'<rect x="{left_x}" y="{note_y}" width="{width - left_x * 2}" height="58" rx="10" class="note"/>',
            f'<text x="{left_x + 18}" y="{note_y + 24}" class="small">npm publishes monthly/daily totals for the package and per-version counts for the previous 7 days only.</text>',
            f'<text x="{left_x + 18}" y="{note_y + 44}" class="tiny muted">Generated {data["generated_at"]}. Sources: api.npmjs.org downloads range and versions last-week endpoints.</text>',
        ],
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _get_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "marama-route-download-diagram/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _date_from_iso(value: str) -> dt.date:
    if not value:
        raise ValueError("missing ISO date")
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def _fmt_int(value: int) -> str:
    return f"{value:,}"


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


if __name__ == "__main__":
    raise SystemExit(main())
