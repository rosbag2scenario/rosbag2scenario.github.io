Rosbag2Scenario — supplementary material for the submitted manuscript

This supplement follows the submitted eight-page manuscript, not a later draft.
Tables II and III are transcribed without changing the numerical results or
reclassifying any event. No new simulator runs were made for this website.

GAP EXPLORER
111 scored natural tracker gaps from the three Town10 evaluation drives.
One identity-unscorable natural pair is excluded, as in the evaluation.
The completion comparison supplies the correct fragment pair to each method.
This differs from association, which must decide which fragments to join.
Per-gap RMSE is in meters; Table II pools squared errors across timestamps.
The summary uses 3296 ground-truth timestamps. The moving subset has 56 gaps.
Motion is classified from ground-truth speed: nearly stationary below 0.3 m/s
at the 90th percentile, moving at least 1 m/s. Each drive is 180 s with 40
traffic vehicles; seeds are 101, 202, 303 and the first 5 s are excluded.

The four displayed benchmark methods correspond to Table II. In particular,
the Zhu-inspired curve is the lane-aware implementation, with Cartesian
Hermite fallback where a lane bridge is unavailable. For the web export its
coordinates were recovered using the archived function and every per-sample
error was checked against the saved result. This is a rendering/export step,
not a new experimental condition. Existing stored predictions are used for
constant velocity, raw Hermite and our method. No new ablation is added.

For display, each gap is translated and rotated into local coordinates.
This preserves physical distances and removes absolute locations. The
benchmark JSON contains 111 cases; the four real examples follow them.
XY points and times are rounded to five decimals for compact delivery; RMSE
values retain their archived precision. Displayed method speed is estimated
by finite differences; observed speed comes from the tracker. Case T001 etc.
are stable export identifiers, not new driving recordings.

REAL-RECORDING EXAMPLES
Four illustrative gaps explain continuity across observed fragments:
D7's 3.1 s example from the paper, a longer D7 gap, a curved D1 trajectory,
and a short moving-vehicle gap from D6. They are chosen for explanation, not
as an accuracy ranking. There is no ground truth inside these real gaps.
Ours is the stored exported trajectory. Constant velocity, Hermite and the
Cartesian Zhu-inspired method are archived alternative completions. The
benchmark uses the lane-aware Zhu-inspired configuration from Table II. The full quantitative benchmark is provided
separately, including cases where ours is not the lowest-error method.

The ambiguity figure is a D7 association example. Its global assignment
margin is 0.77; the method leaves the connection unjoined at margin <= 1.

MEDIA
D1 uses the exact anonymized submission video supplied by the author, including
real cameras, simulation and the author-supplied rear-cone/R overlay. The
file is copied byte-for-byte. D1 is a presentation rerun with an ambulance
proxy for the blocking truck, separate from the scored Table III run.

The D2 hybrid/log-replay pair and D3/D6/D7/D8 are rendered anew from their existing
raw camera mosaics and simulator states. Only simulation camera pixels are
included in these views. Six cameras and BEV use exact matching CARLA
frame IDs. Every available actor is included, without a 50 m scoring filter.
The two D2 runs share source times 0.05 to 22.15 s and the same map extent.
R markers follow actual release transitions. These clips are presented without
cone shading; archived run parameters remain in the provenance. BEVs are geometry visualizations,
not overhead camera images. These exports do not change any trajectories.

MAP, COMMANDS AND TEMPORAL CONTEXT
The D7 ambiguity timeline uses actual adjacent observation timestamps and
up to three seconds of each fragment. Dashed connections are hypotheses,
not inferred vehicle motion. A shared cursor shows observations over time.

Map overlays use the configured corrected Lanelet2 projection, the archived
CARLA lane-center samples and recorded/simulated ego paths. Archived CARLA
samples are converted from the audit's recording frame back to native
OpenDRIVE XY. No additional fitted transform is applied for this display.
Native CARLA y is negated into right-handed XY. Coordinates are translated
locally. Boundaries and centerlines are labelled separately.

The motion views use the existing empty-road run behind the paper's ego-drift
figure: scenario times 9–24 s, handover at 14 s. Control-message stamps are
aligned using the recorded simulator clock origin; commanded acceleration
and steering are published requests, not inferred actuator responses.
The 20 Hz deviation and speed samples are the archived paper-figure data.

The Town10 video shows one of the three evaluation captures. Its redetection
counter belongs to that recording; it is not a count of recovered links.

REGENERATION
See tools/export_gaps.py, tools/export_support.py, tools/export_settings.py and
tools/render_simulation.py. They take explicit
local input paths and do not need to be run to view this static site.
Source hashes and definitions are in gap-provenance.json and
media-provenance.json; supporting-source hashes are in support.json. Private recordings, raw logs and local filesystem
paths are not included in the web bundle. The pipeline code release remains
planned upon acceptance, as stated on the project page.

RECONSTRUCTION RECIPE
The compact settings table uses saved configurations for the D1, D6 and D7
real-gap illustrations. These configurations specify identical source,
association and completion settings. The relevant association, pipeline,
motion and observation-model files are byte-identical at their recorded code
versions (D1 cd8a986; D6/D7 3d50a1b). The exporter verifies this before saving
configuration hashes and motion defaults in reconstruction-settings.json.

HEADING DISPLAY
The browser estimates direction of motion from the secant through neighboring
local XY samples (one-sided at endpoints). Zero degrees is the along-gap axis.
Angles stay in [-180, 180] degrees, with lines and interpolation broken at
wrap crossings. Values are omitted if either the displayed speed or the
position-derived secant speed is below 0.5 m/s. This is a display convention
for unstable low-speed directions, not an evaluation or acceptance threshold.
It is neither tracker box yaw nor a new heading-accuracy measurement.

ADDITIONAL CASE VIDEOS
D3 AWE-20261110-195922, D6 AWE-20261110-201649 and D8 AWE-20261110-203002
match the archived Table III coverage/within-2m rows. Each contains 171
matching camera/state frames. Only the simulation half is extracted.

D2 COMBINED PLAYER
The two aligned D2 exports are composed side by side into a single 1920x900,
22.2 s video. All 222 frames are retained; each side has six cameras and the
complete BEV with matching map bounds. Camera pixels retain their resolution;
the BEV is resized proportionally. Duplicate legends are replaced by one
shared legend and source-relative clock. Input hashes and complete render
provenance remain nested under d2-comparison.inputs in media-provenance.json.
No browser synchronization, custom timeline or custom fullscreen UI is used.
