# Figure QA

Python-only backend; raw 21-wavelength paired records, no confidence intervals or independent-sample claims. Two physical anchor pairs. No smoothing, phase alignment, data exclusion, log color scale, or image manipulation. Source: WAVELENGTH_ERROR.csv and MODAL_AMPLITUDE_PHASE.csv. TE/TM panels use separate linear scales and show SSE fractions explicitly; weak TE must not be compared by color intensity to dominant TM. Amplitude panel selects m=+1,+2,-3 for readability; full seven-order TE/TM data retained in CSV and heatmap. SVG/PDF editable text, 600dpi PNG preview.

Rendered panel audit: all wavelength limits, order axes and phase/amplitude panels inspected. No clipping or curve obscuring legends after repair. PDF audits: minimum7pt, no glyph below5pt. Source preflight:0 FAIL; raster exports600dpi.
