# Rosbag2Scenario project page

Static anonymous research supplement for the submitted eight-page manuscript.
Preview with `python3 tools/serve.py` at http://127.0.0.1:8765. The server
supports byte-range requests for video seeking. No build step, tracking or
third-party requests are required.

- `index.html`, `style.css`, `site.js`: concise pipeline, early D2 comparison
  with an enlarged synchronized player, published results, an expandable
  gap gallery, temporal ambiguity and digital-twin inspection.
- `data/gaps.json`: 111 benchmark cases and four real-gap illustrations.
- `data/support.json`: observed ambiguity fragments, four map overlays and
  the paper's empty-road commands, speed and drift series.
- `data/reconstruction-settings.json`: verified configuration and code hashes
  for the D1/D6/D7 real-gap recipe.
- `media/`: exact anonymized D1 submission video; newly composed six-camera
  simulation/BEV videos for the existing D2 pair and D3/D6/D7/D8; Town10 capture.
- `tools/`: explicit-input export/render utilities and validation.

The D1 presentation rerun is distinguished from the paper's scored run.
Paper figures and results follow the submitted version. No manuscript files
were changed and no new simulator experiments were performed.

Run `python3 tools/validate_site.py` for asset and evidence checks. With
Playwright Chromium installed and the preview running, run
`node tools/browser_qa.cjs`. `PLAYWRIGHT_PACKAGE` may point to an existing
installation. Checks cover all 115 gaps, gallery selection, map and command
views, temporal context, enlarged/inline synchronized playback, keyboard input,
mobile widths and the no-JavaScript fallback. Screenshots go to `/tmp`.

`tools/export_gaps.py`, `tools/export_support.py` and `tools/export_settings.py`
take `--workspace PATH`. The settings exporter compares archived code versions
and reads configuration; it never executes the archived implementation.
`tools/render_simulation.py` takes explicit archived run/video/map paths.
The D2 pair must use identical `--bounds` to preserve comparable map extents.
Rendering reuses archived frames; it does not execute a simulator.
The simulation-only clips use recorded R markers without cone shading. The page retains the
author-requested 90° total-opening wording; recorded metadata remains intact.
The supplied D1 video and all event labels are unchanged.

GitHub Pages serves the root of `main` in
`rosbag2scenario/rosbag2scenario.github.io`. The public site is
https://rosbag2scenario.github.io/. Commits retain the anonymous author identity.

The gap explorer shows coordinated XY, speed and motion-heading plots. Heading
is derived from neighboring local positions; low-speed values are omitted and
angle-wrap crossings are broken. It is not vehicle body yaw. The introductory
schematic precedes the examples; configuration details remain expandable.
