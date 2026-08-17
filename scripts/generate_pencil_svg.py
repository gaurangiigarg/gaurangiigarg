
#!/usr/bin/env python3
"""
Fetches a GitHub user's real contribution calendar and generates an
animated SVG where a pencil "draws" each cell of the grid, using the
same colors/levels GitHub itself assigns (contributionLevel).

Env vars required:
  GITHUB_TOKEN   - token with read access to the user's contributions
                   (the default Actions token works for the user's own repo)
  GITHUB_LOGIN   - the username whose contributions to fetch
                   (defaults to the repo owner in Actions)

Output:
  pencil-contribution.svg  (written to the repo root, or OUT_PATH if set)
"""

import os
import sys
import json
import urllib.request

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_LOGIN = os.environ.get("GITHUB_LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER")
OUT_PATH = os.environ.get("OUT_PATH", "pencil-contribution.svg")

if not GITHUB_TOKEN or not GITHUB_LOGIN:
    print("GITHUB_TOKEN and GITHUB_LOGIN (or GITHUB_REPOSITORY_OWNER) must be set", file=sys.stderr)
    sys.exit(1)

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""

LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

COLORS = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]


def fetch_calendar(login: str, token: str):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.loads(resp.read())
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return weeks


def build_svg(weeks):
    
    cols = len(weeks)
    rows = 7
    cell = 11
    gap = 2
    step = cell + gap
    margin_left = 24
    margin_top = 24

  
    cells = []  
    for c, week in enumerate(weeks):
        for day in week["contributionDays"]:
            level = LEVEL_MAP.get(day["contributionLevel"], 0)
            cells.append((c, day, level))

    n = len(cells)
    step_time = max(0.015, min(0.05, 8.0 / n))  
    draw_dur = n * step_time
    pause_dur = 2.0
    total = draw_dur + pause_dur

    width = margin_left * 2 + cols * step - gap
    height = margin_top * 2 + rows * step - gap

    svg_parts = []
    svg_parts.append(
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="Segoe UI, Helvetica, Arial, sans-serif">'
    )

    points = []
    idx = 0
    for c, day, level in cells:
        row = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].index(
            __import__("datetime").datetime.strptime(day["date"], "%Y-%m-%d").strftime("%a")
        )
        x = margin_left + c * step
        y = margin_top + row * step
        cx, cy = x + cell / 2, y + cell / 2
        points.append((cx, cy))

        color = COLORS[level]
        key_time = round((idx * step_time) / total, 6)
        svg_parts.append(
            f'  <rect x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="2" '
            f'fill="{COLORS[0]}">'
            f'<animate attributeName="fill" calcMode="discrete" '
            f'values="{COLORS[0]};{color}" keyTimes="0;{key_time}" '
            f'dur="{total:.3f}s" begin="0s" repeatCount="indefinite"/></rect>'
        )
        idx += 1

    # pencil motion path
    path_d = f"M {points[0][0]:.1f} {points[0][1]:.1f} "
    for px, py in points[1:]:
        path_d += f"L {px:.1f} {py:.1f} "
    off_x, off_y = width + 30, points[-1][1]
    path_d += f"L {off_x:.1f} {off_y:.1f} "

    key_times_motion = [round((i * step_time) / total, 6) for i in range(n)]
    key_times_motion.append(round(draw_dur / total, 6))
    key_times_motion.append(1.0)

    pencil = f'''
  <g id="pencil">
    <animateMotion path="{path_d.strip()}" keyTimes="{';'.join(str(k) for k in key_times_motion)}"
      dur="{total:.3f}s" begin="0s" repeatCount="indefinite" calcMode="linear"/>
    <g transform="rotate(-40) translate(-4,-16)">
      <rect x="-3" y="0" width="6" height="16" rx="1.5" fill="#f2c14e" stroke="#b8860b" stroke-width="0.5"/>
      <polygon points="-3,0 3,0 0,-7" fill="#e8b04b"/>
      <polygon points="-1,-4.5 1,-4.5 0,-7" fill="#5a4632"/>
      <rect x="-3" y="14" width="6" height="4" rx="1" fill="#e07a5f"/>
    </g>
  </g>'''
    svg_parts.append(pencil)
    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def main():
    weeks = fetch_calendar(GITHUB_LOGIN, GITHUB_TOKEN)
    svg = build_svg(weeks)
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
