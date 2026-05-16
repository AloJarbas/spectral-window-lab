# Spectral Window Lab

Window functions are one of those tiny choices that quietly decide whether your spectrum looks honest or flattering.

This repo puts a few common windows side by side with code you can read in one sitting. The point is not to dump textbook prose. The point is to make the tradeoffs visible:

- narrower main lobes buy frequency resolution
- lower sidelobes buy leakage control
- wider equivalent noise bandwidth is the bill that shows up later

Everything here is pure Python standard library. No NumPy, no plotting stack, no hidden notebook state in the analysis itself.

## Included

- `windowlab/windows.py` builds rectangular, Hann, Hamming, Blackman, Kaiser (`beta=8.6`), Blackman-Harris, Nuttall, and flat-top windows
- `windowlab/metrics.py` computes coherent gain, ENBW, main-lobe width, and peak sidelobe level
- `windowlab/overlap.py` measures periodic overlap-add profiles and flatness for STFT framing hops
- `windowlab/svg.py` renders clean SVG comparison plots without external plotting libraries
- `scripts/make_gallery.py` regenerates the figures and metrics CSVs
- `notebooks/overlap_add_and_stft_framing.ipynb` is the slower companion for the new STFT framing sidecar
- `tests/test_windows.py` checks a few useful ordering facts about the windows and the new overlap-add lane

## Generated artifacts

### Time-domain window shapes

![Window shapes](art/window-shapes.png)

### Spectral tradeoffs near DC

![Window spectra](art/window-spectra.png)

### Amplitude loss versus bin offset

![Amplitude loss versus bin offset](art/window-offset-loss.png)

### Half-bin leakage near the peak

![Half-bin tone leakage](art/window-half-bin-leakage.png)

### Flat-top versus compact amplitude-friendly windows

![Amplitude specialist summary](art/window-amplitude-specialist-summary.png)

This new sidecar figure makes the tradeoff blunt: flat-top almost kills scalloping loss, but it pays for that with much higher ENBW and a much wider main lobe.

### Deep-sidelobe specialists versus amplitude specialists

![Specialist tradeoffs](art/window-specialist-tradeoffs.png)

Blackman-Harris and Nuttall deserve a place here, but not because they secretly replace flat-top. They are the deep-sidelobe branch: much cleaner far-out leakage, modestly better between-bin amplitude honesty, and still a lot more compact than flat-top on ENBW.

### Kaiser beta sweep

![Kaiser beta sweep](art/window-kaiser-beta-sweep.png)

This sweep turns Kaiser from a single named checkpoint into a real family. `beta` is the knob: push it up and ENBW rises, the main lobe widens, and sidelobes fall.

### Overlap-add flatness for common STFT hops

![Overlap-add flatness](art/window-overlap-add-flatness.png)

This sidecar is the repo's first framing pass. A window can look fine in a one-shot FFT and still demand a smaller STFT hop before its overlap-add sum stops wavering.

The generated CSVs in `art/window-metrics.csv`, `art/window-specialist-metrics.csv`, `art/kaiser-beta-sweep.csv`, and `art/window-overlap-add-metrics.csv` now give compact numeric summaries for the named windows, the specialist sidecar, the Kaiser family sweep, and the new overlap-add pass.

## Quick run

```bash
python3 scripts/make_gallery.py
python3 -m unittest discover -s tests
```

On macOS, `scripts/make_gallery.py` also exports matching 300 dpi PNG previews for the generated SVG figures so the README can use GitHub-friendly raster previews without changing the underlying SVG source artifacts.

## Why this deserves its own repo

Because window choice is not a side detail.

It changes what you think you measured.

This repo is small, but it has a real spine: code, generated artifacts, tests, and now a clearer amplitude-specialist story instead of a pile of unnamed curves.

The new Kaiser sweep matters because it replaces folklore like "Kaiser is kind of like Blackman" with an actual path you can inspect.

The Blackman-Harris / Nuttall sidecar matters for a different reason: it keeps the repo from teaching the lazy idea that every low-sidelobe window is basically the same thing with different branding.

The overlap-add sidecar matters because it brings STFT framing into the same conversation. Flat overlap is not the same thing as low leakage, and flat-top turns out to be expensive on both fronts.

## Notes

- [Flat-top is the amplitude specialist, not the default](notes/flattop-amplitude-specialist.md)
- [Blackman-Harris and Nuttall are deep-sidelobe specialists, not amplitude specialists](notes/blackman-harris-and-nuttall-are-deep-sidelobe-specialists.md)
- [Overlap-add flatness is a second window bill](notes/overlap-add-and-stft-framing.md)


## Next directions

- port the metrics core to Julia and Fortran for cross-language comparison once those toolchains are live
- compare the Kaiser sweep at two FFT lengths or iteration densities only if that reveals something real instead of redrawing the same curve
- add one compact window-selection map only if it sharpens real task choices instead of collapsing back into a vague window zoo

Jarbas
