# MDC Native-M1 2D dipole broadband 420-480 v1

Stage status: `native_m1_2d_dipole_device_closure_pass`.
Main candidate device closure: `PASS`.
Wan proxy unweighted FWHM: `window_truncated`.

The Wan engineering proxy left half-maximum is below 420 nm and was not extrapolated. This scoped limitation does not block B2-B4 or the preferred-candidate closure.

## R12 canonical normalization

The formal denominator is `near_source_outward_flux_r12nm`, measured with a 1 nm source-local mesh and four-sided direct outward Poynting integration. `eta_up_normalized_to_r12nm_box` is not exact total emitted power, absolute extraction efficiency, or a zero-radius extrapolation.

The prior M1-8 nm versus M2-12 nm decision compared unequal physical radii. Common-radius M1/M2 replay is below 1% at 12, 16, and 20 nm for x and z. The 12 nm M1 value is frozen.

Existing 440-460 runs contain only r8 monitors, so an r12 spectrum cannot be reconstructed without rerunning. Their raw spectra and invalid normalization evidence are preserved; no mixed-radius substitute is reported.

## 420-480 same-model comparison

|structure|spectral peak (nm)|spectral FWHM (nm)|FWHM status|integrated r12 normalized|relative to Bare|mean 450 angular FWHM|mean cone10|
|---|---:|---:|---|---:|---:|---:|---:|
|bare|480|n/a|no_isolated_peak|3.1361518|1|105.968|0.186653|
|wan_proxy|424.2|n/a|window_truncated|0.79227021|0.252625|33.633|0.545103|
|explicit|448.4|19.93118725085344|pass|0.42915656|0.136842|26.4483|0.626175|
|zl1_nominal|448.2|19.022730686535283|pass|0.55181887|0.175954|25.0349|0.629213|
|zl1_alternative|447.8|18.782086773076742|pass|0.56318791|0.179579|23.5924|0.632357|

## Key angular results

|structure|dipole|wavelength|peak set|FWHM|cone10|fraction sum|
|---|---|---:|---|---:|---:|---:|
|bare|x|443|[-4.217153126300968,4.217153126300968]|122.38352262637696|0.17600963061855626|1.0|
|bare|x|448|[-4.217153126300965,4.217153126300973]|111.83938579778832|0.17592170646801325|1.0|
|bare|x|450|[-4.217153126300967,4.217153126300967]|111.2485005151911|0.1759002430265208|1.0|
|bare|x|453|[-4.217153126300971,4.217153126300964]|111.16881657360125|0.1758893061291788|0.9999999999999999|
|bare|z|443.8|[-4.102201414665169,4.102201414665176]|100.53683916226674|0.19754493519535687|1.0000000000000002|
|bare|z|448|[-4.102201414665169,4.102201414665176]|100.63149136801314|0.19744890140397892|1.0|
|bare|z|450|[-4.102201414665178,4.10220141466517]|100.68809581188272|0.19740655648568156|1.0|
|bare|z|453|[-4.102201414665178,4.102201414665171]|100.77425349146212|0.19735669798628397|1.0|
|wan_proxy|x|422.6|[-68.11962906245793,68.11962906245795]|25.084193629440456|0.15508856618797928|1.0|
|wan_proxy|x|448|[-0.028662222062423855,0.028662222062431533]|29.913330968384606|0.609094419872879|1.0|
|wan_proxy|x|450|[-11.33810692536478,11.338106925364775]|37.782693403244416|0.46398689029507323|0.9999999999999999|
|wan_proxy|x|453|[-17.49666733772113,17.496667337721114]|47.27293995992649|0.3048467035545716|0.9999999999999999|
|wan_proxy|z|423.4|[-0.02866222206242752,0.02866222206242752]|25.8463339573347|0.5977351683280541|1.0|
|wan_proxy|z|448|[-4.102201414665169,4.102201414665176]|23.6358864667053|0.7653733726952584|1.0|
|wan_proxy|z|450|[-8.892281211260178,8.892281211260178]|29.48330800667764|0.6262189850948287|1.0|
|wan_proxy|z|453|[-13.333300177001295,13.333300177001288]|36.9660322829742|0.41190376446394095|1.0|
|explicit|x|448|[-0.028662222062423855,0.028662222062431533]|21.99329425438879|0.5759642758450814|1.0000000000000002|
|explicit|x|448.2|[-0.02866222206243333,0.028662222062425656]|22.25108119016423|0.5803921970601347|1.0|
|explicit|x|450|[-0.028662222062431745,0.028662222062424098]|27.010005969183126|0.5756826367091525|1.0|
|explicit|x|453|[-11.513557402340231,11.513557402340231]|36.08237418668885|0.39398038889949283|1.0|
|explicit|z|448|[-0.028662222062423855,0.028662222062431533]|21.172725050790504|0.7061105307177241|1.0|
|explicit|z|448.2|[-0.02866222206243333,0.028662222062425656]|21.413631903320834|0.7068897261783977|1.0|
|explicit|z|450|[-3.642555256937082,3.642555256937075]|25.88654855253222|0.6766677645000998|1.0|
|explicit|z|453|[-11.396578364289129,11.396578364289121]|34.76853739942243|0.45955432997422496|1.0000000000000002|
|zl1_nominal|x|448|[-0.028662222062423855,0.028662222062431533]|21.198733746820125|0.5566642971010458|0.9999999999999999|
|zl1_nominal|x|450|[-0.028662222062431745,0.028662222062424098]|25.0187681986933|0.572072307309283|1.0|
|zl1_nominal|x|453|[-9.58922346189408,9.589223461894074]|34.04435891666775|0.4301816013747126|1.0|
|zl1_nominal|z|448|[-0.028662222062423855,0.028662222062431533]|20.944835854058766|0.7070457446386693|0.9999999999999999|
|zl1_nominal|z|450|[-3.010918799882,3.0109187998819924]|25.05097277605885|0.6863542969986299|1.0|
|zl1_nominal|z|453|[-10.17110027646537,10.171100276465362]|33.161440571174396|0.5044452899448088|1.0|
|zl1_alternative|x|447.6|[-0.028662222062427314,0.028662222062435]|20.750390719505912|0.513336578197937|1.0|
|zl1_alternative|x|448|[-0.028662222062423855,0.028662222062431533]|20.788935887400587|0.5289468517839109|1.0|
|zl1_alternative|x|450|[-0.028662222062431745,0.028662222062424098]|23.375753005284686|0.5682047914314201|1.0|
|zl1_alternative|x|453|[-9.066388337951864,9.066388337951857]|32.384078374844236|0.45787126113673965|1.0|
|zl1_alternative|z|447.6|[-0.028662222062427314,0.028662222062435]|20.61010532016579|0.6953900047587079|0.9999999999999999|
|zl1_alternative|z|448|[-0.028662222062423855,0.028662222062431533]|20.68380938643853|0.7006878057271251|1.0000000000000002|
|zl1_alternative|z|450|[-0.08598669487822448,-0.028662222062431745,0.028662222062424098,0.08598669487822448]|23.809131803535106|0.6965085880749147|1.0|
|zl1_alternative|z|453|[-9.472969778805565,9.472969778805558]|31.988606761077968|0.539394807845276|0.9999999999999999|

