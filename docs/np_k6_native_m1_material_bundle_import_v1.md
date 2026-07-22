# NP-K6 Native-M1 Material Bundle Import Audit V1

## Source and closure
YAML source: c5fd9990f7d5e9fa385ef71fdeff3f5791b8c06b:configs/material_reference_apcd_blue.yaml | SHA256 59FAB53B4261CF86B789681D80D7545BAABA70DCC6692A03E9CE543C71FE8FC4 | 547 bytes.
JSON source: 40dedf4098fa0ca19e0e5f0e3395e73fb4949c53:configs/material_reference_apcd_blue.json | SHA256 CE174A40D8FB0F4380551F44F1B2D93351A579662F220458E057A298AFD5205F | 1418 bytes.
Helper source: 40dedf4098fa0ca19e0e5f0e3395e73fb4949c53:scripts/apcd_native_materials.py | SHA256 937EB5A29022E97659FB2F6E6F40552AF154868A1DF0D01A93E76A3A72B4FCBD | 8622 bytes.
Policy source: 40dedf4098fa0ca19e0e5f0e3395e73fb4949c53:configs/mdc_defect_450_material_policy.json | SHA256 CF9EA2303C91E71A4C92821EA4E88A10DCB9D1592F8401BD8B396A81C2CFB0C5 | 3264 bytes.
CSV source: 40dedf4098fa0ca19e0e5f0e3395e73fb4949c53:outputs/material_reference/mdc_blue_oujizi_m/material_ref_native_sampled_mdc_native_m1.csv | SHA256 3F924764311CAB5FB824F229A26870ECA65F22F05419B985047F151529230EDB | 63623 bytes.
The exact CSV path is policy.reference.native_sampled_csv; the helper reads it as sampled complex epsilon over frequency_hz.

## Dependency audit
The helper imports only Python stdlib modules and numpy; it has no local-project Python import. It reads only configs/mdc_defect_450_material_policy.json, which then requires the listed CSV. No second mandatory configuration or CSV was found.
configs/mdc_defect_450_material_policy.yaml was not imported because the helper explicitly reads the JSON policy path only.

## Semantics and validation
Policy mapping verified: APCD_TIO2_NATIVE_M1 -> tio22; APCD_SIO2_NATIVE_M1 -> sio222; APCD_GAN_NATIVE_M1 -> GaN.
Policy verified: complex_epsilon, frequency_hz, linear interpolation, extrapolation forbidden. Helper explicitly has no constant-index fallback.
PyYAML, JSON parse, helper AST, external-temporary py_compile, CSV schema/readability, and safe importlib smoke all passed.
Smoke loaded only policy and CSV parsing: IDs APCD_GAN_NATIVE_M1/APCD_SIO2_NATIVE_M1/APCD_TIO2_NATIVE_M1; rows 500/101/101; frequency range 2.9015875218919056e14 to 2.297084192782163e15 Hz.
YAML was imported from the c5fd999 YAML-path-quoting repair. FSP F:\wc_312\MDC_blue_oujizi_m\m_1.fsp was checked for existence only.

## Scope
No NP branch-private material model was created. No policy YAML, FSP, runtime, log, solver output, or unrelated MDC file was imported.
No FDTD, RCWA, lumapi, or other optical simulation was run.
