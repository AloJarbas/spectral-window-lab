# Repo-ready prompt: add an off-bin leakage demo that teaches something real

## Goal

Deepen `spectral-window-lab` with one focused artifact pass that shows what happens when a tone lands between DFT bins.

The repo already explains window tradeoffs in terms of ENBW, main-lobe width, and sidelobes. This pass should add the missing amplitude-honesty angle: **scalloping loss**.

## Constraints

- keep the repo pure Python standard library
- do not add NumPy, SciPy, or plotting dependencies
- keep the first pass to the four existing baseline windows: rectangular, Hann, Hamming, Blackman
- do not cram the new story into the current SVGs if that hurts readability
- prefer one or two clean new artifacts over a huge combined chart

## What to build

1. Add `scalloping_loss_db(window)` to `windowlab/metrics.py`.
2. Add a helper that computes coherent-gain-normalized response versus fractional bin offset over `0.0 .. 0.5` bins.
3. Add a dedicated script or gallery path that generates an SVG such as `art/window-offset-loss.svg`.
4. Add a second artifact that shows the normalized spectrum of a single tone placed exactly halfway between bins under each window, e.g. `art/window-half-bin-leakage.svg`.
5. Update the metrics CSV or add a compact sidecar CSV so scalloping loss becomes a first-class reported metric.
6. Add a short README/note paragraph that says:
   - leakage is unavoidable for off-bin tones,
   - windows redistribute leakage,
   - scalloping loss measures worst-case amplitude loss between bins.

## Recommended plot shape

### Artifact 1: amplitude vs bin offset

- x-axis: fractional bin offset from `0.0` to `0.5`
- y-axis: normalized amplitude error in dB
- one line per window
- keep 0 dB at exact bin center
- make the half-bin endpoint visually obvious

### Artifact 2: half-bin leakage spectrum

- synthesize one complex tone at `k + 0.5` bins for a moderate `k`
- apply each window
- compute a dense zero-padded spectrum or direct evaluation
- normalize each curve by coherent gain so the off-bin sag is honest
- show only a local span around the tone rather than the whole Nyquist range

## Useful ordering facts to test

Add tests that check at least the following at a fixed window length:

1. rectangular has the worst scalloping loss among the current windows
2. blackman has the lowest scalloping loss among the current windows
3. rectangular still has the narrowest main lobe
4. blackman still has the largest ENBW among the current windows
5. scalloping loss is approximately 3.92 dB for rectangular and roughly 1.1 to 1.4 dB for Blackman/Hann at length 129

## Design note

Do not introduce flat-top in the first implementation pass.

First make the off-bin problem visible using the existing four windows.
Then, if the result is clear, a second pass can add flat-top explicitly as the amplitude-measurement specialist with a warning about ENBW and resolution cost.

## Acceptance criteria

- `python3 scripts/make_gallery.py` still succeeds if touched
- `python3 -m unittest discover -s tests` succeeds
- at least one new SVG artifact is generated and committed under `art/`
- scalloping loss appears somewhere durable: CSV, note, or README
- the prose explains that scalloping loss and sidelobe suppression are related but not identical concerns

## Optional second pass

If there is time after the first pass works, add Kaiser (`beta=8.6`) to the amplitude-vs-offset figure once the Kaiser implementation already exists.
