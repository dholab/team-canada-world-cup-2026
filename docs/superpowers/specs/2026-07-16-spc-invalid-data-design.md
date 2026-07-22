# Add SPC results and invalid samples to the dataset

**Date:** 2026-07-16
**Repo:** `dholab/team-canada-world-cup-2026`
**File touched primarily:** `analysis/extract_data.py`, `analysis/data/cartridges_long.csv`

## Problem

`cartridges_long.csv` omits information about invalid runs, so those samples
appear in neither the figures nor a complete data table:

1. The Sample Processing Control (SPC) Ct value is not recorded, only its
   Positive/Negative call.
2. The two SPC failure modes are not distinguished: probe error (SPC reported
   Ct < 5, source "Average Result" = 0.0, tooltip "Invalid — Ct < 5 (assay
   error)") versus SPC no-amplification (Average Result = 99.0).
3. Eleven cartridges recorded in the source only as the target
   "(invalid — no valid test data)" — real collected samples that produced no
   result — are absent from the CSV entirely.

The figures intentionally show only valid runs. The data table should be the
complete record, so a reader can see every collected sample and why some were
excluded from the figures.

## Source of truth

`analysis/raw/API_PER_ROOM.html` (the LabKey "Pathogen heat map by room"
export). Relevant facts confirmed from it:

- 221 unique cartridges: 182 with the four respiratory targets, 11
  "(invalid — no valid test data)", 28 norovirus-only.
- Of the 182 respiratory cartridges, 5 are SPC-negative (2 Vancouver, 1 Los
  Angeles, 2 Houston). All 15 viral detections came from valid runs.
- SPC "Average Result" is ~28–30 for valid runs; the negatives are 0.0 (probe
  error) or 99.0 (no amplification).
- The 11 invalid cartridges carry city/room/sampler/start/end metadata but have
  no `points` entry and no per-virus rows.
- The 28 norovirus-only cartridges are out of scope (this is the respiratory
  dataset).

## Design

Make `cartridges_long.csv` the complete record of all collected
respiratory-scope samples, with explicit validity status. Figures continue to
plot only valid runs.

### Schema

Current columns: `city, room, sampler, cartridge, start, end, dur_h, virus, ct,
qual, detected, spc`.

Add two columns:

- `spc_ct` — the SPC control's Ct for the cartridge. The SPC "Average Result"
  when it is a real Ct (0 < value < 99); blank when 0 (probe error) or 99 (no
  amplification), so the column carries a value only when the control amplified.
- `status` — per-cartridge validity label, one of:
  - `valid` — SPC positive; targets tested and reportable.
  - `spc_negative` — SPC did not amplify (Average Result 99); targets on this
    run are not reliable.
  - `probe_error` — SPC invalid, Ct < 5 (Average Result 0, assay error).
  - `no_valid_data` — cartridge produced only "(invalid — no valid test data)".

`spc` (the existing Positive/Negative call) is retained unchanged.

### Row shape

- The 182 respiratory cartridges keep **4 rows each** (one per virus), 728 rows.
  This includes the 5 SPC-negative/probe-error ones, which have real per-virus
  rows in the source (qualitative "Negative") — those rows stay but are flagged
  via `status` as unreliable.
- The 11 invalid cartridges are added as **1 row each**, with `virus` blank,
  `ct`/`qual` blank, `detected = 0`, `spc` = the SPC call if present,
  `spc_ct` blank, `status = no_valid_data`. They have no per-virus data, so
  four identical rows would fabricate structure that does not exist; one record
  per failed cartridge is honest to the data.

New total: 728 + 11 = **739 rows**.

Consumers already filter on `detected`/`spc`, so the mixed row shape (4 rows for
tested cartridges, 1 for fully-invalid ones) does not affect the figures. A
naive `groupby("virus")` places the 11 blank-virus rows in their own group,
which is correct — they are not virus measurements.

### Extractor (`extract_data.py`)

- Read `spc_ct` from the SPC row's Average Result per cartridge; derive `status`
  from the SPC qualitative call and Ct value (positive → valid; negative with
  99 → spc_negative; negative with 0 → probe_error).
- Emit the existing 728 respiratory rows with the two new columns populated.
- Append the 11 "(invalid — no valid test data)" cartridges as single
  `no_valid_data` rows, taking city/room/sampler/start/end from their source CSV
  metadata and computing `dur_h`.
- Sort order unchanged (city, room, sampler, start, virus), with blank-virus
  rows ordered last within their cartridge.

### Figures

No figure code changes. `make_figures.py` and `make_figure3.py` already select
detections and valid/invalid runs from existing columns. Verification will
confirm the 15 detections are unchanged and the new `no_valid_data` rows do not
appear as detections or valid negatives. The 11 invalid cartridges fall on
sessions the figures already mark with an asterisk (rooms invalid while other
rooms in the session were valid), so no new visual elements are needed.

### Clarity in legends and manuscript

Update the following so it is explicit that invalid samples are retained in the
data table but excluded from the figures:

- `analysis/figure_legends.md` — add a sentence to Figure 1 and Figure 2 legends
  stating that samples with a negative SPC or a probe error are recorded in the
  data table but not shown in the figures.
- The manuscript "Data and code" / data-sharing wording (in `index.qmd` and the
  tracked `docs/data-sharing-statement.md`) — note that
  `cartridges_long.csv` includes invalid runs (SPC-negative, probe error, and
  no-valid-data cartridges), flagged by the `status` column, whereas the figures
  display valid runs only.

## Validation

After regenerating `cartridges_long.csv` and the figures:

- 739 rows total; 193 distinct cartridges (182 respiratory + 11 invalid).
- 15 detections, unchanged (SARS-CoV-2 11, IAV 3, IBV 1, RSV 0), all with
  `status = valid`.
- `status` counts: 5 respiratory cartridges are `spc_negative`/`probe_error`
  (matching the 5 SPC-negatives), 11 are `no_valid_data`, the rest `valid`.
- `spc_ct` populated (roughly 28–30) for valid cartridges, blank for the
  invalid ones.
- All three figures render identically to the pre-change versions (byte-compare
  or visual check); no invalid rows leak in as detections or negatives.

## Non-goals

- Norovirus cartridges (28) remain out of scope.
- No change to the figure rendering or the manuscript figures themselves.
- No re-baselining of denominators (182 collected / 177 valid respiratory
  cartridges is a manuscript-text decision, unaffected by this data change).
