# MDC Native-M1 2D dipole broadband 440-460 v1

Status: `broadband_convergence_failed`.

The raw fixed-moment broadband spectra are valid. Emitted-normalized and stack-deembedded quantities remain diagnostic/invalid because the x-dipole canonical emitted-power gate is unresolved. No device-level throughput-improvement claim is made.

## Case completion

- completed/reused: 20/20
- failed: none

## Same-model raw comparison

|structure|raw peak (nm)|raw FWHM (nm)|x angular FWHM at 450|z angular FWHM at 450|
|---|---:|---:|---:|---:|
|bare|440|None|111.48027270761963|100.8019868623282|
|wan_proxy|440|None|37.77735618217474|29.46505841419888|
|explicit|447.8|None|26.83805141926323|25.926631225399632|
|zl1_nominal|447.6|None|24.87030239602432|25.044005258659787|
|zl1_alternative|447|None|23.293231924831815|23.80720457273695|

All raw/output FWHM values are `window_truncated`; no complete spectral FWHM is claimed from the 440-460 nm window. Stack-deembedded FWHM is also invalid because canonical emission normalization is unresolved.

## Broadband convergence

|structure|dipole|peak shift (nm)|angular FWHM change (deg)|cone10 change|FWHM comparable|peak set unchanged|status|
|---|---|---:|---:|---:|---|---|---|
|bare|x|0.0|0.00030155327240777297|1.0031972780266685e-08|False|True|fail|
|bare|z|0.0|1.765311863266561e-05|3.447232388431587e-09|False|True|fail|
|zl1_alternative|x|0.20000000000010232|0.23006231946389022|0.0016180473171066856|False|True|fail|
|zl1_alternative|z|0.0|0.15286304662304673|0.0007602562125854639|False|False|fail|

## 450 nm angular results

|structure|dipole|symmetry-aware peak set|FWHM (deg)|cone10|cone20|fraction sum|
|---|---|---|---:|---:|---:|---:|
|bare|x|[-4.217153126300967,4.217153126300967]|111.48027270761963|0.17581312988249673|0.3462747905376242|1.0|
|bare|z|[-4.102201414665178,4.10220141466517]|100.8019868623282|0.19719040067963572|0.3864691409749317|0.9999999999999998|
|zl1_alternative|x|[-0.028662222062431745,0.028662222062424098]|23.293231924831815|0.5710477231586767|0.7888793041700704|1.0|
|zl1_alternative|z|[-0.4299373477653126,-0.3726114977338847,-0.31528602070815925,0.3152860207081516,0.3726114977338771,0.4299373477653126]|23.80720457273695|0.6969639672230636|0.9432265894306566|1.0|
|wan_proxy|x|[-11.33810692536478,11.338106925364775]|37.77735618217474|0.4642626170425667|0.8952334248259507|0.9999999999999999|
|wan_proxy|z|[-8.892281211260178,8.892281211260178]|29.46505841419888|0.6266340551953055|0.9824292210007514|0.9999999999999999|
|explicit|x|[-0.028662222062431745,0.028662222062424098]|26.83805141926323|0.5772697626055628|0.8364599808413851|0.9999999999999998|
|explicit|z|[-3.699997581667268,3.69999758166726]|25.926631225399632|0.6764803053076847|0.946715072679318|1.0|
|zl1_nominal|x|[-0.028662222062431745,0.028662222062424098]|24.87030239602432|0.5745641584141243|0.8116581623562087|1.0|
|zl1_nominal|z|[-3.0683240071462246,3.068324007146217]|25.044005258659787|0.6867194440925974|0.9451993744159808|1.0000000000000002|

## Source weighting

The 440-460 nm window captures 59.965608% of the nominal 28 nm-FWHM Gaussian source. Gaussian-weighted results are `source_window_truncated`.

## Decision

The raw data support substantially narrower angular distributions for the defect-MDC candidates than Bare. The alternative has the narrowest 450 nm x-dipole angular FWHM among the three defect-MDC candidates. However broadband convergence and canonical emitted-power normalization remain unresolved, so throughput improvement and a final device winner are not claimed.

All five structures use Native-M1 materials, identical source/mesh/monitor settings, and x/z orientations. `wan_proxy` is an engineering proxy, not an exact reconstruction. Runtime FSP/log/checkpoint files remain outside Git.
