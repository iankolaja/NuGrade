---
name: nuclear-data-quality-assessment
description: Provide broad commentary on experimental and evaluated nuclear cross section data from the NuGrade app. Use this when the user needs to understand if a nuclide or reaction channel is measured well.
license: Complete terms in LICENSE.txt
---

This skill guides analysis of nuclear cross section data from the NuGrade Flask app. NuGrade compares EXFOR measurements with nuclear data evaluations, such as ENDF, and provides a high level visualization of how well a certain nuclide and nuclear reaction channel is measured in terms of error and energy coverage.

## Data Conventions
- All nuclides are stored atomic number then chemical symbol (i.e. "235U", "35Cl").
- All reactions are stored projectile comma target (i.e. "N,TOT", "N,EL, "N,INL", "N,G")
- Always use this for tool calls.

## Data Schema
- 'Energy' - Energy (in eV) of cross section measurement.
- 'Data' - Cross section (in b) of measurement.
- 'dData' - Cross section uncertainty (in b) of measurement
- 'EXFOR_Entry' - EXFOR ID for experiment.
- 'Year' - Year of measurement.
- 'Author' - Experiment author.
- 'endf7-1', 'endf8' - Interpolated cross section from endf7-1 or endf8 at energy.

## Tool Usage
- For data quality questions, start with `get_nugrade_report`.
- For questions about specific experiments, methodology, such as detector types, neutron sources, sample materials, facility details, systematic errors, use `search_corpus` with appropriate filters. Do not answer these from domain knowledge. The EXFOR text corpus is the ground truth. Try to incorporate quotes when possible and relevant. If the first search returns low corpus coverage or no useful results, acknowledge that and stop retrying, as the corpus is currently very limited.
- When calling `search_corpus`, phrase the query as a fragment of EXFOR experimental text rather than a user question. For example, use "NaI(Tl) scintillation detector gamma counting capture measurement" rather than "what detector is used for gamma counting". This improves similarity matching against the corpus style.

## Domain Knowledge
- EXFOR database structure and metadata
- Cross section physics (resonances, thresholds, reaction mechanisms)
- Common systematic errors in measurements
- Evaluation methodology differences between libraries
- Nuclear data and measurement literature

## Questions to Consider in Analysis
- Energy Coverage: Do the measurements cover a wide energy range? If the user is working with a certain neutron flux spectrum, is the cross section measured well in high flux energy regions?
- Measurement Uncertainty: Does the data have measurement uncertainty listed? 
- Evaluation Agreement: Do the measurements generally agree with the evaluation(s)? What's going on with the outliers?
- Overall Verdict: Are the evaluated cross sections well supported by the data? Should they be trusted? Which evaluation best to use?

## Guidelines
- No arbitrary numerical rankings. These metrics exist inside of NuGrade already.
- Reference specific data points by author and year.