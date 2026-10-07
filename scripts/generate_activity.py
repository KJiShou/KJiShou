"""Generate activity SVGs from GitHub data without third-party image services."""

import json
import subprocess
from datetime import date
from html import escape
from pathlib import Path

QUERY = '''query {
  user(login: "KJiShou") {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}'''


def fetch_days():
    response = subprocess.run(
        ['gh', 'api', 'graphql', '-f', 'query=' + QUERY],
        capture_output=True, text=True, check=True,
    )
    payload = json.loads(response.stdout)
    if payload.get('errors'):
        raise RuntimeError('GitHub query failed; keeping previous graphs')
    calendar = payload['data']['user']['contributionsCollection']['contributionCalendar']
    days = sorted(
        (day for week in calendar['weeks'] for day in week['contributionDays']),
        key=lambda day: day['date'],
    )[-31:]
    if len(days) != 31:
        raise ValueError('Expected 31 contribution days')
    for day in days:
        date.fromisoformat(day['date'])
        if not isinstance(day['contributionCount'], int) or day['contributionCount'] < 0:
            raise ValueError('Invalid contribution count')
    return days


def render(days, dark):
    bg, ink, muted, grid = (
        ('#0d1117', '#e6edf3', '#8b949e', '#30363d') if dark
        else ('#ffffff', '#1f2328', '#59636e', '#d1d9e0')
    )
    accent = '#38bdf8' if dark else '#0969da'
    total = sum(day['contributionCount'] for day in days)
    active = sum(day['contributionCount'] > 0 for day in days)
    ceiling = max(4, ((max(day['contributionCount'] for day in days) + 3) // 4) * 4)
    points = [(64 + i * 872 / 30, 246 - day['contributionCount'] * 140 / ceiling) for i, day in enumerate(days)]
    coords = ' '.join(f'{x:.2f},{y:.2f}' for x, y in points)
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="320" viewBox="0 0 1000 320" role="img" aria-labelledby="title description">',
        '<title id="title">KJiShou — GitHub Activity</title>',
        f'<desc id="description">{total} contributions on {active} active days, {days[0]["date"]} to {days[-1]["date"]}.</desc>',
        f'<rect x="1" y="1" width="998" height="318" rx="16" fill="{bg}" stroke="{grid}"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
        f'<text x="32" y="38" fill="{ink}" font-size="21" font-weight="700">GitHub Activity</text>',
        f'<text x="32" y="65" fill="{muted}" font-size="14">Last 31 days · {total:,} contributions · {active} active days</text>',
    ]
    for step in range(5):
        y = 106 + 35 * step
        svg.extend([
            f'<line x1="64" y1="{y}" x2="936" y2="{y}" stroke="{grid}"/>',
            f'<text x="52" y="{y + 4}" text-anchor="end" fill="{muted}" font-size="12">{ceiling * (4 - step) // 4}</text>',
        ])
    svg.extend([
        f'<polygon points="64,246 {coords} 936,246" fill="{accent}" opacity="0.12"/>',
        f'<polyline points="{coords}" fill="none" stroke="{accent}" stroke-width="2.5" stroke-linejoin="round"/>',
    ])
    for (x, y), day in zip(points, days):
        tooltip = escape(f'{day["date"]}: {day["contributionCount"]} contributions')
        svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{accent}"><title>{tooltip}</title></circle>')
    for index in [0, 5, 10, 15, 20, 25, 30]:
        label = date.fromisoformat(days[index]['date']).strftime('%d %b')
        svg.append(f'<text x="{points[index][0]:.2f}" y="272" text-anchor="middle" fill="{muted}" font-size="12">{label}</text>')
    svg.append(f'<text x="32" y="301" fill="{muted}" font-size="12">Source: GitHub contribution calendar · Through {days[-1]["date"]}</text>')
    return '\n'.join(svg + ['</g></svg>']) + '\n'


def main():
    days = fetch_days()
    assets = Path(__file__).resolve().parents[1] / 'assets'
    assets.mkdir(exist_ok=True)
    for theme in ['dark', 'light']:
        (assets / f'activity-{theme}.svg').write_text(render(days, theme == 'dark'), encoding='utf-8')
    print(f'Generated charts through {days[-1]["date"]}')


if __name__ == '__main__':
    main()
