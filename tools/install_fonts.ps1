# Per-user install of the Fillaprint fonts (no admin): unload and unregister any earlier install
# (including the Beadjoint-named ones up to v1.101), copy the current files to the user font folder under
# a versioned name, register them in HKCU, load them into the session and broadcast WM_FONTCHANGE.
# Programs that read the font list only at start (Fusion) need a restart to see a new version.
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\install_fonts.ps1 -Version 0.100
param([string]$Version = "0.100", [string]$Source = (Join-Path $PSScriptRoot '..\fonts'))
$dst = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
New-Item -ItemType Directory -Force -Path $dst | Out-Null
$key = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts'
Add-Type -Namespace W -Name F -MemberDefinition @'
[DllImport("gdi32.dll", CharSet = CharSet.Unicode)] public static extern int AddFontResourceW(string f);
[DllImport("gdi32.dll", CharSet = CharSet.Unicode)] public static extern bool RemoveFontResourceW(string f);
[DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern System.IntPtr SendMessageTimeoutW(System.IntPtr h, uint m, System.IntPtr w, System.IntPtr l, uint f, uint t, out System.IntPtr r);
'@

# the working name until v1.101: unload, unregister and delete those installs and any older versioned copies
foreach ($legacy in 'Beadjoint (TrueType)', 'Beadjoint Tab (TrueType)', 'Beadjoint Mono (TrueType)',
                    'Double bead (TrueType)', 'Double bead Tab (TrueType)', 'Double bead Mono (TrueType)') {
  $old = (Get-ItemProperty -Path $key -Name $legacy -ErrorAction SilentlyContinue).$legacy
  if ($old) {
    [W.F]::RemoveFontResourceW($old) | Out-Null
    Remove-ItemProperty -Path $key -Name $legacy
    Write-Output ("unregistered {0}" -f $legacy)
  }
}
Get-ChildItem -Path $dst -Filter 'v*-Beadjoint*-Regular.ttf' -ErrorAction SilentlyContinue | ForEach-Object {
  [W.F]::RemoveFontResourceW($_.FullName) | Out-Null
  Remove-Item $_.FullName -ErrorAction SilentlyContinue
  Write-Output ("deleted {0}" -f $_.Name)
}

$map = [ordered]@{ 'Fillaprint-Regular.ttf' = 'Fillaprint (TrueType)'; 'FillaprintTab-Regular.ttf' = 'Fillaprint Tab (TrueType)'; 'FillaprintMono-Regular.ttf' = 'Fillaprint Mono (TrueType)' }
foreach ($f in $map.Keys) {
  $target = Join-Path $dst ('v' + $Version + '-' + $f)
  $old = (Get-ItemProperty -Path $key -Name $map[$f] -ErrorAction SilentlyContinue).($map[$f])
  if ($old) {
    [W.F]::RemoveFontResourceW($old) | Out-Null
    if ($old -ne $target) { Remove-Item $old -ErrorAction SilentlyContinue }
    Write-Output ("unloaded {0}" -f $old)
  }
  Copy-Item (Join-Path $Source $f) $target -Force
  New-ItemProperty -Path $key -Name $map[$f] -Value $target -PropertyType String -Force | Out-Null
  $n = [W.F]::AddFontResourceW($target)
  Write-Output ("{0} -> {1} (loaded: {2})" -f $map[$f], $target, $n)
}
$r = [IntPtr]::Zero
[W.F]::SendMessageTimeoutW([IntPtr]0xffff, 0x1D, [IntPtr]::Zero, [IntPtr]::Zero, 2, 1000, [ref]$r) | Out-Null
Write-Output 'WM_FONTCHANGE broadcast'
