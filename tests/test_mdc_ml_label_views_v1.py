import csv, json, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREP = ROOT / "datasets" / "mdc_ml_database_v1_prepared"

def read(name):
    with (PREP / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

class LabelViewsV1Test(unittest.TestCase):
    def test_cardinality_and_roles(self):
        tmm = read("tmm_canonical_spectral_labels.csv")
        ang = read("tmm_angular_sparse_labels.csv")
        tol = read("tolerance_robustness_labels.csv")
        fdtd = read("fdtd_external_reference_labels.csv")
        self.assertEqual(len(tmm), 2688)
        self.assertEqual(len(ang), 2688)
        self.assertEqual(len(tol), 8400)
        self.assertEqual(len(fdtd), 11)
        self.assertEqual(len({r["geometry_hash"] for r in tmm}), 2688)
        self.assertEqual({r["sample_role"] for r in tmm}, {"canonical_tmm_sweep"})
        self.assertEqual({r["sample_role"] for r in tol}, {"tolerance_perturbation"})
        self.assertEqual({r["sample_role"] for r in fdtd}, {"fdtd_external_high_fidelity_reference"})

    def test_topology_and_sparse_labels(self):
        tmm = read("tmm_canonical_spectral_labels.csv")
        ang = read("tmm_angular_sparse_labels.csv")
        from collections import Counter
        self.assertEqual(Counter(r["topology_family"] for r in tmm), {"Explicit":1848,"ZL-1":630,"ZL-2":210})
        self.assertEqual(sum(r["has_angular_fwhm_label"].lower() == "true" for r in ang), 15)
        self.assertEqual(sum(r["has_max_angle_label"].lower() == "true" for r in ang), 2)
        self.assertTrue(all(r["angular_missing_reason"] in ("", "not_computed") for r in ang))
        self.assertTrue(all(r["tmm_angular_FWHM_450_deg"] != "0" for r in ang if r["has_angular_fwhm_label"].lower() == "true"))

    def test_no_cross_role_leakage_and_manifest(self):
        tmm = read("tmm_canonical_spectral_labels.csv")
        tol = read("tolerance_robustness_labels.csv")
        fdtd = read("fdtd_external_reference_labels.csv")
        self.assertTrue(all(r["source_id"] in {"tmm_coarse","tmm_refined"} for r in tmm))
        self.assertTrue(all(r["usable_for_training"].lower() == "true" for r in tmm))
        self.assertTrue(all(r["usable_for_training"].lower() == "false" for r in tol))
        self.assertTrue(all(r["sample_role"] != "canonical_tmm_sweep" for r in fdtd))
        self.assertTrue(all("geometry_master.is_nominal_geometry" not in r for r in tmm))
        manifest=json.loads((PREP/"manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["view_counts"]["tmm_canonical_spectral_labels"],2688)
        self.assertEqual(manifest["label_coverage"]["angular_FWHM"],15)
        self.assertEqual(manifest["label_coverage"]["maximum_angle"],2)

if __name__ == "__main__": unittest.main()
