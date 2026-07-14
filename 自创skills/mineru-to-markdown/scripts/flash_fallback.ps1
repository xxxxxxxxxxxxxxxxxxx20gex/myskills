param(
    [Parameter(Mandatory = $true)]
    [string]$InputFile,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [string]$Language = "ch",
    [int]$Timeout = 900,
    [string]$MineruExe = ""
)

$ErrorActionPreference = "Stop"

$source = (Resolve-Path -LiteralPath $InputFile).Path
$output = [IO.Path]::GetFullPath($OutputDir)
New-Item -ItemType Directory -Force -Path $output | Out-Null

if (-not $MineruExe) {
    $userInstall = Join-Path $HOME ".mineru\bin\mineru-open-api.exe"
    if (Test-Path -LiteralPath $userInstall) {
        $MineruExe = $userInstall
    } else {
        $command = Get-Command mineru-open-api -ErrorAction Stop
        $MineruExe = $command.Source
    }
}

& $MineruExe flash-extract $source -o $output --language $Language --timeout $Timeout
if ($LASTEXITCODE -ne 0) {
    throw "MinerU flash-extract failed with exit code $LASTEXITCODE"
}

$markdown = Get-ChildItem -LiteralPath $output -Filter "*.md" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $markdown) {
    throw "flash-extract completed but no Markdown file was created in $output"
}

$content = Get-Content -Raw -LiteralPath $markdown.FullName
$matches = [regex]::Matches($content, '!\[[^\]]*\]\((images/[^)]+)\)')
$references = @()
foreach ($match in $matches) {
    $relative = $match.Groups[1].Value
    if ($references -notcontains $relative) {
        $references += $relative
    }
}

$recovered = 0
$recoveryStatus = "not-applicable"

if ([IO.Path]::GetExtension($source).ToLowerInvariant() -eq ".docx" -and $references.Count -gt 0) {
    $tempRoot = Join-Path $output ("_flash_recovery_" + [guid]::NewGuid().ToString("N"))
    $zipPath = Join-Path $tempRoot "source.zip"
    $extractPath = Join-Path $tempRoot "unpacked"
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

    try {
        Copy-Item -LiteralPath $source -Destination $zipPath
        Expand-Archive -LiteralPath $zipPath -DestinationPath $extractPath -Force
        $mediaDir = Join-Path $extractPath "word\media"
        $media = @(
            Get-ChildItem -LiteralPath $mediaDir -File |
                Sort-Object { [int]($_.BaseName -replace '\D', '') }
        )

        # Only recover when the one-to-one ordering is unambiguous.
        if ($media.Count -eq $references.Count) {
            for ($index = 0; $index -lt $references.Count; $index++) {
                $destination = Join-Path $output $references[$index]
                New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($destination)) | Out-Null
                Copy-Item -LiteralPath $media[$index].FullName -Destination $destination -Force
                $recovered++
            }
            $recoveryStatus = "complete"
        } else {
            $recoveryStatus = "skipped-count-mismatch"
        }
    } finally {
        if (Test-Path -LiteralPath $tempRoot) {
            Remove-Item -Recurse -Force -LiteralPath $tempRoot
        }
    }
}

$broken = 0
foreach ($relative in $references) {
    if (-not (Test-Path -LiteralPath (Join-Path $output $relative))) {
        $broken++
    }
}

Write-Output "FLASH_FALLBACK_USED=true"
Write-Output "MARKDOWN=$($markdown.FullName)"
Write-Output "IMAGE_REFERENCES=$($references.Count)"
Write-Output "IMAGES_RECOVERED=$recovered"
Write-Output "IMAGE_RECOVERY_STATUS=$recoveryStatus"
Write-Output "BROKEN_IMAGE_REFERENCES=$broken"
Write-Warning "MinerU flash fallback was used. This fast mode may not preserve precise tables, formulas, OCR, or complex layout. Tell the user explicitly that the result is a degraded fallback and report image recovery status."
