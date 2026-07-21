# Pre-Idea Draft: Repetition Gate

## Two-Sentence Pitch

Add a controller-level gate that detects repeated `(normalized error, action, local outcome)` cycles and prevents more calls to the same action on the same proof state. Instead of spending another large prompt, the gate forces a route change: retrieve a proof skeleton, ask for a diagnosis-only plan, or stop the run as low expected value.

## Hidden Assumptions

- Repeated action loops are mostly unproductive after a small number of failures.
- Error signatures can be normalized robustly enough across small line-number changes.
- Forced route changes do not suppress a late successful attempt too often.

## Strongest Rejection Case

Some hard tasks may need many similar-looking attempts before success; a strict gate could reduce verified rate.

## Cheapest Falsification

Replay logs offline:

- Simulate gates after 2, 3, and 4 repeated same-action failures.
- Estimate saved token calls.
- Count how many real successful runs would have been prematurely stopped.

## Promotion Verdict

Promote as a low-risk efficiency component if the offline replay shows high token savings with low false-stop rate.