## Source weighting

The `wan_blue_gaussian_benchmark` uses a 450 nm center and 28 nm input FWHM. It is a common benchmark, not a measured Micro-LED spectrum.

|structure|captured fraction|weighted peak|weighted FWHM|integrated normalized output|weighted cone10 output|
|---|---:|---:|---:|---:|---:|
|bare|0.98836487|450.4|27.85727671480015|1.5493427|0.28919008|
|wan_proxy|0.98836487|449.4|18.716087085876268|0.38879571|0.21193368|
|explicit|0.98836487|448.6|13.030959537610329|0.26691022|0.16713256|
|zl1_nominal|0.98836487|448.4|13.286864544392756|0.33401253|0.21016513|
|zl1_alternative|0.98836487|448|13.26125576194596|0.33760018|0.21348373|

## Configuration and completion

- Actual monitor grid: 420-480 nm, 301 points; actual wavelengths and SHA256 are stored.
- Simulation time: 900 fs; retry ceiling: 1200 fs; autoshutoff target: 1e-7.
- Global dx 20 nm, stack dy 2 nm, source-local dx=dy 1 nm, r12 four-side box.
- Solver completion: 12/12 cases, 0 failed, 0 retry.
- Pilot: 4/4 passed; maximum 450-nm FWHM delta versus the 440-460 run is 0.231772 deg; maximum cone10 delta is 0.00284293.

## Strict FWHM definitions

|physical aperture|Explicit|ZL-1 nominal|ZL-1 alternative|Wan proxy|
|---|---:|---:|---:|---:|
|Native-M1 plane-wave TMM|7.4 nm|3.3 nm|3.3 nm|n/a|
|Native-M1 dipole-FDTD R12-normalized output|19.9312 nm|19.0227 nm|18.7821 nm|window truncated|
|28 nm Gaussian benchmark weighted output|13.0310 nm|13.2869 nm|13.2613 nm|18.7161 nm|

These three FWHM families are not interchangeable: plane-wave transmission, dipole-device output, and source-weighted output use different physical apertures.

## Device-level decision

The ZL-1 alternative has the best defect-MDC angle-power tradeoff: its mean 450-nm angular FWHM is narrower than nominal by 1.44243 deg, its r12-normalized output spectral FWHM is narrower by 0.240644 nm, and its integrated r12-normalized 420-480 power is 1.0206x nominal. No arbitrary composite score is used.

- Preferred candidate: ZL-1 alternative.
- Stable narrow-angle control: ZL-1 nominal.
- Traditional defect baseline: Explicit.
- Engineering proxy: Wan proxy.
- No-stack emission reference: Bare.

The formal stage status is `native_m1_2d_dipole_device_closure_pass`. The Wan-only unweighted FWHM remains `window_truncated` without extrapolation; Bare is `no_isolated_peak`; Explicit and both ZL-1 candidates have closed device-output FWHM.

Compared with the Wan proxy, the alternative is narrower in 450-nm angular FWHM and in the 28-nm weighted benchmark, while its integrated R12-normalized power is about 71.1% of Wan. Directional and spectral gains are supported; a throughput advantage is not. Compared with Bare, directionality improves substantially while integrated R12-normalized power decreases; this ratio is not called an absolute extraction-efficiency loss.

## ML labels

Subrun and candidate label files record the fixed-r12 method, common-radius convergence provenance, actual wavelength-grid hash, spectral/angular/power metrics, quality flags, and runtime FSP/log hashes. The existing 440-460 labels remain present.

All five structures use Native-M1 materials with no constant-index fallback. Runtime FSP/log files remain outside Git. No TMM, RCWA, or FMMAX was run. Raw monitor power is not called extraction efficiency.
