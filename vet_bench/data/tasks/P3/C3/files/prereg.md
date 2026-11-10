# Pre-registration: cheap-side taker test

Written 2026-09-01, before any trade in the test window.

- Question: does buying contracts our model prices at least 5 cents above the ask make money after fees?
- Data: every trade the rule would have made from 2026-09-02 to 2026-10-27 on the weekly series, 120 events.
- Primary: mean P&L per contract after fees in one cell, late window and price under 20 cents, with a 95% interval clustered by event. We chose this cell in an exploration run on 2026-06-03 to 2026-08-26, a period that does not overlap the test window (late window, under 20 cents: n 150, mean +10.4 cents after fees).
- Decision: we call it an edge only if the primary interval's lower bound is above zero. Otherwise the result is not established.
- Secondary, exploratory only, never decision cells: the same mean in the other 11 cells, window (early, mid, late) by price (<20, 20-50, 50-80, >=80 cents), and all trades pooled.
