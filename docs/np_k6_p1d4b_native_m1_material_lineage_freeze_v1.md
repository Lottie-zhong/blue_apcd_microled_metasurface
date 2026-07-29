# NP P1-D4B Native-M1 material implementation lineage freeze v1

Canonical implementation is byte-exact to `06eb759`; data lineage is `5bd69e0` with the `c5fd999` Windows YAML fix. The authoritative entry points are `metasurface.apcd_material_library` and `metasurface.lumerical_native_materials`. P1-D2 identity remains TiO2 pillar + SiO2 substrate + Air background. Both pytest suites passed and the setup-only smoke registered/reloaded native sampled materials without invoking a solver. `scripts/apcd_native_materials.py` is legacy_not_authoritative.
