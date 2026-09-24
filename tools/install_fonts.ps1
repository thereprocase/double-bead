# Per-user install of the Beadjoint fonts (no admin): unload and unregister any earlier Beadjoint
# files, copy the current ones to the user font folder under a versioned name, register them in HKCU,
# load them into the session and broadcast WM_FONTCHANGE. Programs that read the font list only at
# start (Fusion) need a restart to see a new version.
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\install_fonts.ps1 -Version 1.101
param([string]$Version = "1.101", [string]$Source = "F:\code\beadjoint\fonts")
$dst = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
New-Item -ItemType Directory -Force -Path $dst | Out-Null
$key = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts'
Add-Type -Namespace W -Name F -MemberDefinition @'
[DllImport("gdi32.dll", CharSet = CharSet.Unicode)] public static extern int AddFontResourceW(string f);
[DllImport("gdi32.dll", CharSet = CharSet.Unicode)] public static extern bool RemoveFontResourceW(string f);
[DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern System.IntPtr SendMessageTimeoutW(System.IntPtr h, uint m, System.IntPtr w, System.IntPtr l, uint f, uint t, out System.IntPtr r);
'@
$map = [ordered]@{ 'Beadjoint-Regular.ttf' = 'Beadjoint (TrueType)'; 'BeadjointTab-Regular.ttf' = 'Beadjoint Tab (TrueType)'; 'BeadjointMono-Regular.ttf' = 'Beadjoint Mono (TrueType)' }
foreach ($f in $map.Keys) {
  $old = (Get-ItemProperty -Path $key -Name $map[$f] -ErrorAction SilentlyContinue).($map[$f])
  if ($old) {
    [W.F]::RemoveFontResourceW($old) | Out-Null
    Write-Output ("unloaded {0}" -f $old)
  }
  $target = Join-Path $dst ('v' + $Version + '-' + $f)
  Copy-Item (Join-Path $Source $f) $target -Force
  New-ItemProperty -Path $key -Name $map[$f] -Value $target -PropertyType String -Force | Out-Null
  $n = [W.F]::AddFontResourceW($target)
  Write-Output ("{0} -> {1} (loaded: {2})" -f $map[$f], $target, $n)
}
$r = [IntPtr]::Zero
[W.F]::SendMessageTimeoutW([IntPtr]0xffff, 0x1D, [IntPtr]::Zero, [IntPtr]::Zero, 2, 1000, [ref]$r) | Out-Null
Write-Output 'WM_FONTCHANGE broadcast'
