# Existing FSP monitor/export gap

Existing retained FSP and post-FSP metadata support separate wavelength-resolved raw upward power and filtered angular far-field outputs. Source position and x/z orientation are recoverable from case identity; raw power, normalization fields, wavelength grid, angle grid, and filter identity are separately present.

A joint wavelength-angle tensor is not present in the existing export. The frozen classification is **B: ONLY_SEPARATE_SPECTRAL_AND_SINGLE_WAVELENGTH_ANGULAR_AVAILABLE**. The monitor/export upgrade must export a raw joint `lambda x theta x channel` tensor, exact grids, channel identity, source identity, normalization denominator, validity flags, and provenance hashes before the 4-geometry pilot. No solver is authorized by this audit.
