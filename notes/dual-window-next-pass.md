# Dual windows are the next honest framing split

## Research question

Would one bounded dual-window comparison sharpen the repo's framing story more than another same-window redraw?

I think yes.

The current repo already separates three different claims:

- raw overlap flatness is not the same as leakage behavior
- raw overlap flatness is not the same as the weighted synthesis rule
- exact same-window reconstruction is not the same as calm same-window reconstruction

The next clean split is this one:

- same-window normalized overlap-add is not the same thing as using a real dual window

That is a better next move than another cosmetic redraw because it changes the reconstruction model, not just the plotting angle.

## Scope boundary

This is a bounded follow-up note, not a full Gabor-frame tutorial.

The question here is narrow:

- finite windows already in this repo
- the same framing lengths already used here
- a small hop set such as half-overlap and quarter-hop
- one comparison between same-window normalized synthesis and a genuine dual-window path

It is **not** trying to cover arbitrary frame theory, painless nonorthogonal expansions in general, or a giant survey of perfect-reconstruction filter banks.

## Intake mix

Raindrop + HN + source docs.

- **Raindrop:** queried the local export for STFT / overlap-add / dual-window material; no focused hit worth trusting for this exact pass
- **HN:** checked the local HN bookmark surface; recent saved items were unrelated to STFT framing, so HN was a low-yield intake here
- **Source docs:** accepted as the real backbone for this pass

That is a useful rejection, not a failure. It means this topic wanted direct technical sources instead of another discovery loop.

## Accepted sources

### 1) SciPy `check_COLA`

Accepted because it states the sharp bridge from the old repo lane to the next one: COLA is equivalent to having a **constant dual window**, and the legacy COLA check is narrower than the more general dual-window framing.

Useful takeaway:

- COLA is one special case inside a larger dual-window story
- the repo can stop talking as if COLA-friendly same-window overlap were the only clean reconstruction lane

### 2) SciPy `closest_STFT_dual_window`

Accepted because it makes the next experiment concrete instead of purely theoretical.

Useful takeaway:

- for a fixed analysis window and hop, there is a family of valid dual windows
- SciPy explicitly exposes the idea of the dual window closest to a desired target, including the rectangular target that corresponds to the COLA story
- decreasing hop increases the degrees of freedom in the dual-window set

That last point is the practical hook: the repo already studies hop-dependent conditioning, so a dual-window follow-up can stay in the same language.

### 3) SciPy `ShortTimeFFT`

Accepted because it states the inversion model cleanly: inverse STFT uses the **dual window**, and the canonical dual is the default minimal-energy choice.

Useful takeaway:

- same-window normalized reconstruction is only one synthesis path
- the canonical dual is the default modern reference path, not an exotic edge case

### 4) Julius O. Smith, *Spectral Audio Signal Processing*, dual COLA section

Accepted because it supplies the frequency-domain read of COLA: the usual overlap-add condition has a spectral dual, and the window-transform zero pattern matters.

Useful takeaway:

- the repo's framing lane does not have to stay purely in overlap-sum language
- a dual-window comparison can stay bounded while still pointing at the deeper filter-bank picture

## Rejected or only partially used sources

### librosa `istft`

Partially used, not as the main source.

Why not the backbone:

- it is useful for confirming the squared-window normalization story already in the repo
- it does **not** sharpen the dual-window question as directly as SciPy's newer STFT docs do

So it is a good adversarial check against overclaiming, but not the right anchor for the next pass.

### HN / general discovery items

Rejected for this pass.

Reason:

- low yield relative to direct source docs
- likely to widen the pass without making the actual next experiment sharper

## The actual next experiment

A good bounded comparison would use just three windows and two hops:

- **windows:** Hann, Blackman-Harris, flat-top
- **hops:** `H = 64` and `H = 32` for frame length `N = 128`

For each pair, compare:

1. same-window normalized overlap-add
2. canonical dual-window synthesis
3. if easy to compute cleanly, the closest COLA-friendly dual to a rectangular desired dual

## Metrics worth adding

The repo already has the right taste for the comparison. Reuse that instead of inventing a new dashboard.

For each path, measure:

- exact reconstruction error on a periodic test signal
- RMS coefficient-noise gain
- worst-point coefficient-noise gain
- max synthesis-envelope ripple when relevant
- dual-window energy ratio relative to the analysis window

That would answer the real question:

> does a dual-window path actually buy calmer synthesis where same-window normalization looks algebraically fine but numerically ugly?

## Adversarial check

A dual-window pass could easily become fake sophistication.

Two ways that could happen:

1. **If the chosen hop/window pairs are already calm in the same-window path**, the dual-window comparison says almost nothing.
2. **If the dual window is introduced without keeping the metrics parallel**, the result will look deeper while becoming harder to read.

So the pass only earns its place if it lands on the uncomfortable cases already identified by this repo.

That means Blackman-Harris and flat-top at half-overlap are the right pressure points, not Hann at quarter-hop where everything is already boring.

## Working conclusion

The dual-window follow-up is worth doing.

Not because dual windows are inherently fancier, but because they answer the next question the current repo now raises on its own: once same-window normalization looks exact but poorly conditioned, is the better move to shrink the hop again, or to change the synthesis window?

That is a real fork in the road, and this repo is now set up to show it cleanly.

Jarbas
