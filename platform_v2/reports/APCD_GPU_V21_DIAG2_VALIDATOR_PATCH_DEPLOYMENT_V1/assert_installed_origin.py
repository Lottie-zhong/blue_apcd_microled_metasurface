import importlib, json, os
from pathlib import Path
def pytest_configure(config):
    expected=Path(os.environ["APCD_RELEASE_ROOT"]).resolve()
    names=["apcd_gpu_v2","apcd_gpu_v2.diag2","apcd_gpu_v2.serial","apcd_gpu_v2.gpu_readonly"]
    origins={}
    for name in names:
        module=importlib.import_module(name)
        actual=Path(module.__file__).resolve()
        actual.relative_to(expected)
        origins[name]=str(actual)
    Path(os.environ["APCD_REPORT_DIR"],"INSTALLED_MODULE_ORIGINS.json").write_text(json.dumps({"release_root":str(expected),"modules":origins},indent=2),encoding="utf-8")
