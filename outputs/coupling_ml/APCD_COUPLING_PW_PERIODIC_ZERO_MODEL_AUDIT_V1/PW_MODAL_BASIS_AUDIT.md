# PW modal basis audit

For Lambda_x=1740 nm and Lambda_y=290 nm over 440:1:460 nm, the air-side propagating set is `[[-3, 0], [-2, 0], [-1, 0], [0, 0], [1, 0], [2, 0], [3, 0]]` at every pilot wavelength. The +1 target is (1,0). Orders outside this set are not silently discarded: candidate evanescent orders use a bounded first audit basis and the implementation must retain all propagating orders. The GaN-side basis requires native material/dispersion readback before solver admission.
