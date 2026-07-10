from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
C_M_PER_S = 299792458.0
TARGETS = ('SiO222', 'tio22')
DERIVED_GRIDS = {
    '300_1000nm_1nm': np.arange(300.0, 1000.0 + 0.01, 1.0),
    '400_500nm_0p5nm': np.arange(400.0, 500.0 + 0.001, 0.5),
    '448_453nm_0p5nm': np.arange(448.0, 453.0 + 0.001, 0.5),
}


def lumapi_from_runtime(runtime: Path):
    match = re.search(r'python_api_dir:\s*["\']?([^"\'\r\n]+)', runtime.read_text(encoding='utf-8'))
    if not match:
        raise RuntimeError(f'lumapi.python_api_dir missing: {runtime}')
    api_dir = Path(match.group(1).strip())
    if not api_dir.exists():
        raise RuntimeError(f'lumapi API directory missing: {api_dir}')
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))
    import lumapi  # type: ignore
    return lumapi


def resolve_fsp_candidates(raw: Path) -> list[Path]:
    if raw.is_file():
        return [raw]
    suffix_candidate = Path(str(raw) + '.fsp')
    if suffix_candidate.is_file():
        return [suffix_candidate]
    if raw.is_dir():
        all_files = sorted(raw.rglob('*.fsp'))
        preferred = [path for path in all_files if raw.name.casefold() in path.name.casefold()]
        return preferred + [path for path in all_files if path not in preferred]
    raise FileNotFoundError(f'FSP path not found: {raw}; also tried {suffix_candidate}')


def flatten_material_names(value) -> list[str]:
    if value is None:
        return []
    if hasattr(value, 'tolist'):
        return flatten_material_names(value.tolist())
    if isinstance(value, bytes):
        return flatten_material_names(value.decode(errors='replace'))
    if isinstance(value, str):
        return [item.strip() for item in value.splitlines() if item.strip()]
    if isinstance(value, (list, tuple)):
        return [name for item in value for name in flatten_material_names(item)]
    return [str(value).strip()]


def material_names(fdtd) -> list[str]:
    values = []
    try:
        values.append(fdtd.getmaterial())
    except Exception:
        pass
    try:
        fdtd.eval('material_ref_names=getmaterial;')
        values.append(fdtd.getv('material_ref_names'))
    except Exception:
        pass
    return list(dict.fromkeys(name for value in values for name in flatten_material_names(value) if name))


def find_fsp_with_materials(paths: list[Path], lumapi):
    inventories: dict[str, list[str]] = {}
    best: tuple[Path | None, list[str], int] = (None, [], -1)
    for path in paths:
        fdtd = None
        try:
            fdtd = lumapi.FDTD(hide=True)
            fdtd.load(str(path))
            names = material_names(fdtd)
            inventories[str(path)] = names
            score = sum(any(name.casefold() == target.casefold() for name in names) for target in TARGETS)
            if score > best[2]:
                best = (path, names, score)
            if score == len(TARGETS):
                return path, names, inventories
        except Exception as exc:
            inventories[str(path)] = [f'__open_error__: {exc}']
        finally:
            if fdtd is not None:
                try:
                    fdtd.close()
                except Exception:
                    pass
    if best[0] is None:
        raise RuntimeError('No candidate FSP could be opened in hidden lumapi mode')
    return best[0], best[1], inventories


def sampled_epsilon(fdtd, material: str) -> tuple[np.ndarray, np.ndarray]:
    """Return native sampled frequency and complex epsilon; no interpolation occurs here."""
    table = np.asarray(fdtd.getmaterial(material, 'sampled data'))
    if table.ndim != 2 or table.shape[1] < 2:
        raise RuntimeError(f'{material}: unexpected sampled data shape {table.shape}')
    frequency_hz = np.real(np.asarray(table[:, 0], dtype=np.complex128)).astype(float)
    if table.shape[1] == 2:
        epsilon = np.asarray(table[:, 1], dtype=np.complex128)
    else:
        epsilon = np.asarray(table[:, 1], dtype=np.complex128) + 1j * np.asarray(table[:, 2], dtype=np.complex128)
    order = np.argsort(frequency_hz)
    frequency_hz, epsilon = frequency_hz[order], epsilon[order]
    if not np.all(np.diff(frequency_hz) > 0):
        raise RuntimeError(f'{material}: native frequency grid is not strictly increasing')
    return frequency_hz, epsilon


