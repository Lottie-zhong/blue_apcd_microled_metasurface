# Native-M1 Bare/FAB 2D FDTD

Runtime comparison only; raw monitor power is not extraction efficiency. Center x-dipole at 450 nm; finite-window layered approximation, not mesa-edge or x/y average.
{
  "runs": [
    {
      "case_id": "BARE_GAN_AIR_450_XDIPOLE",
      "raw_upward_monitor_power": 0.22409532134303092,
      "absolute_extraction_status": "pending",
      "monitor_fields": "lambda;f;T;Lumerical_dataset",
      "sampled_tio2_count": 0,
      "sampled_sio2_count": 0,
      "layer_count": 0,
      "total_thickness_nm": 0,
      "peak_angle_deg": 4.217153126300966,
      "angular_fwhm_deg": 128.04064424876947,
      "eta10": 0.17192451010866155,
      "eta20": 0.33927167718662854,
      "leakage20_40": 0.6310724629398361,
      "leakage40_60": 0.7504190683639258,
      "normal_to_40_60_ratio": 1.4913978348106744
    },
    {
      "case_id": "EX_N3_L79_H45_C156_450_XDIPOLE",
      "raw_upward_monitor_power": 0.06402855404792016,
      "absolute_extraction_status": "pending",
      "monitor_fields": "lambda;f;T;Lumerical_dataset",
      "sampled_tio2_count": 101,
      "sampled_sio2_count": 101,
      "layer_count": 13,
      "total_thickness_nm": 900,
      "peak_angle_deg": -0.028662222062431738,
      "angular_fwhm_deg": 26.784439586577335,
      "eta10": 0.5696100886667886,
      "eta20": 0.828995633161451,
      "leakage20_40": 0.303176476695724,
      "leakage40_60": 0.0882754109786645,
      "normal_to_40_60_ratio": 39.488771635465405
    }
  ],
  "comparison": {
    "fab_sequence": "L79 H45 L79 H45 L79 H45 C156 H45 L79 H45 L79 H45 L79",
    "fab_layers": 13,
    "fab_thickness_nm": 900,
    "power_ratio_fab_to_bare": 0.2857201732913884,
    "material_registration": "PASS"
  }
}
## Angular metric audit

The original implementation integrated over degree values and used overlapping/incorrect masks. Corrected fractions use radians, full-domain trapezoidal normalization, mutually exclusive masks, and ratio remains a separate mean-intensity metric.
{
  "EX_N3_L79_H45_C156_450_XDIPOLE": {
    "angle_min_deg": -90.0,
    "angle_max_deg": 90.0,
    "point_count": 2000,
    "total_integral": 0.017453292519943292,
    "fractions": {
      "eta10": 0.5696100886667887,
      "eta20": 0.8289956331614512,
      "leakage20_40": 0.08179514301726298,
      "leakage40_60": 0.028363794713740745,
      "residual60_plus": 0.06084542910754525,
      "fraction_sum": 1.569610088666789
    },
    "normal_to_40_60_ratio": 39.488771635465405,
    "peak_angle_deg": -0.028662222062431738,
    "angular_fwhm_deg": 26.839293080632455,
    "finite": true
  },
  "BARE_GAN_AIR_450_XDIPOLE": {
    "angle_min_deg": -90.0,
    "angle_max_deg": 90.0,
    "point_count": 2000,
    "total_integral": 0.017453292519943295,
    "fractions": {
      "eta10": 0.17192451010866155,
      "eta20": 0.33927167718662854,
      "leakage20_40": 0.302626016798074,
      "leakage40_60": 0.22696547951489748,
      "residual60_plus": 0.13113682650039996,
      "fraction_sum": 1.1719245101086617
    },
    "normal_to_40_60_ratio": 1.4913978348106744,
    "peak_angle_deg": 4.217153126300966,
    "angular_fwhm_deg": 128.15517920447604,
    "finite": true
  }
}
## Angular metric audit

The original implementation integrated over degree values and used overlapping/incorrect masks. Corrected fractions use radians, full-domain trapezoidal normalization, mutually exclusive masks, and ratio remains a separate mean-intensity metric.
{
  "EX_N3_L79_H45_C156_450_XDIPOLE": {
    "angle_min_deg": -90.0,
    "angle_max_deg": 90.0,
    "point_count": 2000,
    "total_integral": 0.017453292519943292,
    "fractions": {
      "eta10": 0.5696100886667887,
      "eta20": 0.8289956331614512,
      "annulus10_20": 0.25938554449466245,
      "leakage20_40": 0.08179514301726298,
      "leakage40_60": 0.028363794713740745,
      "residual60_plus": 0.06084542910754525,
      "fraction_sum": 1.0000000000000002
    },
    "normal_to_40_60_ratio": 39.488771635465405,
    "peak_angle_deg": -0.028662222062431738,
    "angular_fwhm_deg": 26.839293080632455,
    "finite": true
  },
  "BARE_GAN_AIR_450_XDIPOLE": {
    "angle_min_deg": -90.0,
    "angle_max_deg": 90.0,
    "point_count": 2000,
    "total_integral": 0.017453292519943295,
    "fractions": {
      "eta10": 0.17192451010866155,
      "eta20": 0.33927167718662854,
      "annulus10_20": 0.16734716707796696,
      "leakage20_40": 0.302626016798074,
      "leakage40_60": 0.22696547951489748,
      "residual60_plus": 0.13113682650039996,
      "fraction_sum": 0.9999999999999999
    },
    "normal_to_40_60_ratio": 1.4913978348106744,
    "peak_angle_deg": 4.217153126300966,
    "angular_fwhm_deg": 128.15517920447604,
    "finite": true
  }
}