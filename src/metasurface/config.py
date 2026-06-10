from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

import yaml


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    stage: str


@dataclass(frozen=True)
class TargetConfig:
    wavelength_nm: float
    incident_wave: str
    incident_polarization: str
    output_polarization: str
    deflection_angle_deg: float
    target_order: str


@dataclass(frozen=True)
class MaterialConfig:
    metasurface: str
    metasurface_index: float | None = None


@dataclass(frozen=True)
class GeometryConfig:
    supercell_atoms: int
    atom_period_nm: float
    supercell_period_um: float


@dataclass(frozen=True)
class NanofinGeometryConfig:
    period_nm: float
    length_nm: float
    width_nm: float
    height_nm: float
    rotation_deg: float


@dataclass(frozen=True)
class PBSupercellGeometryConfig:
    atom_period_nm: float
    atoms: int
    length_nm: float
    width_nm: float
    height_nm: float
    rotation_start_deg: float
    rotation_step_deg: float


@dataclass(frozen=True)
class APCDNanopillarConfig:
    length_nm: float
    width_nm: float
    x_nm: float
    y_nm: float
    rotation_deg: float
    frac_x: float | None = None
    frac_y: float | None = None
    rotation_rule: str | None = None
    role: str | None = None
    shape: str = "rectangle"
    corner_radius_nm: float | None = None
    chamfer_nm: float | None = None
    notch_depth_nm: float | None = None
    notch_width_nm: float | None = None
    notch_side: str | None = None
    polygon_sides: int = 32


@dataclass(frozen=True)
class APCDDimerGeometryConfig:
    layout_mode: str
    period_x_nm: float
    period_y_nm: float
    height_nm: float
    nanopillar_1: APCDNanopillarConfig
    nanopillar_2: APCDNanopillarConfig
    nanopillar_helper: APCDNanopillarConfig | None = None
    minimum_gap_nm: float = 5.0


@dataclass(frozen=True)
class APCDDimerMaterialConfig:
    substrate: str
    meta_material: str
    substrate_material_lumerical: str
    meta_material_lumerical: str
    substrate_index: float | None = None
    meta_index: float | None = None


@dataclass(frozen=True)
class APCDDimerTargetConfig:
    wavelength_nm: float
    incident_wave: str
    output_basis: str
    eps: float
    spin_er_threshold_db: float
    conversion_to_leakage_threshold: float
    target_polarization_type: str = "circular"
    psi_deg: float | None = None
    chi_deg: float | None = None


@dataclass(frozen=True)
class APCDDimerSimulationConfig:
    substrate_thickness_nm: float
    source_offset_nm: float
    monitor_offset_nm: float
    z_padding_above_nm: float
    mesh_accuracy: int
    simulation_time_fs: float


@dataclass(frozen=True)
class FarFieldConfig:
    projection_direction: str
    material_index: str
    far_field_filter: int
    resolution_2d: int
    resolution_3d: int
    assume_structure_is_periodic: bool
    illumination: str
    override_near_field_mesh: bool
    near_field_samples_per_wavelength: int


@dataclass(frozen=True)
class PhaseDesignConfig:
    method: str
    phase_step_rad: float
    rotation_step_deg: float


@dataclass(frozen=True)
class ThicknessSweepConfig:
    h_min_nm: int
    h_max_nm: int
    h_step_nm: int
    h_initial_nm: int


@dataclass(frozen=True)
class OutputConfig:
    result_dir: Path


@dataclass(frozen=True)
class RuntimeConfig:
    mode: str
    enable_lumerical: bool
    lumapi_python_api_dir: str
    hide_gui: bool


@dataclass(frozen=True)
class PlaneWaveSweepConfig:
    project: ProjectConfig
    target: TargetConfig
    material: MaterialConfig
    geometry: GeometryConfig
    phase_design: PhaseDesignConfig
    thickness_sweep: ThicknessSweepConfig
    output: OutputConfig


@dataclass(frozen=True)
class NanofinSingleConfig:
    project: ProjectConfig
    target: TargetConfig
    material: MaterialConfig
    geometry: NanofinGeometryConfig
    far_field: FarFieldConfig
    output: OutputConfig


@dataclass(frozen=True)
class PBSupercellConfig:
    project: ProjectConfig
    target: TargetConfig
    material: MaterialConfig
    geometry: PBSupercellGeometryConfig
    far_field: FarFieldConfig
    output: OutputConfig


