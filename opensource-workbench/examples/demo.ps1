param(
    [string]$OutputDirectory = 'review',
    [switch]$Offline
)

$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$cacheMode = @()
if ($Offline) { $cacheMode = @('--offline') }

function Invoke-Workbench {
    python -m workbench @cacheMode @args
    if ($LASTEXITCODE -ne 0) { throw '开源工作台命令失败。' }
}

function Invoke-FixtureGit {
    git -C $project @args
    if ($LASTEXITCODE -ne 0) { throw '演示项目 Git 命令失败。' }
}

if (Test-Path -LiteralPath $OutputDirectory) { throw '请指定新的演示输出目录。' }
$null = New-Item -ItemType Directory -Path $OutputDirectory
$project = Join-Path ([System.IO.Path]::GetTempPath()) ('workbench-demo-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $project
$manifest = @'
[project]
name = "slug-demo"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
]
'@
[System.IO.File]::WriteAllText((Join-Path $project 'pyproject.toml'), ($manifest -replace "\r\n", "`n") + "`n")
Invoke-FixtureGit -c core.hooksPath=NUL init -q
Invoke-FixtureGit -c core.hooksPath=NUL config user.name 'Workbench Demo'
Invoke-FixtureGit -c core.hooksPath=NUL config user.email 'demo@example.invalid'
Invoke-FixtureGit -c core.hooksPath=NUL -c core.autocrlf=false add -- pyproject.toml
Invoke-FixtureGit -c core.hooksPath=NUL -c commit.gpgSign=false commit -qm 'Create demo project'

Invoke-Workbench search --feature '把包含 Unicode 的标题转换成网址 slug' --keywords slugify `
    --language Python --platform Windows --project $project --limit 3 --out (Join-Path $OutputDirectory 'search.md')
Invoke-Workbench reuse-plan --repo un33k/python-slugify --ref f85f9488520148d5f6899b5639199882b605e30a `
    --keywords slugify --platform Windows --project $project --file slugify/slugify.py `
    --license-reviewed --branch workbench/slugify-demo --requirement 'python-slugify==8.0.4' `
    --release-tag v8.0.4 `
    --version-file slugify/__version__.py --version-evidence "__version__ = '8.0.4'" `
    --out (Join-Path $OutputDirectory 'reuse-plan.md') --patch (Join-Path $OutputDirectory 'reuse.patch')
Invoke-Workbench contribution-draft --repo Textualize/rich --ref 3a109ccdffe5b2d0e30684a304fbd388e99ce57b `
    --kind docs --keywords log_time_format --issue 3256 --evidence examples/rich-evidence.json --policy-reviewed `
    --out (Join-Path $OutputDirectory 'contribution-draft.md') --patch (Join-Path $OutputDirectory 'rich-docstring.patch')

Invoke-FixtureGit status --short --branch
Invoke-FixtureGit diff --check HEAD workbench/slugify-demo
Invoke-FixtureGit diff --stat HEAD workbench/slugify-demo
Write-Output "演示项目和隔离分支位于 $project"
