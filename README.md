# Spectral Window Lab

Window functions are one of those tiny choices that quietly decide whether your spectrum looks honest or flattering.

This repo puts a few common windows side by side with code you can read in one sitting. The point is not to dump textbook prose. The point is to make the tradeoffs visible:

- narrower main lobes buy frequency resolution
- lower sidelobes buy leakage control
- wider equivalent noise bandwidth is the bill that shows up later

Everything here is pure Python standard library. No NumPy, no plotting stack, no hidden notebook state in the analysis itself.

## Included

- `windowlab/windows.py` builds rectangular, Hann, Hamming, Blackman, Kaiser (`beta=8.6`), Blackman-Harris, the repo's current Nuttall alias, an explicit minimum-4-term-BH Nuttall, a continuous-derivative Nuttall, and flat-top windows
- `windowlab/metrics.py` computes coherent gain, ENBW, main-lobe width, and peak sidelobe level
- `windowlab/overlap.py` measures both raw and squared overlap profiles, plus the implied synthesis-normalization swing for STFT framing hops
- `windowlab/reconstruct.py` adds a same-window normalized overlap-add reconstruction path, explicit dual-window helpers, conditioning summaries, and a small coefficient-noise simulation so the framing lane can talk about exactness versus numerical calmness instead of only flatness
- `windowlab/dual_path.py` studies the whole exact path between the canonical dual and the constant-looking dual instead of pretending the framing tradeoff only lives at two endpoints
- `windowlab/kaiser_density.py` audits how much of the Kaiser family sweep is actually stable under coarse versus dense FFT sampling instead of pretending every plotted spectrum metric is equally settled
- `windowlab/specialist_density.py` checks whether the same FFT-density warning survives contact with Blackman-Harris and Nuttall instead of assuming one deep-sidelobe family story
- `windowlab/amplitude_density.py` checks the narrower amplitude-specialist question: whether a coarse sampled FFT peak quietly puts a real amplitude error back into the flat-top lane
- `windowlab/peak_interpolation.py` follows that amplitude lane one step farther by asking whether a tiny 3-point peak interpolator changes the practical ranking between flat-top and more compact windows
- `windowlab/nuttall_variants.py` splits the repo's old bare `nuttall` label into two explicit coefficient families so first-sidelobe depth and far-out decay stop getting flattened into one ranking
- `windowlab/recommend.py` turns the repo's existing metrics into a bounded task-selection map instead of a fake one-size-fits-all ranking
- `windowlab/svg.py` renders clean SVG comparison plots without external plotting libraries
- `scripts/make_gallery.py` regenerates the figures and metrics CSVs
- `notebooks/overlap_add_and_stft_framing.ipynb` is the slower companion for the STFT framing sidecar
- `notebooks/synthesis_normalization_and_weighted_overlap.ipynb` is the companion notebook for the weighted overlap-add sidecar
- `notebooks/reconstruction_conditioning_and_normalized_overlap_add.ipynb` slows down the new exactness-versus-conditioning pass
- `notebooks/dual_window_synthesis_tradeoffs.ipynb` slows down the new canonical-dual versus constant-looking-dual comparison
- `notebooks/dual_window_tradeoff_paths.ipynb` slows down the new exact-dual interpolation follow-up and the midpoint tradeoff question
- `notebooks/kaiser_fft_density_audit.ipynb` slows down the new coarse-versus-dense FFT audit for the Kaiser family
- `notebooks/specialist_fft_density_audit.ipynb` slows down the new family-specific FFT-density follow-up for Blackman-Harris and Nuttall
- `notebooks/amplitude_fft_density_audit.ipynb` slows down the new sampled-peak amplitude-bias follow-up for Blackman, Blackman-Harris, and flat-top
- `notebooks/peak_interpolation_amplitude_audit.ipynb` slows down the new 3-point interpolation follow-up and the split between sampled peaks, linear parabolas, and log parabolas
- `notebooks/nuttall_variant_split.ipynb` slows down the new first-sidelobe-versus-far-tail split inside the Nuttall family
- `notebooks/window_selection_map.ipynb` slows down the task-selection map and the guardrails behind it
- `tests/test_windows.py` checks useful ordering facts about the windows, the overlap-add lane, the reconstruction-conditioning pass, the dual-window sidecars, and the task map

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

### Kaiser FFT-density audit

![Kaiser FFT-density audit](art/window-kaiser-fft-density-audit.png)

This follow-up is the numerical honesty check for the sweep. For higher `beta`, a coarse FFT probe can make Kaiser look cleaner and broader than a denser probe actually supports, even though direct-sum metrics like ENBW and scalloping do not move at all.

### Deep-sidelobe FFT-density family audit

