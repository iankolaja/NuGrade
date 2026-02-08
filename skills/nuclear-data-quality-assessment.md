---
name: nuclear-data-quality-assessment
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI). Generates creative, polished code and UI design that avoids generic AI aesthetics.
license: Complete terms in LICENSE.txt
---

This skill guides the analysis of nuclear cross section data from the NuGrade Flask app. NuGrade compares EXFOR measurements with nuclear data evaluations, such as ENDF, and provides a high level visualization of how well a certain nuclide and nuclear reaction channel is measured.

The conversation is always opened with the NuGrade-processed data specific to the reaction channel or channels being considered.

## Data Conventions
- All nuclides are stored internally atomic number followed by chemical symbol (i.e. "235U", "35Cl", "56Fe").
- All reactions are stored internally with projectile comma target (i.e. "N,TOT", "N,EL, "N,INL", "N,G")
- Always use these conventions for tool calls.

## Data Schema
- 'Energy' - Energy (in eV) of the cross section measurement
- 'dEnergy' - Energy (in eV) uncertainty of the cross section measurement
- 'Data' - Cross section (in b) value of the measurement.
- 'dData' - Cross section uncertainty (in v) of the the measurement
- 'EXFOR_Entry' - EXFOR metadata associated with the experimental measurement
- 'Year' - Year the measurement is from.
- 'Author' - First author on the experiment.
- 'Dataset_Number'  - EXFOR metadata associated with the experimental measurement
- 'MT' - ENDF reaction number
- 'dData_assumed' - Cross section uncertainty (in v) assumed for the measurement when none was provided by the author.
- 'endf7-1' - Interpolated cross section from endf7-1 at this energy.
- 'endf7-1_chi_squared' - Chi Squared value using measured value, endf7-1 value, and measurement uncertaintty.
- 'endf7-1_relative_error' - Relative error between measured value and endf7-1 value.
- 'endf8' - Interpolated cross section from endf8 at this energy.
- 'endf8_chi_squared' - Chi Squared value using measured value, endf8 value, and measurement uncertaintty.
- 'endf8_relative_error' - Relative error between measured value and endf8 value.

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
- Author: Does the author have any trends the user should be aware of in their measurements?
- Ways To Improve: If the user could measure the cross section on their own, what should they focus on?
- Overall Verdict: Are the evaluated cross sections well supported by the data? Should they be trusted? Which evaluation is best to use, and by what margin?

## Guidelines
- Don't give arbitrary numerical rankings. These metrics exist inside of NuGrade already.
- If you need to reference a specific point, identify it by the author and year.