# Flat-top is the amplitude specialist, not the default

Flat-top earns its reputation honestly.

If your tone lands between FFT bins and you care most about reading its amplitude correctly, flat-top is the window that resists the usual droop. That is the good news.

The bill shows up immediately after that.

Flat-top spends a lot of bandwidth to buy that amplitude honesty:

- the main lobe gets much wider
- the equivalent noise bandwidth jumps hard
- coherent gain drops enough that amplitude correction is not optional

So this is not the "best" window in general. It is the right specialist when single-tone amplitude accuracy matters more than frequency resolution or noise-floor efficiency.

## The fast way to read the figures

### Offset-loss plot

![Amplitude loss versus bin offset](../art/window-offset-loss.svg)

This is the cleanest reason to use flat-top.

As the tone slides away from the center of a DFT bin, most windows sag. Flat-top barely does. By the half-bin case, Blackman and Kaiser are still down by about a decibel. Flat-top is essentially flat.

### Half-bin leakage plot

![Half-bin tone leakage near the peak](../art/window-half-bin-leakage.svg)

This shows the same tradeoff from a different angle.

Flat-top keeps the peak top broad and flat, which is exactly why amplitude stays honest between bins. But that same broad top is also the warning sign: you are paying with resolution.

### Summary tradeoff card

![Amplitude specialist summary](../art/window-amplitude-specialist-summary.svg)

This is the point in one picture:

- **half-bin amplitude loss**: flat-top wins by a mile
- **ENBW**: flat-top is much more expensive
- **main-lobe width**: flat-top is also much broader

That is why it belongs as a specialist, not as the repo's default recommendation.

## When to use it

Use flat-top when:

- you are measuring the level of a mostly isolated sinusoid
- the exact bin alignment is not guaranteed
- amplitude accuracy matters more than squeezing nearby tones apart

Do not reach for it first when:

- you care about fine frequency resolution
- you are already leakage-limited by nearby tones
- raising ENBW would make the noise floor less honest for the task

## Repo takeaway

The clean mental split is simple:

- **Blackman / Kaiser** are strong general-purpose leakage-control choices
- **Flat-top** is the deliberate amplitude-measurement specialist

That is a useful distinction to keep in your head before the window zoo gets any bigger.
