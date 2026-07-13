# MDC GaN Native-M1 extraction and deembedding audit v1

## Answers

1. Response is queried from the fixed Native-M1 source FSP, not newly fitted.
2. Measurement provenance cannot be proven from the available material metadata.
3. Blank-session response reproduction: `portable_response_roundtrip_pass`.
4. Bulk-GaN suitability remains unconfirmed: the object is named GaN but its physical role/provenance is not established.
5. At 450 nm, k=0.0841534686933; this implies strong propagation loss, not a lossless bulk-substrate assumption.
6. Phase A/B/C remain blocked.
7. User approval/provenance clarification is required before a policy can be frozen.
8. No solver execution occurred.

## Source

- `F:\wc_312\MDC_blue_oujizi_m\m_1.fsp`
- SHA256 `d7511bb92154152d5050d7ae664cb5b281ad3794a280129008359353b357e26f`, bytes `34241853`.

## Material metadata

- Geometry object/material assignment: `{'assigned_material': 'GaN', 'geometry_object': 'GaN'}`.
- Available metadata: `{'frequency max': 2297084192782163.0, 'frequency min': 302249748454938.6, 'sampled data': {'dtype': 'complex128', 'kind': 'ndarray', 'sha256': '906f2983665a51b748aa85ef85cd095550bb64a8ef77b8796e36a0b765407ef0', 'shape': [500, 2]}, 'tolerance': 0.1, 'type': 'Sampled 3D data'}`.
- API limitations: `[{'property': 'material type', 'reason': '"The material\'s material type property is not available."'}, {'property': 'reference', 'reason': '"The material\'s reference property is not available."'}, {'property': 'fit tolerance', 'reason': '"The material\'s fit tolerance property is not available."'}, {'property': 'fit range', 'reason': '"The material\'s fit range property is not available."'}, {'property': 'material database', 'reason': '"The material\'s material database property is not available."'}]`.

## Response and absorption

- 601 queried fitted/effective response points, 420-480 nm, 0.1 nm step.
- Critical n/k: 448 nm (2.41774622366, 0.0846828744691), 450 nm (2.41494647635, 0.0841534686933), 453 nm (2.41088392741, 0.083391833341).
- 450 nm absorption: `{'wavelength_nm': '450.0', 'k_imag': '0.0841534686933', 'absorption_coefficient_m_inv': '2350008.16908', 'absorption_coefficient_cm_inv': '23500.0816908', 'intensity_remaining_100nm': '0.790570203806', 'intensity_remaining_400nm': '0.390626558933', 'intensity_remaining_1um': '0.0953683831409'}`.

## Decision

- Status: `portable_response_found_but_bulk_substrate_physics_unconfirmed`.
- Candidate response is not declared measured, bulk-correct, or frozen.
- `gan_candidate_policy.json` is null.

## Deembedding

- Formal comparison requires matched homogeneous-GaN reference-plane deembedding; bare GaN/Air remains an independent control.
- A lossless n=2.41 TMM comparison must carry `material_model_mismatch_present`.

## Safety

- Only material metadata/index queries and blank-session sampled-data registration were used; no solver execution or project save.