@dataclass(frozen=True)
class APCDSingleDimerConfig:
    project: ProjectConfig
    target: APCDDimerTargetConfig
    material: APCDDimerMaterialConfig
    geometry: APCDDimerGeometryConfig
    simulation: APCDDimerSimulationConfig
    output: OutputConfig


def load_sweep_config(path: Union[str, Path]) -> PlaneWaveSweepConfig:
    data = _read_yaml_mapping(path)
    return PlaneWaveSweepConfig(
        project=ProjectConfig(**_required_mapping(data, "project")),
        target=TargetConfig(**_required_mapping(data, "target")),
        material=MaterialConfig(**_required_mapping(data, "material")),
        geometry=GeometryConfig(**_required_mapping(data, "geometry")),
        phase_design=PhaseDesignConfig(**_required_mapping(data, "phase_design")),
        thickness_sweep=ThicknessSweepConfig(**_required_mapping(data, "thickness_sweep")),
        output=OutputConfig(result_dir=Path(_required_mapping(data, "output")["result_dir"])),
    )


def load_nanofin_single_config(path: Union[str, Path]) -> NanofinSingleConfig:
    data = _read_yaml_mapping(path)
    return NanofinSingleConfig(
        project=ProjectConfig(**_required_mapping(data, "project")),
        target=TargetConfig(**_required_mapping(data, "target")),
        material=MaterialConfig(**_required_mapping(data, "material")),
        geometry=NanofinGeometryConfig(**_required_mapping(data, "geometry")),
        far_field=FarFieldConfig(**_required_mapping(data, "far_field")),
        output=OutputConfig(result_dir=Path(_required_mapping(data, "output")["result_dir"])),
    )


def load_pb_supercell_config(path: Union[str, Path]) -> PBSupercellConfig:
    data = _read_yaml_mapping(path)
    return PBSupercellConfig(
        project=ProjectConfig(**_required_mapping(data, "project")),
        target=TargetConfig(**_required_mapping(data, "target")),
        material=MaterialConfig(**_required_mapping(data, "material")),
        geometry=PBSupercellGeometryConfig(**_required_mapping(data, "geometry")),
        far_field=FarFieldConfig(**_required_mapping(data, "far_field")),
        output=OutputConfig(result_dir=Path(_required_mapping(data, "output")["result_dir"])),
    )


def load_apcd_single_dimer_config(path: Union[str, Path]) -> APCDSingleDimerConfig:
    data = _read_yaml_mapping(path)
    target_data = _required_mapping(data, "target")
    geometry_data = _required_mapping(data, "geometry")
    layout_mode = str(geometry_data.get("layout_mode", "manual_absolute"))
    period_x_nm = float(geometry_data["period_x_nm"])
    period_y_nm = float(geometry_data["period_y_nm"])
    geometry = APCDDimerGeometryConfig(
        layout_mode=layout_mode,
        period_x_nm=period_x_nm,
        period_y_nm=period_y_nm,
        height_nm=float(geometry_data["height_nm"]),
        nanopillar_1=_load_apcd_nanopillar(
            geometry_data,
            "nanopillar_1",
            layout_mode=layout_mode,
            period_x_nm=period_x_nm,
            period_y_nm=period_y_nm,
            target_data=target_data,
        ),
        nanopillar_2=_load_apcd_nanopillar(
            geometry_data,
            "nanopillar_2",
            layout_mode=layout_mode,
            period_x_nm=period_x_nm,
            period_y_nm=period_y_nm,
            target_data=target_data,
        ),
        nanopillar_helper=_load_optional_apcd_nanopillar(
            geometry_data,
            "nanopillar_helper",
            layout_mode=layout_mode,
            period_x_nm=period_x_nm,
            period_y_nm=period_y_nm,
            target_data=target_data,
        ),
        minimum_gap_nm=float(geometry_data.get("minimum_gap_nm", 5.0)),
    )
    return APCDSingleDimerConfig(
        project=ProjectConfig(**_required_mapping(data, "project")),
        target=APCDDimerTargetConfig(
            wavelength_nm=float(target_data["wavelength_nm"]),
            incident_wave=str(target_data["incident_wave"]),
            output_basis=str(target_data["output_basis"]),
            eps=float(target_data.get("eps", 1.0e-12)),
            spin_er_threshold_db=float(target_data.get("spin_er_threshold_db", 8)),
            conversion_to_leakage_threshold=float(target_data.get("conversion_to_leakage_threshold", 6)),
            target_polarization_type=str(target_data.get("target_polarization_type", "circular")),
            psi_deg=_optional_float(target_data.get("psi_deg")),
            chi_deg=_optional_float(target_data.get("chi_deg")),
        ),
        material=APCDDimerMaterialConfig(**_required_mapping(data, "material")),
        geometry=geometry,
        simulation=APCDDimerSimulationConfig(**_required_mapping(data, "simulation")),
        output=OutputConfig(result_dir=Path(_required_mapping(data, "output")["result_dir"])),
    )


