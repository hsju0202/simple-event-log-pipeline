from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from html import escape
from pathlib import Path

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
CHART_BACKGROUND = "#f8fafc"
TEXT_COLOR = "#0f172a"
MUTED_TEXT_COLOR = "#475569"
GRID_COLOR = "#cbd5e1"
AXIS_COLOR = "#64748b"
BAR_COLOR = "#2563eb"
LINE_COLOR = "#0f766e"
ERROR_COLOR = "#dc2626"
SUCCESS_COLOR = "#16a34a"


def write_analysis_charts(
    analysis_results: dict[str, list[dict[str, object]]],
    *,
    output_dir: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    chart_files = [
        output_dir / "dashboard.html",
        output_dir / "event_type_counts.svg",
        output_dir / "user_event_counts.svg",
        output_dir / "hourly_event_trend.svg",
        output_dir / "error_rate.svg",
    ]

    chart_files[1].write_text(
        _build_bar_chart_svg(
            title="Event Type Counts",
            subtitle="SQL aggregate: count by event_type",
            labels=[str(row["event_type"]) for row in analysis_results["event_type_counts"]],
            values=[int(row["event_count"]) for row in analysis_results["event_type_counts"]],
            x_axis_label="Event Type",
            y_axis_label="Events",
        ),
        encoding="utf-8",
    )
    chart_files[2].write_text(
        _build_horizontal_bar_chart_svg(
            title="Top Users By Event Count",
            subtitle="Top 10 rows from SQL aggregate grouped by user_id",
            labels=[f"User {int(row['user_id'])}" for row in analysis_results["user_event_counts"][:10]],
            values=[int(row["event_count"]) for row in analysis_results["user_event_counts"][:10]],
            x_axis_label="Events",
        ),
        encoding="utf-8",
    )
    chart_files[3].write_text(
        _build_line_chart_svg(
            title="Hourly Event Trend",
            subtitle="SQL aggregate: count by hour",
            labels=[_format_hour_label(row["hour"]) for row in analysis_results["hourly_event_trend"]],
            values=[int(row["event_count"]) for row in analysis_results["hourly_event_trend"]],
            x_axis_label="Hour",
            y_axis_label="Events",
        ),
        encoding="utf-8",
    )
    chart_files[4].write_text(
        _build_error_rate_svg(analysis_results["error_rate"]),
        encoding="utf-8",
    )
    chart_files[0].write_text(
        _build_dashboard_html(
            analysis_results=analysis_results,
            event_type_chart_path=chart_files[1].name,
            user_chart_path=chart_files[2].name,
            hourly_chart_path=chart_files[3].name,
            error_rate_chart_path=chart_files[4].name,
        ),
        encoding="utf-8",
    )

    return chart_files


def _build_dashboard_html(
    *,
    analysis_results: dict[str, list[dict[str, object]]],
    event_type_chart_path: str,
    user_chart_path: str,
    hourly_chart_path: str,
    error_rate_chart_path: str,
) -> str:
    error_rate_row = analysis_results["error_rate"][0]
    total_events = int(error_rate_row["total_events"])
    error_events = int(error_rate_row["error_events"])
    error_rate_percent = float(error_rate_row["error_rate_percent"])
    distinct_event_types = len(analysis_results["event_type_counts"])
    active_users = len(analysis_results["user_event_counts"])
    peak_hour = _find_peak_hour_label(analysis_results["hourly_event_trend"])
    top_users_rows = "".join(
        _build_table_row(
            [f"User {int(row['user_id'])}", str(int(row["event_count"]))],
        )
        for row in analysis_results["user_event_counts"][:8]
    )
    event_type_rows = "".join(
        _build_table_row(
            [str(row["event_type"]), str(int(row["event_count"]))],
        )
        for row in analysis_results["event_type_counts"]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Event Analytics Dashboard</title>
  <style>
    :root {{
      --bg: #e2e8f0;
      --panel: rgba(248, 250, 252, 0.86);
      --panel-border: rgba(148, 163, 184, 0.28);
      --text: #0f172a;
      --muted: #475569;
      --accent: #0f766e;
      --accent-2: #2563eb;
      --danger: #dc2626;
      --shadow: 0 22px 60px rgba(15, 23, 42, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(14, 165, 233, 0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(34, 197, 94, 0.16), transparent 24%),
        linear-gradient(180deg, #eff6ff 0%, #e2e8f0 100%);
    }}
    .dashboard {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.7fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .panel {{
      background: var(--panel);
      backdrop-filter: blur(10px);
      border: 1px solid var(--panel-border);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .hero-main {{
      padding: 28px;
      min-height: 230px;
      background:
        linear-gradient(135deg, rgba(15, 118, 110, 0.10), rgba(37, 99, 235, 0.12)),
        var(--panel);
    }}
    .eyebrow {{
      font-size: 12px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 12px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(34px, 4vw, 52px);
      line-height: 1;
      letter-spacing: -0.04em;
    }}
    .hero-copy {{
      margin: 16px 0 0;
      max-width: 620px;
      font-size: 16px;
      line-height: 1.6;
      color: var(--muted);
    }}
    .hero-side {{
      padding: 24px;
      display: grid;
      align-content: center;
      gap: 18px;
    }}
    .stat-label {{
      font-size: 13px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }}
    .stat-value {{
      font-size: 42px;
      font-weight: 700;
      letter-spacing: -0.05em;
    }}
    .stat-sub {{
      font-size: 14px;
      color: var(--muted);
      margin-top: 6px;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 18px;
      margin-bottom: 18px;
    }}
    .kpi {{
      padding: 22px;
      min-height: 138px;
    }}
    .kpi .value {{
      font-size: 34px;
      font-weight: 700;
      letter-spacing: -0.04em;
      margin-top: 18px;
    }}
    .kpi .meta {{
      color: var(--muted);
      font-size: 14px;
      margin-top: 8px;
      line-height: 1.5;
    }}
    .section-title {{
      margin: 0 0 4px;
      font-size: 20px;
      letter-spacing: -0.03em;
    }}
    .section-subtitle {{
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }}
    .content-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.3fr) minmax(360px, 0.7fr);
      gap: 18px;
    }}
    .chart-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 18px;
    }}
    .chart-panel, .table-panel {{
      padding: 20px;
    }}
    .chart-frame {{
      margin-top: 16px;
      border-radius: 18px;
      overflow: hidden;
      border: 1px solid rgba(148, 163, 184, 0.24);
      background: white;
    }}
    .chart-frame img {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .table-stack {{
      display: grid;
      gap: 18px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 14px;
      font-size: 14px;
    }}
    th, td {{
      text-align: left;
      padding: 12px 0;
      border-bottom: 1px solid rgba(148, 163, 184, 0.18);
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
    }}
    .danger {{
      color: var(--danger);
    }}
    @media (max-width: 1080px) {{
      .hero, .content-grid, .kpi-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main class="dashboard">
    <section class="hero">
      <article class="panel hero-main">
        <div class="eyebrow">Event Pipeline Dashboard</div>
        <h1>Operational Event Analytics</h1>
        <p class="hero-copy">
          SQL aggregate results are presented as a lightweight BI-style dashboard with KPI cards,
          trend panels, and ranked breakdowns. It is generated locally from the current pipeline run.
        </p>
      </article>
      <aside class="panel hero-side">
        <div>
          <div class="stat-label">Error Rate</div>
          <div class="stat-value danger">{error_rate_percent:.2f}%</div>
          <div class="stat-sub">{error_events} error events across {total_events} total events</div>
        </div>
        <div>
          <div class="stat-label">Peak Hour</div>
          <div class="stat-value">{escape(peak_hour)}</div>
          <div class="stat-sub">Highest hourly event volume from the SQL time bucket aggregate</div>
        </div>
      </aside>
    </section>

    <section class="kpi-grid">
      <article class="panel kpi">
        <div class="stat-label">Total Events</div>
        <div class="value">{total_events}</div>
        <div class="meta">All ingested events included in the aggregate output.</div>
      </article>
      <article class="panel kpi">
        <div class="stat-label">Active Users</div>
        <div class="value">{active_users}</div>
        <div class="meta">Distinct user rows present in the grouped SQL result.</div>
      </article>
      <article class="panel kpi">
        <div class="stat-label">Event Types</div>
        <div class="value">{distinct_event_types}</div>
        <div class="meta">Categorical breakdown of current event activity.</div>
      </article>
      <article class="panel kpi">
        <div class="stat-label">Healthy Events</div>
        <div class="value">{max(total_events - error_events, 0)}</div>
        <div class="meta">Events outside client/system error categories.</div>
      </article>
    </section>

    <section class="content-grid">
      <div class="chart-grid">
        <article class="panel chart-panel">
          <h2 class="section-title">Volume By Event Type</h2>
          <p class="section-subtitle">Distribution across page views, purchases, and error categories.</p>
          <div class="chart-frame">
            <img src="{escape(event_type_chart_path)}" alt="Event type counts chart" />
          </div>
        </article>
        <article class="panel chart-panel">
          <h2 class="section-title">Hourly Trend</h2>
          <p class="section-subtitle">Time-series view of traffic volume per SQL hour bucket.</p>
          <div class="chart-frame">
            <img src="{escape(hourly_chart_path)}" alt="Hourly event trend chart" />
          </div>
        </article>
      </div>

      <div class="table-stack">
        <article class="panel chart-panel">
          <h2 class="section-title">User Concentration</h2>
          <p class="section-subtitle">Top contributors by event volume from grouped user counts.</p>
          <div class="chart-frame">
            <img src="{escape(user_chart_path)}" alt="Top users by event count chart" />
          </div>
        </article>
        <article class="panel chart-panel">
          <h2 class="section-title">Reliability Snapshot</h2>
          <p class="section-subtitle">Error ratio view derived from the global aggregate query.</p>
          <div class="chart-frame">
            <img src="{escape(error_rate_chart_path)}" alt="Error rate chart" />
          </div>
        </article>
        <article class="panel table-panel">
          <h2 class="section-title">Top Users Table</h2>
          <p class="section-subtitle">Compact ranking for quick inspection.</p>
          <table>
            <thead>
              <tr><th>User</th><th>Events</th></tr>
            </thead>
            <tbody>{top_users_rows}</tbody>
          </table>
        </article>
        <article class="panel table-panel">
          <h2 class="section-title">Event Type Table</h2>
          <p class="section-subtitle">Raw grouped counts behind the category chart.</p>
          <table>
            <thead>
              <tr><th>Event Type</th><th>Events</th></tr>
            </thead>
            <tbody>{event_type_rows}</tbody>
          </table>
        </article>
      </div>
    </section>
  </main>
</body>
</html>
"""


def _build_bar_chart_svg(
    *,
    title: str,
    subtitle: str,
    labels: list[str],
    values: list[int],
    x_axis_label: str,
    y_axis_label: str,
) -> str:
    width = 900
    height = 560
    left = 90
    right = 40
    top = 85
    bottom = 125
    chart_width = width - left - right
    chart_height = height - top - bottom
    max_value = max(values, default=1) or 1
    step_count = min(5, max_value) if max_value > 1 else 1
    grid_values = _build_grid_values(max_value=max_value, step_count=max(step_count, 1))
    bar_count = max(len(values), 1)
    slot_width = chart_width / bar_count
    bar_width = min(84, slot_width * 0.62)

    parts = [_svg_header(width, height), _chart_shell(title=title, subtitle=subtitle, width=width, height=height)]
    parts.append(_y_axis_label(y_axis_label))
    parts.append(
        f'<text x="{width / 2:.1f}" y="{height - 22}" text-anchor="middle" '
        f'font-size="15" fill="{MUTED_TEXT_COLOR}">{escape(x_axis_label)}</text>'
    )
    parts.append(
        f'<line x1="{left}" y1="{top + chart_height}" x2="{width - right}" y2="{top + chart_height}" '
        f'stroke="{AXIS_COLOR}" stroke-width="1.5" />'
    )
    parts.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" '
        f'stroke="{AXIS_COLOR}" stroke-width="1.5" />'
    )

    for grid_value in grid_values:
        y = top + chart_height - (grid_value / max_value * chart_height)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
            f'stroke="{GRID_COLOR}" stroke-dasharray="4 4" />'
        )
        parts.append(
            f'<text x="{left - 12}" y="{y + 5:.1f}" text-anchor="end" '
            f'font-size="12" fill="{MUTED_TEXT_COLOR}">{grid_value}</text>'
        )

    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        x_center = left + slot_width * index + slot_width / 2
        bar_height = value / max_value * chart_height if max_value else 0
        x = x_center - bar_width / 2
        y = top + chart_height - bar_height
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" '
            f'rx="10" fill="{BAR_COLOR}" />'
        )
        parts.append(
            f'<text x="{x_center:.1f}" y="{y - 10:.1f}" text-anchor="middle" '
            f'font-size="12" fill="{TEXT_COLOR}">{value}</text>'
        )
        parts.append(
            f'<text x="{x_center:.1f}" y="{top + chart_height + 24:.1f}" text-anchor="middle" '
            f'font-size="12" fill="{MUTED_TEXT_COLOR}">{escape(label)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def _build_horizontal_bar_chart_svg(
    *,
    title: str,
    subtitle: str,
    labels: list[str],
    values: list[int],
    x_axis_label: str,
) -> str:
    width = 900
    row_height = 34
    left = 150
    right = 40
    top = 95
    bottom = 70
    chart_height = max(200, row_height * max(len(values), 1))
    height = top + chart_height + bottom
    chart_width = width - left - right
    max_value = max(values, default=1) or 1
    step_count = min(5, max_value) if max_value > 1 else 1
    grid_values = _build_grid_values(max_value=max_value, step_count=max(step_count, 1))

    parts = [_svg_header(width, height), _chart_shell(title=title, subtitle=subtitle, width=width, height=height)]
    parts.append(
        f'<text x="{width / 2:.1f}" y="{height - 22}" text-anchor="middle" '
        f'font-size="15" fill="{MUTED_TEXT_COLOR}">{escape(x_axis_label)}</text>'
    )
    parts.append(
        f'<line x1="{left}" y1="{top + chart_height}" x2="{width - right}" y2="{top + chart_height}" '
        f'stroke="{AXIS_COLOR}" stroke-width="1.5" />'
    )

    for grid_value in grid_values:
        x = left + grid_value / max_value * chart_width
        parts.append(
            f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + chart_height}" '
            f'stroke="{GRID_COLOR}" stroke-dasharray="4 4" />'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{top + chart_height + 24:.1f}" text-anchor="middle" '
            f'font-size="12" fill="{MUTED_TEXT_COLOR}">{grid_value}</text>'
        )

    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        y = top + index * row_height + 6
        bar_width = value / max_value * chart_width if max_value else 0
        parts.append(
            f'<text x="{left - 14}" y="{y + 16:.1f}" text-anchor="end" '
            f'font-size="12" fill="{TEXT_COLOR}">{escape(label)}</text>'
        )
        parts.append(
            f'<rect x="{left}" y="{y:.1f}" width="{bar_width:.1f}" height="20" '
            f'rx="10" fill="{BAR_COLOR}" />'
        )
        parts.append(
            f'<text x="{left + bar_width + 8:.1f}" y="{y + 16:.1f}" '
            f'font-size="12" fill="{TEXT_COLOR}">{value}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def _build_line_chart_svg(
    *,
    title: str,
    subtitle: str,
    labels: list[str],
    values: list[int],
    x_axis_label: str,
    y_axis_label: str,
) -> str:
    width = 960
    height = 560
    left = 90
    right = 40
    top = 85
    bottom = 105
    chart_width = width - left - right
    chart_height = height - top - bottom
    max_value = max(values, default=1) or 1
    step_count = min(5, max_value) if max_value > 1 else 1
    grid_values = _build_grid_values(max_value=max_value, step_count=max(step_count, 1))

    points = list(_build_line_points(values=values, left=left, top=top, chart_width=chart_width, chart_height=chart_height, max_value=max_value))
    polyline_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    parts = [_svg_header(width, height), _chart_shell(title=title, subtitle=subtitle, width=width, height=height)]
    parts.append(_y_axis_label(y_axis_label))
    parts.append(
        f'<text x="{width / 2:.1f}" y="{height - 22}" text-anchor="middle" '
        f'font-size="15" fill="{MUTED_TEXT_COLOR}">{escape(x_axis_label)}</text>'
    )
    parts.append(
        f'<line x1="{left}" y1="{top + chart_height}" x2="{width - right}" y2="{top + chart_height}" '
        f'stroke="{AXIS_COLOR}" stroke-width="1.5" />'
    )
    parts.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" '
        f'stroke="{AXIS_COLOR}" stroke-width="1.5" />'
    )

    for grid_value in grid_values:
        y = top + chart_height - (grid_value / max_value * chart_height)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
            f'stroke="{GRID_COLOR}" stroke-dasharray="4 4" />'
        )
        parts.append(
            f'<text x="{left - 12}" y="{y + 5:.1f}" text-anchor="end" '
            f'font-size="12" fill="{MUTED_TEXT_COLOR}">{grid_value}</text>'
        )

    if polyline_points:
        parts.append(
            f'<polyline fill="none" stroke="{LINE_COLOR}" stroke-width="3" '
            f'stroke-linecap="round" stroke-linejoin="round" points="{polyline_points}" />'
        )

    for x, y in points:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{LINE_COLOR}" />')

    label_step = max(1, len(labels) // 8)
    for index, label in enumerate(labels):
        if index % label_step != 0 and index != len(labels) - 1:
            continue
        x = points[index][0] if points else left
        parts.append(
            f'<text x="{x:.1f}" y="{top + chart_height + 24:.1f}" text-anchor="middle" '
            f'font-size="11" fill="{MUTED_TEXT_COLOR}">{escape(label)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def _build_error_rate_svg(error_rate_rows: list[dict[str, object]]) -> str:
    row = error_rate_rows[0]
    total_events = int(row["total_events"])
    error_events = int(row["error_events"])
    error_rate = float(row["error_rate_percent"])
    safe_events = max(total_events - error_events, 0)
    error_width = 720 * (error_rate / 100)
    success_width = 720 - error_width

    parts = [_svg_header(900, 380), _chart_shell(title="Error Rate", subtitle="SQL aggregate over all events", width=900, height=380)]
    parts.append(
        f'<text x="70" y="150" font-size="60" font-weight="700" fill="{ERROR_COLOR}">{error_rate:.2f}%</text>'
    )
    parts.append(
        f'<text x="70" y="184" font-size="16" fill="{MUTED_TEXT_COLOR}">Errors among total events</text>'
    )
    parts.append(
        f'<rect x="70" y="220" width="720" height="28" rx="14" fill="{SUCCESS_COLOR}" opacity="0.22" />'
    )
    parts.append(
        f'<rect x="70" y="220" width="{error_width:.1f}" height="28" rx="14" fill="{ERROR_COLOR}" />'
    )
    parts.append(
        f'<text x="70" y="285" font-size="15" fill="{TEXT_COLOR}">Error events: {error_events}</text>'
    )
    parts.append(
        f'<text x="260" y="285" font-size="15" fill="{TEXT_COLOR}">Non-error events: {safe_events}</text>'
    )
    parts.append(
        f'<text x="500" y="285" font-size="15" fill="{TEXT_COLOR}">Total events: {total_events}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _build_line_points(
    *,
    values: Iterable[int],
    left: float,
    top: float,
    chart_width: float,
    chart_height: float,
    max_value: int,
) -> Iterable[tuple[float, float]]:
    value_list = list(values)
    if not value_list:
        return []
    if len(value_list) == 1:
        return [(left + chart_width / 2, top + chart_height - value_list[0] / max_value * chart_height)]

    step = chart_width / (len(value_list) - 1)
    return [
        (
            left + step * index,
            top + chart_height - value / max_value * chart_height,
        )
        for index, value in enumerate(value_list)
    ]


def _build_grid_values(*, max_value: int, step_count: int) -> list[int]:
    if max_value <= 0:
        return [0]
    return sorted({round(max_value * step / step_count) for step in range(step_count + 1)})


def _find_peak_hour_label(hourly_event_trend_rows: list[dict[str, object]]) -> str:
    if not hourly_event_trend_rows:
        return "-"
    peak_row = max(hourly_event_trend_rows, key=lambda row: int(row["event_count"]))
    return _format_hour_label(peak_row["hour"])


def _build_table_row(cells: list[str]) -> str:
    escaped_cells = "".join(f"<td>{escape(cell)}</td>" for cell in cells)
    return f"<tr>{escaped_cells}</tr>"


def _format_hour_label(value: object) -> str:
    if isinstance(value, datetime):
        return value.strftime("%m-%d %H:00")
    return str(value)


def _svg_header(width: int, height: int) -> str:
    return (
        f'<svg xmlns="{SVG_NAMESPACE}" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" fill="none">'
    )


def _chart_shell(*, title: str, subtitle: str, width: int, height: int) -> str:
    return (
        f'<rect width="{width}" height="{height}" rx="24" fill="{CHART_BACKGROUND}" />'
        f'<text x="40" y="48" font-size="28" font-weight="700" fill="{TEXT_COLOR}">{escape(title)}</text>'
        f'<text x="40" y="72" font-size="15" fill="{MUTED_TEXT_COLOR}">{escape(subtitle)}</text>'
    )


def _y_axis_label(label: str) -> str:
    return (
        f'<text x="28" y="290" text-anchor="middle" transform="rotate(-90 28 290)" '
        f'font-size="15" fill="{MUTED_TEXT_COLOR}">{escape(label)}</text>'
    )
