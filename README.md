# Rosbag2Scenario project page

Static anonymous research supplement for the submitted eight-page manuscript.
Preview with `python3 tools/serve.py` at http://127.0.0.1:8765. The server
supports byte-range requests for video seeking. No build step, tracking or
third-party requests are required.

- `index.html`, `style.css`, `site.js`: concise pipeline, early D2 comparison
  in one side-by-side video with native playback and fullscreen, published results, an expandable
  gap gallery, temporal ambiguity and digital-twin inspection.
- `data/gaps.json`: 111 benchmark cases and four real-gap illustrations.
- `data/association.json`: the archived 2 s / 5 s × 5 m / 10 m association sweep,
  with link counts, metric definitions and source hashes. Export with
  `tools/export_association.py --study PATH --output data/association.json`.
- `data/support.json`: observed ambiguity fragments, four map overlays and
  the paper's empty-road commands, speed and drift series.
- `data/reconstruction-settings.json`: verified configuration and code hashes
  for the D1/D6/D7 real-gap recipe.
- `media/`: anonymized D1 submission video with readable camera labels and a closed row gap; newly composed six-camera
  simulation/BEV videos for the existing D2 pair and D3/D6/D7/D8; Town10 capture.
- `fig/motion/`, `data/encounter-motion.json`: four matching motion plots for
  each encounter run, including both D2 variants.
- `tools/`: explicit-input export/render utilities and validation.

Source distinctions, including the D1 presentation rerun, are recorded in
`data/README.txt` and media provenance.
Paper figures and results follow the submitted version. No manuscript files
were changed and no new simulator experiments were performed.

Run `python3 tools/validate_site.py` for asset and evidence checks. With
Playwright Chromium installed and the preview running, run
`node tools/browser_qa.cjs`. `PLAYWRIGHT_PACKAGE` may point to an existing
installation. Checks cover all 115 gaps, gallery selection, map and command
views, temporal context, native video playback/seeking/fullscreen,
mobile widths and the no-JavaScript fallback. Screenshots go to `/tmp`.

`tools/export_gaps.py`, `tools/export_support.py` and `tools/export_settings.py`
take `--workspace PATH`. The settings exporter compares archived code versions
and reads configuration; it never executes the archived implementation.
`tools/render_standard_sim.py` takes an archived run, Lanelet2 map and output
path. It uses the unchanged `draw_bev` and `sample` functions from the usual
submission renderer, preserved in `tools/standard_bev.py`. D2 uses reciprocal
`--paired-run` arguments for identical ego-centered bounds at every frame.
Rendering reuses archived frames; it does not execute a simulator.
The simulation-only clips use recorded R markers and a rear-cone overlay. The page retains the
author-requested 90° total-opening wording; recorded metadata remains intact.
The D1 clip retains the supplied real/SIM/BEV composition and timing. Its camera
labels are enlarged and the 10-pixel camera-row gap is removed. The FFmpeg filter
is saved in `tools/d1-layout.ffmpeg`; apply it to the original submission video
with `-filter_complex_script tools/d1-layout.ffmpeg -map '[out]'`.
All event labels are unchanged.

GitHub Pages serves the root of `main` in
`rosbag2scenario/rosbag2scenario.github.io`. The public site is
https://rosbag2scenario.github.io/. Commits retain the anonymous author identity.

The gap explorer shows coordinated XY, speed and motion-heading plots. Heading
is derived from neighboring local positions; low-speed values are omitted and
angle-wrap crossings are broken. It is not vehicle body yaw. The introductory
schematic precedes the examples; configuration details remain expandable.

`tools/compose_comparison.py` joins two standard exports (`--left`, `--right`,
`--output`) into one native-player comparison, checking all source times and
BEV bounds. Each side retains six cameras, the full standard BEV panel and
its legend. D3 uses the requested H2v2AL5SSXPG4G run AWE-20261111-115708.
`tools/export_encounter_plots.py` exports speed, along-path position difference,
commanded acceleration and achieved acceleration from saved comparisons.
D1 uses a comparison extracted from the exact submitted video's run.
Map views show the whole encounter. Gap and command plots have no time
slider; the ambiguity view retains its temporal inspection control.
