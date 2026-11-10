---
name: vet
description: Eight checks that catch the usual ways a research result turns out to be wrong. Use it before any backtest, replay, edge, win rate or P&L number is believed or written up (a memo paragraph, a slide line, a go-live summary), when asked to confirm a result is real, when picking the "real finding" out of several bands or cells, when planning a live test or its go/no-go criteria, when deciding whether a mismatch means the data or the backtester is broken, and whenever someone wants the headline fast or the job behind the number is still running.
---

# vet

Agents are very good at producing a number and very bad at doubting it. A backtest says it works, the agent says it works, and you find out a week later that the fills were imaginary or the data knew the future.

These eight rules each come from a result that looked fine and wasn't. vet makes the agent go through them, one by one, before it tells you anything worked. It's slower than just reporting the headline. That's the point.

## How to use it

1. Copy this folder into `.claude/skills/` in your project.
2. When the agent is about to report a result, it runs the eight checks below against that result and writes down what it found for each: **PASS**, **FAIL** or **N/A**, with the evidence (a file, a row, a command, a count).
3. It then labels the claim with one word:
   - **EDGE:** the main test's interval clears the bar after costs, and a second look confirmed it.
   - **NOT ESTABLISHED:** the point estimate looks good, but the interval still includes "no effect", or no second look has run yet.
   - **NO EDGE:** the interval rules out an effect big enough to matter.
   - **UNDECIDABLE:** there isn't enough data to answer, and there won't be soon.
4. Any FAIL means the claim can't be EDGE. Say which check failed and what would fix it.

## The eight checks

### 1. Model fills against the real trade tape.

*A fill model built on price candles predicted that almost every order would fill. Few did.*

If the result depends on orders getting filled, match each simulated order against real trades: on your side of the book, at your price or better, after the moment your order would have been resting. A trade printing at your price is not your fill. Never use a candle's high or low as a fill. If queue position matters, measure how much size was ahead of you; don't assume it. Report the fill rate next to the result.

### 2. Replay only what was public at the time.

*A backtest edge came from knowing a figure would later be revised.*

For every input, ask when it became public. Use the value as it was first published, not the cleaned-up final one, and if the source only keeps the final version, record the first versions yourself going forward. Watch for fields that quietly encode the answer, like a close time that only exists because the event already ended.

### 3. A number is not citable until its job has finished.

*A per-trade figure from a partial scan was later withdrawn.*

Don't quote a number from a job that's still running or that died partway. Name files from unfinished runs as partial. When the job finishes, re-read every number you already quoted, because some of them will have moved.

### 4. A strong secondary result is not an edge until it replicates as the pre-registered primary.

*One did not.*

Write down the main test before you look at the data. If some other cell comes out positive, call it a candidate, not a result, and name the test that would confirm it: the same question, written down in advance, on data you haven't touched.

### 5. Compare with a tolerance, not equality.

*A match rate that looked like a data problem was a floating-point comparison.*

When two numbers should match and don't, check how they're stored before you blame the data. Compare floats within a tolerance you pick on purpose. For each mismatch that survives the tolerance, trace its cause in the data before you report it: find the field or step where the two sides part, and name it. If the files can't show the cause, say so plainly and name the data that would. For a number that lives in two systems, use the `reconcile` skill in this repo.

### 6. A result that looks too good is a bug until you decompose it.

If the result is much bigger than you'd expect, split it before you believe it: by side, by price range, by time period, by how far the model disagreed with the market. Real effects usually show up across the pieces. Bugs usually live in one of them: look-ahead, a filter nobody mentioned, duplicated rows. Report the split, not just the total.

### 7. A pass on the data that chose it needs a second look before it counts.

If you picked a price band, a subgroup or a threshold because it looked good on some data, that same data can't also be the proof. Hold out a slice before you start looking, or re-run the exact test on new data, or write the test down and wait for data that doesn't exist yet. Until then the claim is NOT ESTABLISHED. Report the pooled result across every band or cell you looked at next to the one you picked, so the reader sees how special it really is.

### 8. Ask whether the question is decidable before you work on it.

*Some needed years of data.*

Before building anything, estimate how many observations you'd need to detect a realistic effect, and how long the data takes to reach that. If the answer is years, stop, or change the question.

## House rules

- A point estimate alone is never a verdict. Give the interval: Wilson for win rates, a t interval for means, and cluster by whatever makes observations depend on each other (days, games, users).
- A positive interval that still includes zero is NOT ESTABLISHED. Never write it up as "has an edge".
- Don't kill an idea on a point estimate either. A kill needs the interval to rule out an effect worth having.
- The agent that built the result shouldn't be the one that checks it. If you can, have a second agent recompute the headline numbers from the raw data without reusing the first one's code.