![Deep-sidelobe FFT-density family audit](art/window-specialist-fft-density-audit.png)

This next pass keeps the FFT-density warning from turning into a fake universal rule. Blackman-Harris is almost grid-stable on the same probe ladder. Nuttall is not. It lands in the useful middle: the sidelobe read settles fairly quickly, but the width read stays soft longer because the first sampled null can jump to the wrong place.

### Amplitude-specialist FFT-density audit

![Amplitude-specialist FFT-density audit](art/window-amplitude-fft-density-audit.png)

This follow-up closes the amplitude-side loophole left open by the task map. A coarse sampled FFT peak still underreads Blackman and Blackman-Harris by visible tenths of a dB, but flat-top stays essentially level on the same grid. Its real bill is still width and ENBW, not a hidden coarse-grid amplitude trap.

### Peak interpolation audit

![Peak interpolation audit](art/window-peak-interpolation-audit.png)

This follow-up asks the next amplitude question after the sampled-peak audit. Flat-top still wins when you want the sampled peak itself to be honest. But if you allow one tiny 3-point log-parabola around the peak, Blackman-Harris becomes a serious compact amplitude option instead of an automatic loser.

### Nuttall variant split

![Nuttall variant split](art/window-nuttall-variant-split.png)

This follow-up closes the naming loophole inside that same branch. The repo's current `nuttall` really is strong on first-sidelobe depth, but the continuous-derivative variant wins the far tail, so the word `Nuttall` is not precise enough once the lesson shifts from peak sidelobes to weak spurs farther away.

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

### Dual-window tradeoff paths

![Dual-window tradeoff paths](art/window-dual-tradeoff-paths.png)

This follow-up is the sharper dual-window question. The old sidecar only compared two exact duals: the calm canonical one and the flattest constant-looking one. This one traces the whole exact path between them. That makes the real split visible: some windows have a usable middle lane where flatness improves faster than noise, while others stay hostile no matter how you retune the synthesis window.

### Task-based window selection map

![Task-based window selection map](art/window-selection-map.png)

This sidecar is the repo's explicit decision card. Instead of pretending one window is "best," it uses guardrails plus the existing metrics to say different things for different jobs: rectangular for very tight equal-strength tone separation, Kaiser `β=8.6` for a compact low-sidelobe compromise, Nuttall min-4-term BH for weak spurs close to a strong line, Nuttall continuous for weaker farther-out spurs, flat-top for isolated-tone amplitude honesty, and Hamming for the repo's bounded quarter-hop STFT lane.

The generated CSVs in `art/window-metrics.csv`, `art/window-specialist-metrics.csv`, `art/kaiser-beta-sweep.csv`, `art/window-kaiser-fft-density-audit.csv`, `art/window-specialist-fft-density-audit.csv`, `art/window-amplitude-fft-density-audit.csv`, `art/window-peak-interpolation-audit.csv`, `art/window-nuttall-variant-split.csv`, `art/window-overlap-add-metrics.csv`, `art/window-synthesis-normalization-metrics.csv`, `art/window-reconstruction-conditioning.csv`, `art/window-dual-window-comparison.csv`, `art/window-dual-tradeoff-paths.csv`, and `art/window-selection-map.csv` now give compact numeric summaries for the named windows, the specialist sidecar, the Kaiser family sweep, the three FFT-density audits, the new peak-interpolation amplitude split, the Nuttall-variant split, the raw overlap-add pass, the synthesis-normalization pass, the reconstruction-conditioning pass, the endpoint dual-window comparison, the new exact-dual path follow-up, and the task map.

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

The new FFT-density audit matters because it keeps the repo from quietly teaching that every plotted spectrum metric is equally settled. For higher `beta`, the Kaiser window itself does not change, but a coarse FFT probe can still over-credit its sidelobe suppression and overstate its main-lobe width. That is a numerical-measurement lesson, not a window-family lesson, and the repo is stronger for making that split explicit.

The new deep-sidelobe family audit matters because it keeps that warning from hardening into the wrong folklore. Blackman-Harris and Nuttall are both deep-sidelobe windows, but they do not share one FFT-grid sensitivity story. Blackman-Harris stays almost locked to the sampled grid here; Nuttall leaves a softer middle case where the sidelobe read settles sooner than the width read.

The Blackman-Harris / Nuttall sidecar matters for a different reason: it keeps the repo from teaching the lazy idea that every low-sidelobe window is basically the same thing with different branding.

The new Nuttall naming note matters because it closes a quieter loophole inside that same branch: `Nuttall` is not one universally fixed coefficient set in practice. The current repo implementation matches the minimum-4-term-Blackman-Harris variant, which really does push the first sidelobe very low. Some practical tables use a different continuous-derivative variant under the same label, and that one tells a different far-out-decay story.

