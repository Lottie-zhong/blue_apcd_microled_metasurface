"""Read-only shared-server admission; no solver, process control or global controller."""
import csv
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time


def command(args):
    p = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
    if p.returncode:
        raise RuntimeError('Monitor failed: ' + str(args[0]) + ': ' + p.stderr[:500])
    return p.stdout.strip().lstrip('\ufeff')


def rows(text):
    return list(csv.reader(io.StringIO(text)))


def snapshot(output_dir):
    # Windows WDDM lists graphics applications as C+G in nvidia-smi. A GUI name
    # alone is not evidence of a competing solver. Inspect GPU engine contexts.
    ps = r'''$ErrorActionPreference='Stop'; $eng=@(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine); $os=Get-CimInstance Win32_OperatingSystem; $cpu=Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'"; $tasks=@(Get-ScheduledTask | Where-Object {$_.TaskName -in @('APCD_GPU_V2_SERIAL_CONTROLLER','APCD_GPU_RUNNER_V1_COUPLING_SERIAL_QUEUE_CONTROLLER','APCD_GPU_RUNNER_V1_SINGLE_CASE_WORKER')}); [pscustomobject]@{engine_count=$eng.Count;compute_contexts=@($eng | Where-Object {$_.Name -match 'engtype_(Compute|Cuda)' } | Select Name,UtilizationPercentage);ram_free_mib=([double]$os.FreePhysicalMemory/1024);cpu_load_pct=$cpu.PercentProcessorTime;cpu_threads=[int]$env:NUMBER_OF_PROCESSORS;legacy_tasks=@($tasks | Select TaskName,@{n='enabled';e={$_.Settings.Enabled}},@{n='running';e={"$($_.State)" -eq 'Running'}})} | ConvertTo-Json -Depth 7 -Compress'''
    samples = []
    for i in range(2):
        gpu = rows(command(['nvidia-smi','--query-gpu=uuid,name,memory.total,memory.used,utilization.gpu','--format=csv,noheader,nounits']))
        apps = rows(command(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader']))
        windows = json.loads(command(['powershell','-NoProfile','-Command',ps]))
        if len(gpu) != 1 or len(gpu[0]) != 5:
            raise RuntimeError('Expected one monitored GPU; device attribution unknown')
        g = gpu[0]
        samples.append(dict(gpu_uuid=g[0].strip(), gpu_name=g[1].strip(), gpu_free_mib=float(g[2])-float(g[3]), gpu_utilization_pct=float(g[4]), gpu_apps=apps, windows=windows))
        if i == 0:
            time.sleep(1)
    ancestor = Path(output_dir).resolve()
    while not ancestor.exists():
        ancestor = ancestor.parent
    return dict(samples=samples, disk_free_gib=shutil.disk_usage(ancestor).free / (1024**3), sampled_unix=time.time())


def evaluate(evidence, requirements, policy, licenses):
    reasons = []
    required = ('gpu_free_mib','ram_free_mib','disk_free_gib','cpu_threads','license_features')
    if not isinstance(requirements, dict) or any(k not in requirements for k in required):
        return ['Per-job resource_requirements are required for real admission']
    for key in required[:-1]:
        v = requirements[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            reasons.append('Invalid positive resource requirement: ' + key)
    features = requirements['license_features']
    if not isinstance(features, dict) or not features:
        reasons.append('Explicit license feature quantities required')
    else:
        for name, count in features.items():
            if not re.fullmatch(r'[A-Za-z0-9_\-]+', name) or type(count) is not int or count <= 0:
                reasons.append('Invalid license feature quantity')
            elif licenses.get(name, -1) < count:
                reasons.append('License unavailable or unconfirmed: ' + name)
    if reasons:
        return reasons
    if len(evidence.get('samples', [])) < 2 or abs(time.time()-evidence.get('sampled_unix', 0)) > 60:
        return ['Resource samples missing or stale']
    for sample in evidence['samples']:
        w = sample['windows']
        measured = [sample['gpu_free_mib'],sample['gpu_utilization_pct'],w['ram_free_mib'],w['cpu_load_pct'],w['cpu_threads']]
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v < 0 for v in measured) or not 0 <= w['cpu_load_pct'] <= 100 or w['cpu_threads'] == 0:
            reasons.append('System resource measurements unknown or invalid')
            continue
        if sample['gpu_uuid'] != policy['gpu_uuid']:
            reasons.append('GPU identity mismatch')
        if sample['gpu_utilization_pct'] > policy.get('max_gpu_utilization_pct',20):
            reasons.append('GPU busy; arrange shared use before admission')
        if not w['engine_count']:
            reasons.append('Windows GPU attribution unavailable')
        if w['compute_contexts']:
            # A resident compute context is retained even at instantaneous 0%.
            reasons.append('Existing GPU compute context; arrange shared use before admission')
        for app in sample['gpu_apps']:
            if len(app) != 2:
                reasons.append('GPU process attribution malformed')
            elif re.search(r'(fdtd-engine|fdtd-engine-gpu|optiengine|python|cuda)', app[1], re.I):
                reasons.append('GPU compute process present: PID ' + app[0].strip())
        tasks = w['legacy_tasks']
        if len(tasks) != 3 or any(t['enabled'] or t['running'] for t in tasks):
            reasons.append('APCD legacy GPU Scheduler isolation not confirmed')
        if sample['gpu_free_mib'] < requirements['gpu_free_mib']:
            reasons.append('Insufficient GPU memory')
        if w['ram_free_mib'] < requirements['ram_free_mib']:
            reasons.append('Insufficient system RAM')
        if w['cpu_threads'] * (1-w['cpu_load_pct']/100) < requirements['cpu_threads']:
            reasons.append('Insufficient estimated CPU headroom')
    if evidence['disk_free_gib'] < requirements['disk_free_gib']:
        reasons.append('Insufficient output disk space')
    return sorted(set(reasons))


def license_free(policy):
    text = command([policy['lmutil'], 'lmstat', '-a', '-c', policy['license_server']])
    matches = re.findall(r'Users of ([\w-]+):\s*\(Total of (\d+) licenses? issued;\s*Total of (\d+) licenses? in use\)', text)
    if not matches:
        raise RuntimeError('License availability could not be parsed')
    return {name:int(total)-int(used) for name,total,used in matches}


def check(requirements, output_dir, policy):
    evidence = snapshot(output_dir)
    licenses = license_free(policy)
    reasons = evaluate(evidence, requirements, policy, licenses)
    evidence['license_free'] = licenses
    evidence['hold_reasons'] = reasons
    return evidence
