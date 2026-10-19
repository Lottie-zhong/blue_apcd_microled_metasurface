# Figure QA

{
  "visual_status": "PASS",
  "figures": {
    "PSCALE_DECOUPLING_OVERVIEW": "all4panels checked: fold lines, zero-origin power MAE, explicit Oracle and four-fold min/max bars, bias band; labels clear",
    "PSCALE_AND_POWER_SPECTRA": "all6panels checked: lowest/median/highest fixed NN3 Pscale error selection, shared legend, native1nm truth and model curves, no clipping; poor shifted peaks preserved"
  },
  "PDF_min_font_pt": 7,
  "width_mm": 183,
  "automated": "19PASS1WARN0FAIL",
  "warning": "No TIFF; report delivery uses editable PDF/SVG plus600dpiPNG, not final journal submission",
  "statistics": "n124 geometry,4frozenfolds; foldrange not confidenceinterval; representative spectra are individualcases without replicatebars",
  "source": "FIGURES.py,FIGURES/SPECTRA_SOURCE_DATA.csv and frozen OOF predictions",
  "no_data_excluded": true
}