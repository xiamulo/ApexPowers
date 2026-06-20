$env:APEXPOWERS_ROOT = $PSScriptRoot
python (Join-Path $PSScriptRoot "src/apexpowers_cli/cli.py") @args
