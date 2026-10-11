# V3 two-anchor complete-axis plan

- A1: K6GDP2_DEV_G001 = [120, 160, 165, 175, 160, 195] nm; DEVELOPMENT_GLOBAL.
- A2: K6GDP2_DEV_G004 = [210, 115, 175, 115, 180, 125] nm; DEVELOPMENT_GLOBAL.

A1: nearest fixed domain center; A2: maximum normalized separation fromA1 among full-axis eligible truth-valid nonS31 nonlocal anchors. Selection uses geometry and source-validity only, not heldout error/routing. Each has D1..D6 both +/-5nm, 12cases/anchor, all24pair-complete. Sourceanchors retain fixedphysicalcontract and oldtruthSHA. New32/56 scientific identities do not replay S31 D6_M05.

Four sealedlocal combinations: each anchor +/-[5,5,-5,-5,5,-5]nm inall6coordinates. These are interaction checks, nottraining. Canonical full6D span is only sampled at axis/endpoints and2combineddirections; cannot infer arbitraryinteraction smoothness. Full-axiscentral differences are retrospective only afterlegaldevelopment truth, and laterCV sensitivities/preprocessing fit train-only.

Existing S31 has11validpoints/D6_M05missing; unchanged. Newanchors test crossanchor reproducibility and all6 sensitivity axes, not proof of whole6D generalization. No independentrun noise floor yet.
