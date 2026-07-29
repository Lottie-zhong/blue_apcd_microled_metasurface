def test_run3b():
 from pathlib import Path
 assert (Path(__file__).resolve().parents[1]/'outputs/np_k6_p1d4b_k6x_transmission_candidate_run3b_freeze_v1/order_efficiency_spectrum.csv').exists()