def epsilon_to_index(epsilon: np.ndarray) -> np.ndarray:
    index = np.sqrt(np.asarray(epsilon, dtype=np.complex128))
    index[np.real(index) < 0] *= -1
    return index


def rows_from_native(source_fsp: Path, material: str, frequency_hz: np.ndarray, epsilon: np.ndarray) -> list[dict]:
    wavelength_nm = C_M_PER_S / frequency_hz * 1e9
    index = epsilon_to_index(epsilon)
    rows = []
    for f_hz, lam_nm, eps, nk in zip(frequency_hz, wavelength_nm, epsilon, index):
        rows.append({
            'source_fsp_path': str(source_fsp), 'material_name': material,
            'frequency_hz': float(f_hz), 'wavelength_nm': float(lam_nm),
            'epsilon_real': float(np.real(eps)), 'epsilon_imag': float(np.imag(eps)),
            'n_real': float(np.real(nk)), 'k_imag': float(np.imag(nk)),
            'data_kind': 'native_sampled', 'interpolation_method': 'none',
        })
    return rows


def bounded_interpolated_rows(source_fsp: Path, material: str, frequency_hz: np.ndarray, epsilon: np.ndarray, requested_wavelength_nm: np.ndarray, label: str) -> list[dict]:
    native_lambda_nm = C_M_PER_S / frequency_hz * 1e9
    lambda_min, lambda_max = float(native_lambda_nm.min()), float(native_lambda_nm.max())
    valid = requested_wavelength_nm[(requested_wavelength_nm >= lambda_min) & (requested_wavelength_nm <= lambda_max)]
    if valid.size == 0:
        return []
    request_frequency = C_M_PER_S / (valid * 1e-9)
    eps_re = np.interp(request_frequency, frequency_hz, np.real(epsilon))
    eps_im = np.interp(request_frequency, frequency_hz, np.imag(epsilon))
    eps = eps_re + 1j * eps_im
    index = epsilon_to_index(eps)
    return [{
        'source_fsp_path': str(source_fsp), 'material_name': material,
        'frequency_hz': float(f_hz), 'wavelength_nm': float(lam_nm),
        'epsilon_real': float(np.real(eps_value)), 'epsilon_imag': float(np.imag(eps_value)),
        'n_real': float(np.real(nk)), 'k_imag': float(np.imag(nk)),
        'data_kind': label, 'interpolation_method': 'linear_complex_epsilon_vs_frequency_within_native_range',
    } for f_hz, lam_nm, eps_value, nk in zip(request_frequency, valid, eps, index)]


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = ['source_fsp_path', 'material_name', 'frequency_hz', 'wavelength_nm', 'epsilon_real', 'epsilon_imag', 'n_real', 'k_imag', 'data_kind', 'interpolation_method']
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def ref_450(rows: list[dict], material: str) -> dict:
    value = next((row for row in rows if row['material_name'] == material and abs(row['wavelength_nm'] - 450.0) < 1e-9), None)
    return {'source_name': material, 'n_450': value['n_real'] if value else None, 'k_450': value['k_imag'] if value else None}


