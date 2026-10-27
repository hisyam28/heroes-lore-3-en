$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$javaExe = Join-Path $projectRoot 'work/android-tools/jdk/jdk-21.0.13.0.2+1/bin/java.exe'
$sdkTools = Join-Path $projectRoot 'work/android-tools/build-tools/android-16'
$signerJar = Join-Path $sdkTools 'lib/apksigner.jar'
$passwordFile = Join-Path $projectRoot 'work/heroes-lore-3-signing-password.txt'
$keystore = Join-Path $projectRoot 'work/heroes-lore-3-local.keystore'
$unsignedApk = Join-Path $projectRoot 'work/heroes-lore-3-en-optimized-unsigned.apk'
$alignedApk = Join-Path $projectRoot 'work/heroes-lore-3-en-optimized-aligned.apk'
$signedApk = Join-Path $projectRoot 'work/heroes-lore-3-en-optimized.apk'
$baselineApk = Join-Path $projectRoot 'work/heroes-lore-3-final.apk'

function Assert-Command([string] $description) {
    if ($LASTEXITCODE -ne 0) { throw "$description failed with exit code $LASTEXITCODE" }
}

python -B tools/hl3_curate_optimized.py
Assert-Command 'UI/dialogue curation'
python -B tools/hl3_curate_quests.py
Assert-Command 'Quest curation'
python -B tools/hl3_probe_font.py
Assert-Command 'ARM font regression/benchmark'
python -B tools/hl3_build_optimized.py
Assert-Command 'Resource and native profile build'
python -B tools/hl3_layout_qa.py
Assert-Command 'Panel layout QA'
python -B tools/hl3_probe_home.py
Assert-Command 'Native settings and actual ARM slot-row QA'
python -B tools/hl3_regression_checks.py
Assert-Command 'Failure-mode regressions'
& (Join-Path $sdkTools 'zipalign.exe') -f -P 16 4 $unsignedApk $alignedApk
Assert-Command 'ZIP alignment'
$previousSigningPassword = $env:HL3_OPTIMIZED_KEYSTORE_PASSWORD
try {
    # The existing password file was written with a UTF-8 BOM. ReadAllText
    # handles that BOM; apksigner's file: password source treats it as password
    # characters and cannot unlock the existing keystore.
    $env:HL3_OPTIMIZED_KEYSTORE_PASSWORD = [System.IO.File]::ReadAllText($passwordFile).TrimEnd([char[]]"`r`n")
    & $javaExe -jar $signerJar sign --ks $keystore --ks-pass env:HL3_OPTIMIZED_KEYSTORE_PASSWORD --key-pass env:HL3_OPTIMIZED_KEYSTORE_PASSWORD --v1-signing-enabled false --v2-signing-enabled true --v3-signing-enabled true --v4-signing-enabled false --out $signedApk $alignedApk
    Assert-Command 'APK signing'
}
finally {
    $env:HL3_OPTIMIZED_KEYSTORE_PASSWORD = $previousSigningPassword
}
& (Join-Path $sdkTools 'zipalign.exe') -c -P 16 4 $signedApk
Assert-Command 'Signed APK alignment check'
& $javaExe -jar $signerJar verify --verbose $signedApk
Assert-Command 'APK signature verification'
$oldCert = & $javaExe -jar $signerJar verify --print-certs $baselineApk
Assert-Command 'Baseline signer inspection'
$newCert = & $javaExe -jar $signerJar verify --print-certs $signedApk
Assert-Command 'New signer inspection'
$oldDigest = @($oldCert | Where-Object { $_ -match '^Signer #1 certificate SHA-256 digest:' })
$newDigest = @($newCert | Where-Object { $_ -match '^Signer #1 certificate SHA-256 digest:' })
if ($oldDigest.Count -ne 1 -or $newDigest.Count -ne 1 -or $oldDigest[0] -ne $newDigest[0]) {
    throw 'The APK signer differs from the previous final build'
}
python -B tools/hl3_verify_optimized.py $signedApk
Assert-Command 'Signed artifact invariants'
& (Join-Path $sdkTools 'aapt.exe') dump badging $signedApk | Select-Object -First 8
Assert-Command 'Android package inspection'
Write-Output "Signed optimized APK: $signedApk"
Write-Output 'Signer matches the previous final build.'
