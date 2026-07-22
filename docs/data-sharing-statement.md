# Data sharing statement — updated text for the Google Doc

Copy the paragraph below into the **Data sharing statement** section of the
manuscript Doc, replacing the current placeholder paragraph. It points to the
actual locations of the data in this repository. The sequencing sentence still
has a bracketed placeholder because the repository and accession are not yet
assigned — fill those in before submission.

---

The air-sampling detection data reported in this study — cartridge-level results
by virus, room type, city, date, sampling window, and cycle-threshold value —
are available in the study repository at
`analysis/data/cartridges_long.csv` (739 rows, the complete record of collected
samples, being 182 respiratory cartridges tested for 4 targets plus 11
cartridges that produced no valid test data). Each cartridge carries a `status`
flag (valid, spc_negative, probe_error, or no_valid_data), and the figures show
valid runs only, so invalid samples appear in the table but not in the figures.
The community wastewater surveillance
values used for the contextual comparison are provided as per-city extracts in
the same repository (`analysis/data/ww_canada.csv`,
`analysis/data/ww_losangeles.csv`, and `analysis/data/ww_houston.csv`), each
retrieved from the public source cited in the Methods. All figures in this
manuscript are reproducible from these files using the analysis scripts in the
repository (`analysis/make_figures.py` and `analysis/make_figure3.py`). The
repository is at https://github.com/dholab/team-canada-world-cup-2026 [currently
private; it will be made public upon publication — confirm access conditions and
add an archived DOI, e.g. via Zenodo, at that time]. Viral sequencing data from
the July 4, 2026 Houston eluates will be deposited in [repository, e.g. NCBI
GenBank/SRA] under accession [number] upon publication. [Confirm repository,
accession numbers, and access conditions.]