def write_report(path: Path, source_fsp: Path, found: dict[str, str], native_rows: list[dict], derived: dict[str, list[dict]]) -> None:
    lines = [
        '# MDC blue native material reference library', '',
        f'Actual FSP read: `{source_fsp}`', '',
        'Extraction was hidden-mode and read-only. No FDTD, GUI, FSP save, or FSP copy was performed.', '',
        '## Materials',
        f'- SiO222 actual name: {found.get("SiO222", "missing")}',
        f'- tio22 actual name: {found.get("tio22", "missing")}', '',
        '## Native sampled data',
        'The Lumerical `sampled data` property is a two-column complex-permittivity table `[frequency_hz, epsilon]`. `n + i k` is derived as the principal physical square root of complex epsilon.',
    ]
    for requested, actual in found.items():
        rows = [row for row in native_rows if row['material_name'] == actual]
        lines.append(f'- {requested} ({actual}): lambda_min={min(r["wavelength_nm"] for r in rows):.9g} nm; lambda_max={max(r["wavelength_nm"] for r in rows):.9g} nm; sample_count={len(rows)}')
    lines += ['', '## 450 nm reference']
    blue_rows = derived['448_453nm_0p5nm']
    for requested, actual in found.items():
        value = ref_450(blue_rows, actual)
        lines.append(f'- {requested} ({actual}): n={value["n_450"]:.9g}; k={value["k_450"]:.9g}')
    lines += [
        '', '## Derived tables',
        '- 300-1000 nm in 1 nm increments: exported only where the requested wavelength lies within the native range.',
        '- 400-500 nm and 448-453 nm in 0.5 nm increments: same bounded interpolation rule.',
        '- Interpolation is linear in real/imaginary epsilon on the native frequency axis. No native-range extrapolation is performed.',
        '', '## Comparison and branch use',
        '- Literature reference only: TiO2 n=2.25 @450 nm; SiO2 n=1.47 @450 nm. Use this FSP-derived material set as the APCD branch reference.',
        '- LP smoke may remain object-defined dielectric plus `n_material`; center it at TiO2_reference.n_450 and retain a local index sweep.',
        '- LP, MDC/TMM, and RCLED-MDC should reuse the unified config and native/derived CSVs emitted here.',
        '', 'No FDTD was run. No FSP or runtime configuration was modified.',
    ]
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description='Read-only native sampled-material export; never runs FDTD or saves FSP.')
    parser.add_argument('--fsp-path', default=r'F:\wc_312\MDC_blue_oujizi_m')
    parser.add_argument('--out-dir', default=str(ROOT / 'outputs' / 'material_reference' / 'mdc_blue_oujizi_m'))
    parser.add_argument('--runtime', default=str(ROOT / 'configs' / 'runtime.yaml'))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    lumapi = lumapi_from_runtime(Path(args.runtime))
    source_fsp, all_names, inventory = find_fsp_with_materials(resolve_fsp_candidates(Path(args.fsp_path)), lumapi)
    found = {target: next((name for name in all_names if name.casefold() == target.casefold()), None) for target in TARGETS}
    found = {key: value for key, value in found.items() if value}
    missing = [target for target in TARGETS if target not in found]

    native_rows: list[dict] = []
    derived = {label: [] for label in DERIVED_GRIDS}
    material_metadata = {}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=True)
        fdtd.load(str(source_fsp))
        for requested, actual in found.items():
            frequency_hz, epsilon = sampled_epsilon(fdtd, actual)
            native = rows_from_native(source_fsp, actual, frequency_hz, epsilon)
            native_rows.extend(native)
            lambda_nm = C_M_PER_S / frequency_hz * 1e9
            material_metadata[requested] = {
                'source_name': actual, 'native_property': 'sampled data', 'native_data_semantics': 'complex_permittivity_epsilon',
                'lambda_min_nm': float(lambda_nm.min()), 'lambda_max_nm': float(lambda_nm.max()), 'sample_count': int(len(native)),
            }
            for label, grid in DERIVED_GRIDS.items():
                derived[label].extend(bounded_interpolated_rows(source_fsp, actual, frequency_hz, epsilon, grid, label))
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass

    write_csv(out_dir / 'material_ref_native_sampled.csv', native_rows)
    for label, rows in derived.items():
        filename = 'material_ref_448_453.csv' if label == '448_453nm_0p5nm' else f'material_ref_interp_{label}.csv'
        write_csv(out_dir / filename, rows)
    payload = {
        'source_fsp_path': str(source_fsp), 'extraction_time': datetime.now(timezone.utc).isoformat(),
        'materials_found': found, 'missing_materials': missing, 'candidate_fsp_inventory': inventory,
        'native_material_metadata': material_metadata, 'native_samples': native_rows,
        'derived_tables': {label: {'sample_count': len(rows), 'interpolation_method': 'linear_complex_epsilon_vs_frequency_within_native_range'} for label, rows in derived.items()},
        'no_fdtd_run': True, 'no_fsp_saved_or_modified': True,
    }
    (out_dir / 'material_ref_native_sampled.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    # Keep the previous consumer path as a compact compatibility summary for the 448-453 nm derivative.
    (out_dir / 'material_ref_448_453.json').write_text(json.dumps({**payload, 'derived_rows': derived['448_453nm_0p5nm']}, indent=2), encoding='utf-8')

    blue_rows = derived['448_453nm_0p5nm']
    config = {
        'material_reference_id': 'mdc_blue_oujizi_m_fsp_material_db_native_sampled',
        'source_fsp_path': str(source_fsp), 'wavelength_nm': 450.0,
        'materials': {
            'SiO2_reference': ref_450(blue_rows, found['SiO222']) if 'SiO222' in found else None,
            'TiO2_reference': ref_450(blue_rows, found['tio22']) if 'tio22' in found else None,
        },
        'native_library': {
            'native_csv': 'outputs/material_reference/mdc_blue_oujizi_m/material_ref_native_sampled.csv',
            'native_json': 'outputs/material_reference/mdc_blue_oujizi_m/material_ref_native_sampled.json',
            'derived_csv': {
                '300_1000nm_1nm': 'outputs/material_reference/mdc_blue_oujizi_m/material_ref_interp_300_1000nm_1nm.csv',
                '400_500nm_0p5nm': 'outputs/material_reference/mdc_blue_oujizi_m/material_ref_interp_400_500nm_0p5nm.csv',
                '448_453nm_0p5nm': 'outputs/material_reference/mdc_blue_oujizi_m/material_ref_448_453.csv',
            },
            'interpolation_rule': 'linear complex epsilon versus frequency, bounded to native wavelength range; no extrapolation',
        },
        'recommended_usage': {
            'LP_ML': 'use TiO2_reference n_450 as measured/reference n_material center; keep index sweep around it',
            'MDC_TMM': 'use TiO2_reference and SiO2_reference for film stack baseline',
            'RCLED_MDC': 'use these as material set for top-filter/source-module audit',
        },
    }
    (ROOT / 'configs' / 'material_reference_apcd_blue.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    yaml_lines = [
        'material_reference_id: mdc_blue_oujizi_m_fsp_material_db_native_sampled',
        f'source_fsp_path: "{source_fsp}"', 'wavelength_nm: 450.0', 'materials:',
    ]
    for key, value in config['materials'].items():
        yaml_lines += [f'  {key}:', f'    source_name: "{value["source_name"]}"', f'    n_450: {value["n_450"]}', f'    k_450: {value["k_450"]}']
    yaml_lines += ['native_library:', f'  native_csv: "{config["native_library"]["native_csv"]}"', '  interpolation_rule: "linear complex epsilon versus frequency within native range; no extrapolation"']
    (ROOT / 'configs' / 'material_reference_apcd_blue.yaml').write_text('\n'.join(yaml_lines) + '\n', encoding='utf-8')
    write_report(ROOT / 'reports' / 'material_ref_mdc_blue_oujizi_m_report.md', source_fsp, found, native_rows, derived)
    print(json.dumps({'fsp_path_resolved': str(source_fsp), 'materials_found': found, 'missing_materials': missing, 'native_sample_count': len(native_rows), 'derived_counts': {key: len(value) for key, value in derived.items()}}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
