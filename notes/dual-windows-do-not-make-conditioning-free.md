# Dual windows are real, but flatter duals are not free

The draft research note for this repo asked a fair next question: once same-window normalized overlap-add is exact but numerically ugly, should the next move be a real dual window?

After building the sidecar, the sharper answer is:

- yes, dual windows are the right next concept
- no, they do not give a free escape hatch from the conditioning bill

## The first useful correction

In this repo's bounded periodic setting, normalized same-window synthesis already gives the **canonical dual**.

So the interesting comparison is not really

- same-window normalized synthesis versus
- canonical dual synthesis

because those collapse to the same path here.

The real comparison is this:

- the canonical dual, which is the calm minimum-energy dual
- the closest constant-looking dual, which tries to stay as close as possible to a scaled rectangular synthesis window while still reconstructing exactly

That turns out to be a better experiment anyway.

## Bounded setup

This pass stays narrow on purpose:

- frame length `N = 128`
- windows: Hann, Blackman-Harris, flat-top
- hops: `H = 64` and `H = 32`
- exact periodic reconstruction with no coefficient modification beyond synthetic coefficient noise

The generated artifact is `art/window-dual-window-comparison.png`, with the numeric sidecar in `art/window-dual-window-comparison.csv`.

## What the figure says

Every case reconstructs the reference signal to floating-point precision under both duals.

So exactness is not the story.

The story is the tradeoff between **looking flatter** and **staying calm under coefficient noise**.

### Hann

For Hann, the constant-looking dual gets almost perfectly flat:

- half-overlap flatness error drops from about `0.650` to `0.003`
- quarter-hop flatness error drops from about `0.715` to `0.001`

But the noise bill rises too:

- half-overlap RMS coefficient-noise gain goes from `1.20` to `1.43`
- quarter-hop RMS coefficient-noise gain goes from `0.82` to `1.01`

That is the gentlest version of the tradeoff: flatter, yes; calmer, no.

### Blackman-Harris

Blackman-Harris makes the split clearer.

At quarter-hop, the closest constant-looking dual is almost perfectly flat, but it is noticeably noisier:

- flatness error drops from `1.008` to essentially zero
- RMS coefficient-noise gain rises from `0.99` to `1.40`
- dual energy ratio rises from `0.96` to `1.93`

So the flatter-looking synthesis window is not the calmer one. The canonical dual still wins the conditioning lane.

### Flat-top

Flat-top is where the repo's earlier warnings cash out hardest.

At quarter-hop:

- flatness error drops from `1.568` to `0.013`
- RMS coefficient-noise gain jumps from `1.27` to `2.36`
- dual energy ratio jumps from `2.31` to `7.98`

At half-overlap, both duals are ugly because the starting point is already ugly. The constant-looking dual still fails to rescue the case in any meaningful way.

## Practical read

The dual-window pass still matters, but not for the reason a quick first guess might suggest.

It does **not** show a hidden synthesis trick that makes the bad cases easy.

It shows something more useful:

- exact reconstruction is cheap to arrange
- flatter-looking synthesis windows are cheap to ask for
- calm synthesis is not cheap, and the canonical dual is already the low-energy answer in this bounded setting

So when the same-window path looks badly conditioned, the first honest fix is still often the boring one:

- use a smaller hop
- or stop insisting on an analysis window that is hostile to the framing job

A constant-looking dual can make the synthesis window look tidier. It does not make the noise bill disappear.

## Caveat

This is still a narrow, painless periodic model.

It does not settle every STFT implementation detail, every boundary convention, or every modified-coefficient use case. It does settle the bounded question this repo actually asked: **for these windows and hops, does forcing a flatter dual buy a calmer synthesis path?**

Here, the answer is no.

## Companion notebook

Open `notebooks/dual_window_synthesis_tradeoffs.ipynb` next if you want the equations and the code path side by side.

Jarbas
