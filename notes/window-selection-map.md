# A bounded window-selection map for actual tasks

This repo has enough lanes now that "just use Hann" or "just use flat-top" is worse than saying nothing.

The point of this sidecar is not to crown one universal best window.
It is to answer a narrower question:

**if the task is specific, which windows survive the obvious guardrails, and which of those survivors actually fit best?**

![Window selection map](../art/window-selection-map.png)

## 1. What this map is built from

The map does not invent a second scoring universe.
It reuses the metrics already living in this repo:

- equivalent noise bandwidth,
- null-to-null main-lobe width,
- peak sidelobe level,
- half-bin scalloping loss,
- quarter-hop synthesis-gain swing from the weighted overlap-add sidecar.

The frequency metrics use the repo's symmetric length-129 windows.
The STFT lane uses the existing length-128 quarter-hop framing pass.

That makes this a **bounded decision card**, not a generic DSP commandment.

## 2. Why the guardrails matter first

A weighted score by itself can still lie.
If you ask for amplitude honesty, a window with huge scalloping loss should not stay in the race just because it is narrow.
If you ask for a calmer quarter-hop STFT lane, a window with a loud synthesis-normalization swing should be rejected before ranking starts.

So each task column does two things in order:

1. apply a few simple caps or floors,
2. rank the surviving windows with weighted versions of the existing metrics.

That is the whole trick that keeps the map from collapsing back into a vague window zoo.

## 3. The five task lanes

### A. Separate very close equal-strength tones

Winner: **rectangular**

This is the narrowest and most dangerous lane in the figure.
Rectangular wins only because the task is scoped so tightly that main-lobe width matters more than far-out leakage.
The note is not "rectangular is a good default."
It is the opposite:

**rectangular only deserves to win when you really mean resolution first and you accept the leakage bill.**

### B. Compact low-sidelobe compromise

Winner: **Kaiser `β = 8.6`**

This lane excludes the very wide heavy specialists and then asks for a compact answer with cleaner sidelobes than Hann or Hamming.
That is where the repo's old Blackman-like Kaiser checkpoint finally becomes a real recommendation instead of a trivia fact.

Why it wins here:

- noticeably stronger sidelobe suppression than Hamming or Hann,
- still much more compact than Blackman-Harris, Nuttall, or flat-top,
- scalloping loss stays in the same neighborhood as Blackman.

### C. Hunt a weak spur beside a strong line

Winner: **Nuttall**

This is the deep-sidelobe lane.
Once the task really is "show me the small thing next to the loud thing," the window that pushes far-out leakage lower deserves to surface.

Nuttall edges out Blackman-Harris here because the sidelobe win is slightly stronger while the width and ENBW cost stay in the same rough class.

### D. Measure isolated-tone amplitude honestly

Winner: **flat-top**

This is the one task where the repo should say the quiet part out loud:

**flat-top is expensive, but the expense is the point.**

If between-bin amplitude honesty dominates the task, flat-top should stop apologizing for its ENBW and main-lobe width and just win the column.

### E. Quarter-hop STFT with calmer reconstruction

Winner: **Hamming**

This is the least obvious column, and I like that.
The quarter-hop framing lane rejects windows whose weighted overlap bill is already loud, then ranks the survivors by synthesis calm plus a smaller spectral sanity check.

Hamming wins because it stays very flat in the quarter-hop weighted-overlap sense while keeping better sidelobes and slightly lower ENBW than Hann.
The gap is not huge, but it is real in this bounded setup.

## 4. What the map teaches better than a single ranking

The strongest lesson is not which window won which column.
It is that the winners are different **for good reasons**:

- resolution-first picks do not look like amplitude-first picks,
- deep-sidelobe picks are not compact defaults,
- STFT framing calm is not the same thing as spectrum-reading honesty,
- flat-top should only win when you explicitly mean amplitude honesty.

That is more useful than another paragraph ending in "it depends" and then refusing to say how.

## 5. What this map does not claim

It does **not** claim:

- that these weights are universal,
- that one window should dominate every measurement chain,
- that a different frame length or hop would keep the same STFT winner,
- that the close-tone lane is safe when leakage matters more than main-lobe width.

It only claims that, for the bounded tasks above, the repo's own metrics are now rich enough to support a short decision graphic instead of a folklore answer.

## 6. Artifact trail

This sidecar adds:

- `art/window-selection-map.svg`
- `art/window-selection-map.png`
- `art/window-selection-map.csv`
- `notebooks/window_selection_map.ipynb`
- `windowlab/recommend.py`

## Best next move

If this repo gets one more pass, the strongest continuation is probably **one bounded reconstruction note**:

- not just which windows keep the overlap bill calm,
- but when an analysis/synthesis pair with the same window stays numerically well-behaved after actual overlap-add normalization.

That would keep the new task map tied to one more concrete downstream use instead of letting it drift back into an abstract ranking card.