def _load_apcd_nanopillar(
    geometry_data: dict[str, Any],
    key: str,
    *,
    layout_mode: str,
    period_x_nm: float,
    period_y_nm: float,
    target_data: dict[str, Any],
) -> APCDNanopillarConfig:
    pillar_data = _required_mapping(geometry_data, key)
    frac_x = _optional_float(pillar_data.get("frac_x"))
    frac_y = _optional_float(pillar_data.get("frac_y"))
    if layout_mode == "apcd_fractional":
        if frac_x is None or frac_y is None:
            raise ValueError(f"{key} requires frac_x and frac_y for apcd_fractional layout")
        x_nm = (frac_x - 0.5) * period_x_nm
        y_nm = (frac_y - 0.5) * period_y_nm
    elif layout_mode == "manual_absolute":
        x_nm = float(pillar_data["x_nm"])
        y_nm = float(pillar_data["y_nm"])
    else:
        raise ValueError(f"Unsupported APCD layout_mode: {layout_mode}")

    rotation_rule = pillar_data.get("rotation_rule")
    if rotation_rule is None:
        rotation_deg = float(pillar_data.get("rotation_deg", 0.0))
    else:
        rotation_deg = _resolve_apcd_rotation_deg(str(rotation_rule), target_data, key)

    return APCDNanopillarConfig(
        length_nm=float(pillar_data["length_nm"]),
        width_nm=float(pillar_data["width_nm"]),
        x_nm=x_nm,
        y_nm=y_nm,
        rotation_deg=rotation_deg,
        frac_x=frac_x,
        frac_y=frac_y,
        rotation_rule=None if rotation_rule is None else str(rotation_rule),
        role=_optional_str(pillar_data.get("role", pillar_data.get("helper_role"))),
        shape=str(pillar_data.get("shape", "rectangle")),
        corner_radius_nm=_optional_float(pillar_data.get("corner_radius_nm")),
        chamfer_nm=_optional_float(pillar_data.get("chamfer_nm")),
        notch_depth_nm=_optional_float(pillar_data.get("notch_depth_nm")),
        notch_width_nm=_optional_float(pillar_data.get("notch_width_nm")),
        notch_side=_optional_str(pillar_data.get("notch_side")),
        polygon_sides=int(pillar_data.get("polygon_sides", 32)),
    )


def _load_optional_apcd_nanopillar(
    geometry_data: dict[str, Any],
    key: str,
    *,
    layout_mode: str,
    period_x_nm: float,
    period_y_nm: float,
    target_data: dict[str, Any],
) -> APCDNanopillarConfig | None:
    if key not in geometry_data or geometry_data[key] is None:
        return None
    return _load_apcd_nanopillar(
        geometry_data,
        key,
        layout_mode=layout_mode,
        period_x_nm=period_x_nm,
        period_y_nm=period_y_nm,
        target_data=target_data,
    )


def _resolve_apcd_rotation_deg(rotation_rule: str, target_data: dict[str, Any], key: str) -> float:
    psi_deg = _optional_float(target_data.get("psi_deg"))
    if psi_deg is None:
        raise ValueError(f"{key} rotation_rule={rotation_rule} requires target.psi_deg")
    if rotation_rule == "psi":
        return psi_deg
    if rotation_rule == "psi_minus_45":
        return psi_deg - 45
    raise ValueError(f"Unsupported APCD rotation_rule for {key}: {rotation_rule}")


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def load_runtime_config(path: Union[str, Path]) -> RuntimeConfig:
    data = _read_yaml_mapping(path)
    runtime = _required_mapping(data, "runtime")
    lumapi = _required_mapping(data, "lumapi")
    return RuntimeConfig(
        mode=str(runtime.get("mode", "")),
        enable_lumerical=bool(runtime.get("enable_lumerical", False)),
        lumapi_python_api_dir=str(lumapi.get("python_api_dir", "")),
        hide_gui=bool(lumapi.get("hide_gui", True)),
    )


def _read_yaml_mapping(path: Union[str, Path]) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {config_path}")
    return data


def _required_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Missing required mapping section: {key}")
    return value
