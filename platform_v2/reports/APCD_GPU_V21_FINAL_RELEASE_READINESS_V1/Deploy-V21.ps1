param([ValidateSet('Verify','Apply','Rollback')][string]$Mode='Verify',[string]$Authorization='DENY',[string]$AclAuthorization='DENY',[string]$Backup)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$py='N:\anaconda_envs\RCP_LCP\python.exe'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root 'RELEASE_PACKAGE.zip')).Hash.ToLowerInvariant() -ne '3175fba5cf5ab4285174b351ba21a1dd9b19acab1ee69bb655be1427104998d0') {throw 'ARCHIVE_SHA_CHANGED'}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root 'v21_deployment_transaction.py')).Hash.ToLowerInvariant() -ne 'deaf6a41def1c623c193fb66981c771190a33c51d62ad6d6a6881dd593787fda') {throw 'TRANSACTION_SHA_CHANGED'}
if ($Mode -eq 'Apply' -and ($Authorization -ne 'APPROVE_V21_DISABLED_INSTALL_AND_OLD_TIMER_REBIND_ONLY' -or $AclAuthorization -ne 'APPROVE_V21_RUNTIME_ROOT_ACL_HARDENING_ONLY')) {throw 'SEPARATE_INSTALL_AND_ACL_AUTHORIZATION_REQUIRED'}
if ($Mode -eq 'Rollback' -and ($Authorization -ne 'APPROVE_V21_DISABLED_ROLLBACK_ONLY' -or -not $Backup)) {throw 'ROLLBACK_AUTHORIZATION_AND_BACKUP_REQUIRED'}
$package=Join-Path $root 'RELEASE_PACKAGE'
if (-not (Test-Path -LiteralPath $package)) {Expand-Archive -LiteralPath (Join-Path $root 'RELEASE_PACKAGE.zip') -DestinationPath $package}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $package 'PACKAGE_MANIFEST.json')).Hash.ToLowerInvariant() -ne 'c6649b9c072cd92714575ad6fc067b4cbeba974531d065c5b4dc53d98ebf4406') {throw 'PACKAGE_c6649b9c072cd92714575ad6fc067b4cbeba974531d065c5b4dc53d98ebf4406_CHANGED'}
$argv=@((Join-Path $root 'v21_deployment_transaction.py'),$Mode.ToLowerInvariant(),'--package',$package,'--package-sha256','c6649b9c072cd92714575ad6fc067b4cbeba974531d065c5b4dc53d98ebf4406','--authorization',$Authorization,'--acl-authorization',$AclAuthorization)
if ($Backup) {$argv+=@('--backup',$Backup)}
& $py @argv
if ($LASTEXITCODE -ne 0) {throw "Transaction failed: $LASTEXITCODE"}
