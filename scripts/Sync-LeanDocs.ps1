param([string]$ProjectRoot = 'C:\Projects\Film_TV_participation_dynamic_DSL')
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$manifest = Get-Content -LiteralPath (Join-Path $repoRoot 'docs\lean-resources.json') -Raw | ConvertFrom-Json
$docsRoot = Join-Path $ProjectRoot 'reference\lean4'
New-Item -ItemType Directory -Path $docsRoot -Force | Out-Null
$records = @()
function Invoke-GitChecked {
    param([string[]]$GitArgs)
    & git @GitArgs
    if ($LASTEXITCODE -ne 0) { throw "Git failed: $($GitArgs -join ' ')" }
}
foreach ($resource in $manifest.resources) {
    $destination = Join-Path $docsRoot $resource.directory
    if (-not (Test-Path -LiteralPath $destination)) {
        Invoke-GitChecked -GitArgs @('init', $destination)
        Invoke-GitChecked -GitArgs @('-C', $destination, 'remote', 'add', 'origin', $resource.repository)
        Invoke-GitChecked -GitArgs @('-C', $destination, 'fetch', '--depth', '1', 'origin', $resource.revision)
        if ($env:OS -eq 'Windows_NT' -and $resource.directory -eq 'functional-programming') {
            # AUX is a reserved Windows filename. Its Git object remains available.
            Invoke-GitChecked -GitArgs @('-C', $destination, '-c', 'core.protectNTFS=false', 'sparse-checkout', 'set', '--no-cone', '/*', '!/examples/second-lake/greeting/Aux.lean')
            Invoke-GitChecked -GitArgs @('-C', $destination, '-c', 'core.protectNTFS=false', 'checkout', '--detach', 'FETCH_HEAD')
        } else {
            Invoke-GitChecked -GitArgs @('-C', $destination, 'checkout', '--detach', 'FETCH_HEAD')
        }
    }
    $actualRevision = & git -C $destination rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $actualRevision -ne $resource.revision) { throw "Unexpected revision at $destination; inspect before updating." }
    $actualOrigin = & git -C $destination remote get-url origin
    if ($LASTEXITCODE -ne 0 -or $actualOrigin -ne $resource.repository) { throw "Unexpected origin at $destination." }
    $changes = & git -C $destination status --porcelain
    if ($LASTEXITCODE -ne 0 -or $changes) { throw "Modified reference checkout: $destination" }
    $toolchainFile = Join-Path $destination 'lean-toolchain'
    if (-not (Test-Path -LiteralPath $toolchainFile)) { $toolchainFile = Join-Path $destination 'book\lean-toolchain' }
    $toolchain = if (Test-Path -LiteralPath $toolchainFile) { (Get-Content -LiteralPath $toolchainFile -Raw).Trim() } else { $null }
    [string[]]$excluded = @()
    if ($env:OS -eq 'Windows_NT' -and $resource.directory -eq 'functional-programming') { $excluded = @('examples/second-lake/greeting/Aux.lean') }
    $records += [ordered]@{ directory = $resource.directory; repository = $resource.repository; revision = $actualRevision; website = $resource.website; documentationToolchain = $toolchain; excludedWorkingTreePaths = $excluded }
}
[ordered]@{
    verifiedAtUtc = [DateTime]::UtcNow.ToString('o')
    projectToolchain = (Get-Content -LiteralPath (Join-Path $repoRoot 'lean-toolchain') -Raw).Trim()
    format = 'Upstream sources, readable offline; not rendered website mirrors'
    resources = $records
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $docsRoot 'snapshot.json') -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $repoRoot 'docs\lean-resources.md') -Destination (Join-Path $docsRoot 'README.md') -Force
Write-Output "Verified Lean documentation in $docsRoot"
