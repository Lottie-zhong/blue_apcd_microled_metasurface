# Deterministic, solver-free adapters for the V1 power interface.
import math

def _finite(value, name):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result

def _order_value(values, order, name):
    keys = [order, str(order)]
    if order > 0:
        keys.append(f"+{order}")
    for key in keys:
        if key in values:
            return _finite(values[key], f"{name}[{order}]")
    raise ValueError(f"{name} is missing diffraction order {order}")

def _strict_axis(axis, name):
    values = [_finite(v, name) for v in axis]
    if len(values) < 2 or any(b <= a for a, b in zip(values, values[1:])):
        raise ValueError(f"{name} must be strictly increasing")
    return values

def adapt_mdc_profile(record):
    required = ("mdc_geometry_hash","wavelength_nm","kx_over_k0","joint_weight","relative_upward_power","profile_sha","model_scope","source_aggregation_id")
    missing = [key for key in required if key not in record]
    if missing:
        raise ValueError(f"MDC record missing fields: {missing}")
    result = dict(record)
    for key in ("wavelength_nm","kx_over_k0","joint_weight","relative_upward_power"):
        result[key] = _finite(record[key], key)
    if result["joint_weight"] < 0 or result["relative_upward_power"] < 0:
        raise ValueError("MDC powers and weights must be non-negative")
    if "theta_air_deg" in record and record["theta_air_deg"] is not None:
        result["theta_air_deg"] = _finite(record["theta_air_deg"], "theta_air_deg")
    return result

def adapt_np_order_response(record, order=1):
    required = ("np_geometry_hash","wavelength_nm","kx_over_k0","polarization","eta_t_order","eta_r_order","T_total","R_total","theta_out_plus1","interface_stack_id","model_scope")
    missing = [key for key in required if key not in record]
    if missing:
        raise ValueError(f"NP record missing fields: {missing}")
    result = dict(record)
    for key in ("wavelength_nm","kx_over_k0","T_total","R_total","theta_out_plus1"):
        result[key] = _finite(record[key], key)
    result["eta_plus1"] = _order_value(record["eta_t_order"], order, "eta_t_order")
    _order_value(record["eta_r_order"], order, "eta_r_order")
    if result["T_total"] < 0 or result["R_total"] < 0 or result["eta_plus1"] < 0:
        raise ValueError("NP powers must be non-negative")
    if result["polarization"] not in {"x","y","p","s"}:
        raise ValueError("polarization must be an explicit x/y or p/s label")
    return result

def interpolate_no_extrapolation(x, source_x, source_y):
    x_value = _finite(x, "x")
    xs = _strict_axis(source_x, "source_x")
    ys = [_finite(v, "source_y") for v in source_y]
    if len(xs) != len(ys):
        raise ValueError("source_x and source_y must have equal length")
    if x_value < xs[0] or x_value > xs[-1]:
        raise ValueError("extrapolation is forbidden")
    if x_value == xs[-1]:
        return ys[-1]
    for left, right in zip(range(len(xs)-1), range(1, len(xs))):
        if xs[left] <= x_value <= xs[right]:
            fraction = (x_value-xs[left])/(xs[right]-xs[left])
            return ys[left] + fraction*(ys[right]-ys[left])
    raise RuntimeError("deterministic interpolation interval was not found")

def integrate_power(values, weights):
    if len(values) != len(weights) or not values:
        raise ValueError("values and weights must be non-empty and aligned")
    return math.fsum(_finite(v, "value")*_finite(w, "weight") for v, w in zip(values, weights))

def normalize_power(values):
    if not values:
        raise ValueError("values must be non-empty")
    clean = [_finite(v, "power") for v in values]
    if any(v < 0 for v in clean):
        raise ValueError("power must be non-negative")
    total = math.fsum(clean)
    if total <= 0:
        raise ValueError("power total must be positive")
    return [value/total for value in clean]