The new Nuttall-variant sidecar matters because it turns that warning into an actual measured split instead of leaving it as a footnote. The minimum-4-term-BH branch still wins the first-sidelobe contest. The continuous variant wins the deeper far tail. That makes the repo's next weak-spur or sidelobe-falloff lesson much safer because the coefficient family is finally explicit.

The overlap-add sidecar matters because it brings STFT framing into the same conversation. Flat overlap is not the same thing as low leakage, and flat-top turns out to be expensive on both fronts.

The new synthesis-normalization sidecar matters because it closes the loophole inside the framing story: a raw overlap sum can look almost flat while the squared overlap still implies a real weighted overlap-add gain swing. That keeps the repo from quietly teaching that one overlap metric is enough.

The new reconstruction-conditioning sidecar matters because it splits two ideas that get blurred together all the time: exact overlap-add reconstruction and a calm overlap-add reconstruction path. A positive denominator is enough for the algebra. It is not enough to guarantee that tiny frame-domain error will stay tiny after normalization.

The new dual-window sidecar matters because it closes the next loophole honestly instead of theatrically. In this bounded setting, normalized same-window synthesis already *is* the canonical dual, so the interesting comparison is against a flatter, more COLA-looking dual. That dual reconstructs exactly too, but it does not make the noise bill disappear. For the ugly cases, the canonical dual stays calmer and shrinking hop is still the cleaner fix.

The new dual-path follow-up matters because it turns that binary comparison into a real design question. Once both endpoints are exact, the honest question is whether there is a usable middle lane between them. For Hann and especially Blackman-Harris at quarter-hop, there is. For flat-top at half-overlap, there really is not.

The task-selection sidecar matters for a different reason: it forces the repo to stop hiding behind generic advice like "Hann is a good default." The winners are different because the tasks are different, and now the repo has one compact artifact that makes that visible. The new far-spur follow-up makes one sharper point inside the old deep-sidelobe lane too: the first-sidelobe winner and the far-tail winner are not always the same window.

The new amplitude-density sidecar matters because it closes the loophole on the other side of the map. It is easy to say flat-top is the amplitude specialist and still leave open the practical objection that a coarse sampled FFT peak might quietly put a real amplitude error back into the read. In this bounded audit, that objection does not survive. Flat-top stays almost perfectly level on the same sampled-peak ladder where Blackman and Blackman-Harris still visibly underread.

The new peak-interpolation sidecar matters because it stops that result from hardening into the wrong next folklore. Flat-top still owns the no-extra-work lane. But once a 3-point log parabola is allowed, Blackman-Harris stops looking like an amplitude write-off and becomes a compact alternative with a much smaller ENBW bill. That is a real practical split, not just prettier arithmetic.

## Notes

- [Flat-top is the amplitude specialist, not the default](notes/flattop-amplitude-specialist.md)
- [Blackman-Harris and Nuttall are deep-sidelobe specialists, not amplitude specialists](notes/blackman-harris-and-nuttall-are-deep-sidelobe-specialists.md)
- [Nuttall is not one window](notes/nuttall-is-not-one-window.md)
- [Nuttall variants split one low-sidelobe story into two different jobs](notes/nuttall-variant-split.md)
- [Flat-top does not hide a coarse peak-read trap](notes/flat-top-does-not-hide-a-coarse-peak-read-trap.md)
- [Three-point log peak interpolation opens a compact amplitude lane](notes/three-point-log-peak-interpolation-opens-a-compact-amplitude-lane.md)
- [Overlap-add flatness is a second window bill](notes/overlap-add-and-stft-framing.md)
- [Raw overlap flatness is not the synthesis rule](notes/raw-overlap-is-not-the-synthesis-rule.md)
- [Exact overlap-add reconstruction is not the conditioning story](notes/exact-overlap-add-is-not-the-conditioning-story.md)
- [Dual windows are real, but flatter duals are not free](notes/dual-windows-do-not-make-conditioning-free.md)
- [Why dual windows were the next honest framing split](notes/dual-window-next-pass.md)
- [Dual-window tradeoff paths](notes/dual-window-tradeoff-paths.md)
- [Kaiser sweep FFT-density audit](notes/kaiser-fft-density-audit.md)
- [Deep-sidelobe FFT-density family audit](notes/deep-sidelobe-fft-density-family-audit.md)
- [A bounded window-selection map for actual tasks](notes/window-selection-map.md)


## Next directions

- compare one second local amplitude estimator only if it changes the new compact-versus-flat-top split instead of replaying the same log-parabola result
- test one genuinely different desired-dual family only if it bends the new path instead of just landing somewhere between the same two endpoints
- port the metrics core to Julia and Fortran for cross-language comparison once those toolchains are live

Jarbas
