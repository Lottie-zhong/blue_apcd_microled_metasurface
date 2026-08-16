Set-Location 'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1'
$d='reports/lp_branch_2026_08_16_formal_closeout'
$required=@('01_CURRENT_STATUS.md','02_STAGE_INVENTORY.csv','03_PHYSICS_CONCLUSIONS.md','04_QUANTITATIVE_EVIDENCE.md','05_DATASET_REGISTRY_INVENTORY.csv','06_ML_MODEL_ARCHIVE.md','07_PAPER_A_HANDOFF.md','08_REMOTE_WORKFLOW.md','09_SCHEDULER_AUTHORITY.md','10_REOPEN_CONDITIONS.md','11_PROVENANCE_MANIFEST.json','12_FILE_HASHES.csv')
foreach($f in $required){if(!(Test-Path "$d/$f")){throw "missing $f"}}
$s=Get-Content "$d/11_PROVENANCE_MANIFEST.json" -Raw|ConvertFrom-Json;if($s.scheduler_cap -ne 3){throw 'scheduler cap'};if($s.solver_entered_delta -ne 0){throw 'solver delta'};if($s.ml_training_delta -ne 0){throw 'training delta'}
$st=Import-Csv "$d/02_STAGE_INVENTORY.csv";if(@($st|Group-Object stage_id|Where-Object Count -gt 1).Count){throw 'duplicate stage id'}
$ds=Import-Csv "$d/05_DATASET_REGISTRY_INVENTORY.csv";if(@($ds|Where-Object {$_.dataset_id -eq 'K6_FULLWAVE_REGISTRY' -and $_.geometry_space -like '*local*'}).Count){throw 'registry mixing'}
if($s.lp_k6_status -notin @('PAUSED_ARCHIVED')){throw 'active K6'};if($s.lp_ml_status -notin @('PAUSED_ARCHIVED')){throw 'active ML'}
$hashRows=Import-Csv "$d/12_FILE_HASHES.csv";foreach($r in $hashRows){$p=$r.path.Replace('/','\');$actual=(Get-FileHash -Algorithm SHA256 $p).Hash;if($actual -ne $r.sha256){throw "hash mismatch $($r.path)"}}
Write-Output "LP_CLOSEOUT_TEST_PASS stages=$($st.Count) datasets=$($ds.Count)"
