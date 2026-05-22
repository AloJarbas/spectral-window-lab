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
- `windowlab/overlap.py` measures both raw and squared overlap profiles, plus the implied synthesis-normalization swing for STFT framing hops
- `windowlab/reconstruct.py` adds a same-window normalized overlap-add reconstruction path, explicit dual-window helpers, conditioning summaries, and a small coefficient-noise simulation so the framing lane can talk about exactness versus numerical calmness instead of only flatness
- `windowlab/recommend.py` turns the repo's existing metrics into a bounded task-selection map instead of a fake one-size-fits-all ranking
- `windowlab/svg.py` renders clean SVG comparison plots without external plotting libraries
- `scripts/make_gallery.py` regenerates the figures and metrics CSVs
- `notebooks/overlap_add_and_stft_framing.ipynb` is the slower companion for the STFT framing sidecar
- `notebooks/synthesis_normalization_and_weighted_overlap.ipynb` is the companion notebook for the weighted overlap-add sidecar
- `notebooks/reconstruction_conditioning_and_normalized_overlap_add.ipynb` slows down the new exactness-versus-conditioning pass
- `notebooks/dual_window_synthesis_tradeoffs.ipynb` slows down the new canonical-dual versus constant-looking-dual comparison
- `notebooks/window_selection_map.ipynb` slows down the task-selection map and the guardrails behind it
- `tests/test_windows.py` checks useful ordering facts about the windows, the overlap-add lane, the new reconstruction-conditioning pass, the dual-window sidecar, and the task map

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

### Raw overlap versus synthesis normalization

![Raw overlap versus synthesis normalization](art/window-synthesis-normalization-bill.png)

This second framing sidecar is the sharper follow-up. Quarter-hop framing can already look calm on the raw overlap sum while the squared overlap still forces a visibly phase-dependent synthesis gain. That turns out to be a real difference between Hann/Hamming and the heavier deep-sidelobe or amplitude-specialist windows.

### Same-window reconstruction conditioning after normalization

![Reconstruction conditioning](art/window-reconstruction-conditioning.png)

This new sidecar closes one more loophole in the framing story. Same-window normalized overlap-add can be exact in algebra and still be a bad conditioning choice if the squared-overlap denominator develops deep troughs. Half-overlap is rough for Blackman-Harris, Nuttall, and especially flat-top; quarter-hop already makes almost everything calm except flat-top; one-eighth hop flattens the whole set again.

### Canonical dual versus constant-looking dual

![Dual-window comparison](art/window-dual-window-comparison.png)

This follow-up makes the next framing split explicit. In this repo's bounded periodic setting, normalized same-window synthesis already gives the canonical dual. The real comparison is therefore against the closest constant-looking dual. That dual can look much flatter, but it still spends more energy and usually amplifies more coefficient noise.

### Task-based window selection map

![Task-based window selection map](art/window-selection-map.png)

This sidecar is the repo's explicit decision card. Instead of pretending one window is "best," it uses guardrails plus the existing metrics to say different things for different jobs: rectangular for very tight equal-strength tone separation, Kaiser `β=8.6` for a compact low-sidelobe compromise, Nuttall for weak-spur hunting, flat-top for isolated-tone amplitude honesty, and Hamming for the repo's bounded quarter-hop STFT lane.

The generated CSVs in `art/window-metrics.csv`, `art/window-specialist-metrics.csv`, `art/kaiser-beta-sweep.csv`, `art/window-overlap-add-metrics.csv`, `art/window-synthesis-normalization-metrics.csv`, `art/window-reconstruction-conditioning.csv`, `art/window-dual-window-comparison.csv`, and `art/window-selection-map.csv` now give compact numeric summaries for the named windows, the specialist sidecar, the Kaiser family sweep, the raw overlap-add pass, the synthesis-normalization pass, the reconstruction-conditioning pass, the new dual-window comparison, and the task map.

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

The new synthesis-normalization sidecar matters because it closes the loophole inside the framing story: a raw overlap sum can look almost flat while the squared overlap still implies a real weighted overlap-add gain swing. That keeps the repo from quietly teaching that one overlap metric is enough.

The new reconstruction-conditioning sidecar matters because it splits two ideas that get blurred together all the time: exact overlap-add reconstruction and a calm overlap-add reconstruction path. A positive denominator is enough for the algebra. It is not enough to guarantee that tiny frame-domain error will stay tiny after normalization.

The new dual-window sidecar matters because it closes the next loophole honestly instead of theatrically. In this bounded setting, normalized same-window synthesis already *is* the canonical dual, so the interesting comparison is against a flatter, more COLA-looking dual. That dual reconstructs exactly too, but it does not make the noise bill disappear. For the ugly cases, the canonical dual stays calmer and shrinking hop is still the cleaner fix.

The task-selection sidecar matters for a different reason: it forces the repo to stop hiding behind generic advice like "Hann is a good default." The winners are different because the tasks are different, and now the repo has one compact artifact that makes that visible.

## Notes

- [Flat-top is the amplitude specialist, not the default](notes/flattop-amplitude-specialist.md)
- [Blackman-Harris and Nuttall are deep-sidelobe specialists, not amplitude specialists](notes/blackman-harris-and-nuttall-are-deep-sidelobe-specialists.md)
- [Overlap-add flatness is a second window bill](notes/overlap-add-and-stft-framing.md)
- [Raw overlap flatness is not the synthesis rule](notes/raw-overlap-is-not-the-synthesis-rule.md)
- [Exact overlap-add reconstruction is not the conditioning story](notes/exact-overlap-add-is-not-the-conditioning-story.md)
- [Dual windows are real, but flatter duals are not free](notes/dual-windows-do-not-make-conditioning-free.md)
- [Why dual windows were the next honest framing split](notes/dual-window-next-pass.md)
- [A bounded window-selection map for actual tasks](notes/window-selection-map.md)


## Next directions

- compare the canonical dual against one second desired synthesis target only if it changes the story instead of dressing up the same noise tradeoff in a new costume
- port the metrics core to Julia and Fortran for cross-language comparison once those toolchains are live
- compare the Kaiser sweep at two FFT lengths or iteration densities only if that reveals something real instead of redrawing the same curve

Jarbas
