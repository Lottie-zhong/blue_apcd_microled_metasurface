Set-Location 'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1'
$d='reports/stage_h1f4b2a_combined_objective_aligned_forensic'
$s=Get-Content "$d/h1f4b2a_forensic_summary.json" -Raw|ConvertFrom-Json
if($s.solver_entered_delta -ne 0){throw 'solver delta'}
if($s.ml_admitted -ne $false){throw 'ml admission'}
if($s.historical_verdict -ne 'GROUPED_D_PLUS_J1_CANCELLATION_FAILED'){throw 'historical verdict'}
if($s.route -ne 'COMBINED_OBJECTIVE_RESPONSE_PARTIAL_BROADBAND_UNRESOLVED'){throw 'route'}
$n=@(Import-Csv "$d/baseline_plus_minus_delta_9point.csv"); if($n.Count -ne 36){throw "delta rows $($n.Count)"}
$c=@(Import-Csv "$d/desired_sign_map_9point.csv"); if($c.Count -ne 72){throw "class rows $($c.Count)"}
$a=@(Import-Csv "$d/absolute_objective_and_formal_metrics_9point.csv"); if($a.Count -ne 27){throw "absolute rows $($a.Count)"}
if(@($a|Where-Object {$_.directionality -eq 'NaN' -or $_.order_closure -eq 'NaN'}).Count){throw 'formal NaN'}
$m=@(Import-Csv "$d/model_breakdown.csv"); if($m.Count -ne 4 -or @($m|Where-Object {$_.point_count -ne 9}).Count){throw 'model rows'}
$p=@(Import-Csv "$d/pareto_comparison.csv"); if($p.Count -ne 10 -or @($p|Where-Object scope -eq '9_point_mean').Count -ne 1){throw 'pareto rows'}
$o=@(Import-Csv "$d/odd_even_decomposition_9point.csv"); if($o.Count -ne 36){throw 'odd even rows'}
Write-Output 'H1F4B2A_TEST_PASS'
