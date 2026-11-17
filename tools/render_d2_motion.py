"""Render the published D2 motion data with comparable axes and fixed panel sizes."""
import argparse
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/rosbag-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

BLUE, ORANGE, GREY = '#1760dc', '#f47700', '#7c8aa0'
CASES = ('d2-hybrid', 'd2-replay')
CHARTS = (
    ('speed', 'Speed', 'Speed [m/s]', ('v_real', 'v_sim'), 'Vehicle speed on both sides.', 'speed'),
    ('position', 'Along-path position difference', 'Simulation − recording [m]', ('ds',), 'Positive: simulated ego ahead.', 'position'),
    ('command', 'Commanded acceleration', 'Acceleration [m/s²]', ('a_cmd_real', 'a_cmd_sim'), 'Acceleration requested by each stack.', 'acceleration'),
    ('achieved', 'Achieved acceleration', 'Acceleration [m/s²]', ('a_real', 'a_sim'), 'Smoothed rate of change of speed.', 'acceleration'),
)


def render(site, preview=None):
    data = json.loads((site / 'data/encounter-motion.json').read_text())
    xlim = [min(data[k]['window'][0] for k in CASES), max(data[k]['window'][1] for k in CASES)]
    xticks = np.arange(np.ceil(xlim[0] / 2) * 2, xlim[1] + 1e-9, 2)
    pooled = {}
    for case in CASES:
        series = data[case]['series']
        t = np.asarray(series['t'], float)
        mask = (t >= xlim[0]) & (t <= xlim[1])
        for _, _, _, fields, _, group in CHARTS:
            for field in fields:
                values = np.asarray(series[field], float)[mask]
                pooled.setdefault(group, []).extend(values[np.isfinite(values)])
    scales = {}
    for group, values in pooled.items():
        lo, hi = min(0., min(values)), max(0., max(values))
        pad = max(.08, (hi - lo) * .1)
        ticks = MaxNLocator(nbins=6).tick_values(lo - pad, hi + pad)
        scales[group] = ([float(ticks[0]), float(ticks[-1])], ticks)

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'svg.fonttype': 'none',
                         'svg.hashsalt': 'rosbag-motion', 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.spines.left': False, 'axes.spines.bottom': False})

    def draw(ax, case, chart):
        _, title, unit, fields, caption, group = chart
        d = data[case]
        colors = (ORANGE,) if len(fields) == 1 else (BLUE, ORANGE)
        for field, color in zip(fields, colors):
            ax.plot(d['series']['t'], np.asarray(d['series'][field], float), color=color, lw=1.65)
        ylim, yticks = scales[group]
        ax.set_xticks(xticks)
        ax.set_yticks(yticks)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_xlabel('Time in the recording [s]')
        ax.set_ylabel(unit)
        ax.set_title(title, loc='left', fontweight='bold', pad=28)
        ax.text(0, 1.07, caption, transform=ax.transAxes, color='#57657a', fontsize=10)
        ax.grid(axis='y', color='#e5eaf1')
        ax.set_axisbelow(True)
        ax.tick_params(axis='both', length=0, pad=6, labelcolor='#526078')
        for when, label in [(d['t_h'], 'handover'), (d['t_d'], 'takeover')]:
            ax.axvline(when, color=GREY, lw=1, ls='--')
            ax.text(when + .08, .96, label, transform=ax.get_xaxis_transform(), color='#58657b', fontsize=9, va='top')

    dest = site / 'fig/motion'
    for case in CASES:
        for chart in CHARTS:
            fig = plt.figure(figsize=(6.4, 3.8))
            ax = fig.add_axes([.15, .20, .81, .57])
            draw(ax, case, chart)
            metadata = dict(case=case, group=chart[-1], xlim=list(ax.get_xlim()), ylim=list(ax.get_ylim()),
                            xticks=list(ax.get_xticks()), yticks=list(ax.get_yticks()),
                            axes_position=list(ax.get_position().bounds), figure_inches=list(fig.get_size_inches()))
            path = dest / f'{case}-{chart[0]}.svg'
            fig.savefig(path, metadata={'Date': None, 'Creator': 'Rosbag2Scenario', 'Description': json.dumps(metadata)})
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()) + '\n')
            plt.close(fig)
    if preview:
        fig, axes = plt.subplots(2, 4, figsize=(23, 8), dpi=100)
        for case, row in zip(CASES, axes):
            for chart, ax in zip(CHARTS, row):
                draw(ax, case, chart)
        fig.suptitle('D2 hybrid traffic (top) and log replay (bottom) — matching scales', fontsize=16)
        fig.subplots_adjust(left=.045, right=.985, bottom=.08, top=.85, hspace=.75, wspace=.3)
        fig.savefig(preview)
        plt.close(fig)
    print('D2 shared limits:', {k: v[0] for k, v in scales.items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--preview', type=Path)
    args = parser.parse_args()
    render(args.site, args.preview)
