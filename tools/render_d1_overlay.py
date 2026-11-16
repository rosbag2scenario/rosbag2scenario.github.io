"""Keep the submitted D1 composition; clarify camera labels, mode and event timing.

Input must be the original anonymized submission MP4. Reuses d1-layout.ffmpeg
for camera labels and the closed row gap. No camera or BEV re-rendering.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
SOURCE_SHA = 'de98fe3d3ec9b6f275bdf79919630516592a126a35ae3a62e11761215f51d84d'


def render(source, output, timing, source_start):
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA
    motion = json.loads(timing.read_text())['d1']
    handover, event = motion['t_h'] - source_start, motion['t_d'] - source_start
    filters = []

    def box(x, y, w, h, color, enable=None, thickness='fill'):
        f = f'drawbox=x={x}:y={y}:w={w}:h={h}:color=0x{color}:t={thickness}'
        filters.append(f + (f":enable='{enable}'" if enable else ''))

    def text(value, x, y, size, color='white', enable=None, bold=False, expansion=False):
        value = value if expansion else value.replace(':', r'\:')
        f = f"drawtext=fontfile={BOLD if bold else FONT}:text='{value}':x={x}:y={y}:fontsize={size}:fontcolor={color}"
        filters.append(f + (f":enable='{enable}'" if enable else ''))

    def badge(x, mode, bg, border, enable):
        box(x, 8, 920, 48, bg, enable)
        box(x, 8, 920, 48, border, enable, 2)
        text(f'Driving mode: {mode}', x + 22, 15, 30, enable=enable, bold=True)

    # Mode replaces the title/clock strip at the top. Existing Real drive and
    # Simulation column headers immediately below identify the two badges.
    box(0, 0, 1920, 64, '0e1726')
    badge(20, 'Autonomous', '15382e', '70ed91', f'lt(t,{event:.9f})')
    badge(20, 'Manual', '7f1d1d', 'ff6b6b', f'gte(t,{event:.9f})')
    badge(980, 'Replay', '243348', 'a6b7ce', f'lt(t,{handover:.9f})')
    badge(980, 'Autonomous', '15382e', '70ed91', f'gte(t,{handover:.9f})')

    # Remove the previous footer status. Keep the clock and event time in
    # the unused legend column, above the native player's controls.
    box(0, 1026, 1920, 54, '0e1726')
    box(1435, 830, 465, 110, '17263a')
    text(r't = %{eif\:floor(t+0.05)\:d}.%{eif\:mod(floor((t+0.05)*10)\,10)\:d} s',
         1455, 847, 32, bold=True, expansion=True)
    text(f'Disengagement t_d = {event:.1f} s', 1455, 900, 23, '0xffb5b5')

    base = Path(__file__).with_name('d1-layout.ffmpeg').read_text().strip()
    graph = base.removesuffix('[out]') + '[layout];[layout]' + ','.join(filters) + '[out]'
    output.parent.mkdir(parents=True, exist_ok=True)
    filter_path = output.with_suffix('.ffmpeg')
    filter_path.write_text(graph + '\n')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source),
                    '-filter_complex_script', str(filter_path), '-map', '[out]',
                    '-an', '-c:v', 'libx264', '-threads', '4', '-preset', 'medium',
                    '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)], check=True)
    metadata = dict(source_sha256=SOURCE_SHA, source_start_s=source_start,
                    handover_source_s=motion['t_h'], disengagement_source_s=motion['t_d'],
                    handover_video_s=handover, disengagement_video_s=event,
                    displayed_disengagement_s=round(event, 1),
                    real_modes=['Autonomous', 'Manual'], simulation_modes=['Replay', 'Autonomous'],
                    mode_y=8, clock_position=[1455, 847], event_position=[1455, 900],
                    event_callout=False, real_camera_outline=False,
                    timing_unchanged=True,
                    renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    filter_sha256=hashlib.sha256(filter_path.read_bytes()).hexdigest())
    output.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--timing', type=Path, required=True)
    p.add_argument('--source-start', type=float, default=0.05000000074505806)
    a = p.parse_args()
    render(a.input, a.output, a.timing, a.source_start)
