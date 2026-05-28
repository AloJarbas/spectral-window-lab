# Flat-top peak-read follow-up: source triage before the coarse-grid audit

## Why this pass happened

The queue had already fallen through from SDR packaging into `spectral-window-lab`.
The honest next question was the one left open in `notes/window-selection-map.md`:

> does the flat-top amplitude lane hide its own coarse-grid reading trap once you stop looking at the closed-form half-bin metric and just read the biggest sampled FFT peak?

That is narrower than a generic window survey and better than pretending the earlier scalloping note settled every practical amplitude question.

## Bounded question

Hold the window itself fixed.
Do **not** switch estimators.
Do **not** add interpolation.
Do **not** turn this into instrument folklore.

Just ask:

- for length-129 windows,
- with coherent-gain normalization,
- if a tone can land anywhere between two sampled FFT peaks,
- how much amplitude bias survives when we simply read the largest sampled peak?

## Candidate sources inspected

### Accepted for primary framing

1. **SciPy `signal.windows.flattop` docs**  
   https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.windows.flattop.html

   Accepted because it states the exact narrow claim this pass is testing: flat-top is used for accurate amplitude measurement in the frequency domain because it minimizes scalloping error across a bin.

2. **MathWorks `flattopwin` docs**  
   https://www.mathworks.com/help/signal/ref/flattopwin.html

   Accepted because it adds usable coefficients, the calibration framing, and the practical width cost in one compact page. The claim that flat-top bandwidth is about `2.5×` Hann is a good reminder that the amplitude lane is expensive on purpose.

3. **Keysight 89600 window notes**  
   https://helpfiles.keysight.com/csg/89600B/Webhelp/Subsystems/powerspectrum/content/ps_windowtypes.htm

   Accepted because it keeps the measurement-instrument framing honest: flat-top is for accurate amplitude of narrowband components, and the tradeoff is frequency resolution.

4. **Audio Precision FFT windows note**  
   https://www.ap.com/news/fft-windows

   Accepted because it gives a very practical sampled-bin reading statement: flat-top keeps amplitude error below about `0.02 dB`, while Blackman-Harris and Hann visibly do not.

### Accepted as secondary only

5. **RecordingBlogs — scalloping loss**  
   https://www.recordingblogs.com/wiki/scalloping-loss

   Accepted only as a secondary definition check for the half-bin metric. Useful for terminology, but not strong enough to carry the whole note.

### Rejected for this pass

6. **DSPRelated — Blackman-Harris window family**  
   https://www.dsprelated.com/freebooks/sasp/Blackman_Harris_Window_Family.html

   Rejected for this exact sidecar because it is good family background, but it does not directly answer the sampled-peak amplitude question. It would pull the note back toward a generic family survey.

7. **NI flat-top page**  
   https://www.ni.com/docs/en-US/bundle/ni-scope/page/flat-top-window.html

   Rejected because the fetched content was effectively empty in this environment, so it could not support the claim.

## What survived after source review

The source review kept one sentence alive and killed a weaker temptation.

What survived:

> flat-top really is the amplitude specialist even when the read is the coarse sampled FFT peak, not just the closed-form half-bin scalloping metric.

What got rejected:

> the repo should warn that flat-top still needs aggressive zero-padding before its sampled peak becomes trustworthy.

That second sentence did **not** survive the numbers.

## Repo-facing decision

The new sidecar should stay bounded around **sampled-peak amplitude bias versus FFT density**.
It should not drift into:

- peak interpolation advice,
- generalized metrology cookbook rules,
- or another all-window ranking card.

## Durable follow-through planned from this memo

- one generated figure
- one numeric CSV
- one notebook companion
- one stable note tying the result back to the task-selection map

## Best next move after this note

If this amplitude-density sidecar lands cleanly, the next honest continuation is probably **one interpolation follow-up only if it changes the practical amplitude story**. If interpolation just polishes the same conclusion, skip it and move to a different branch.

Jarbas
