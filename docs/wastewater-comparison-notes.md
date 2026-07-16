# Wastewater cross-check vs. air-sampling detections

Working notes — comparing Team Canada air-sampling results against public
wastewater surveillance dashboards in each host jurisdiction, for the four
study targets (SARS-CoV-2, influenza A, influenza B, RSV).

## What each source actually reports (this is the crux)

The four dashboards do **not** report the same quantity, and three of the four
use fundamentally incompatible units:

| Source | Cities | Targets | Reported quantity | Units |
|---|---|---|---|---|
| Canada (health-infobase aggregate) | Montreal, Toronto, **Metro** Vancouver | all 4 | PMMoV-normalized viral index | dimensionless index |
| California (CDPH/NWSS) | LA / JWPCP (Torrance) | all 4 | absolute concentration | copies/L (or copies/g dry sludge) + human fecal marker |
| Houston (Rice/HHD ArcGIS) | 69th Street (downtown/Main St) | SARS-CoV-2 only (per-plant) | proprietary viral-load index, 100 = Jul-2020 baseline | dimensionless index |

Key mismatches:
- **Canada** is already flow/fecal-normalized → a unitless index.
- **California** is raw copies/L, but ships a `hum_frac_mic_conc` fecal marker
  in the same units on every row → can be self-normalized (target ÷ marker).
- **Houston's** public per-plant feed is a rescaled index (`vl_est`) and, for
  per-plant granularity, **SARS-CoV-2 only**; flu/RSV are citywide/school-level.
- **Houston coverage ends 2026-06-22**, before the team's 6/30–7/4 stay.

So absolute levels are NOT directly comparable across all five cities. The only
defensible comparison is **within-source, relative** (z-score / rank / % of
each site's own recent baseline), not absolute copy numbers.

## Normalized approach used

- Canada: median of the 3 sub-site rows per (city, measure, week) of `w_avg`
  (already PMMoV-normalized).
- California (LA/JWPCP): `pcr_target_avg_conc ÷ hum_frac_mic_conc` (×1e6),
  averaged per ISO week.
- Houston (69th St): `vl_est` index as published.
- Floor values in the Canada feed (fluA 0.0122, fluB 0.0088, rsv 0.0082) are
  non-detect substitutions → treat as "not detected."

## Study window levels (normalized)

CANADA index (median across sub-sites):

Montreal (team there 6/3–6/6):
  SARS ~0.9–1.3 (low), fluA/fluB/RSV at floor → all essentially absent.

Toronto (6/7–6/11):
  SARS ~3.6–7.3 (moderate, higher than Montreal), flu/RSV at/near floor.

Metro Vancouver (6/14–6/24):
  SARS ~4.3–7.7 during the visit, spiking to ~21 by 6/28; fluA intermittent,
  fluB persistently detected (~1–2), RSV low. Highest SARS of the 3 CA cities.

LA/JWPCP (Torrance, 6/27–6/28) — SARS÷marker ×1e6:
  wk of 6/21 = 3.16, wk of 6/28 = 2.40. Non-zero SARS, flu/RSV ~0.

Houston/69th St (downtown, through 6/22 only):
  vl_est 11–17 on a 100=baseline scale → very low SARS; window ends before stay.

## Did Canadian sites have lower virus levels than US sites?

**No — not clearly, and not for SARS-CoV-2.** The dominant signal everywhere is
SARS-CoV-2 (matching the air data, where SARS was the only target detected in
more than one or two cartridges). On the normalized indices, the Canadian sites
(especially Toronto and Metro Vancouver) were running **as high or higher** than
the two US sites during the visits:

- Metro Vancouver SARS index (~4–8, spiking to 21) and Toronto (~3.6–7.3) were
  the busiest SARS signals of any host city.
- LA was clearly positive but moderate; Houston (through 6/22) was very low.
- Montreal was the *lowest* Canadian city, comparable to LA/Houston.

So the framing "Canadian sites lower than US" is not supported. If anything the
two western Canadian host cities had the strongest community SARS-CoV-2 signal.

## Concordance with the air data

- Air data: SARS detected in Houston, LA, Montreal (1 hit); **zero** SARS in
  Toronto and Vancouver air despite those two having the highest wastewater
  SARS. Flu A had single sporadic air hits (Houston, Toronto, Vancouver); flu B
  one hit (Vancouver, which is the one city with persistent fluB in wastewater);
  RSV never detected in air (consistent with RSV at/near floor everywhere).
- The air and wastewater signals are directionally consistent for the "what's
  circulating" question (SARS >> flu > RSV; RSV essentially absent in summer),
  but per-city they do **not** track tightly — expected, since air sampling
  measured a handful of team-occupied rooms over a few days, while wastewater
  integrates an entire metropolitan sewershed over weeks.
