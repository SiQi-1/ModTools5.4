param(
  [Parameter(Mandatory = $true)][int]$X,
  [Parameter(Mandatory = $true)][int]$Y,
  [int]$Hwnd = 0,
  [string]$Label = ""
)
# 简单的 Windows 鼠标点击（屏幕坐标；若给 Hwnd 则把 X,Y 当作客户区坐标并在其上叠加窗口客户区原点）
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Win32Click {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, IntPtr dwExtraInfo);
    [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr hWnd, ref POINT lpPoint);
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X; public int Y; }
    public const uint LEFTDOWN = 0x0002;
    public const uint LEFTUP = 0x0004;
}
"@
[void][Win32Click]::SetProcessDPIAware()
$sx = $X; $sy = $Y
if ($Hwnd -ne 0) {
    $pt = New-Object Win32Click+POINT
    $pt.X = $X; $pt.Y = $Y
    [void][Win32Click]::ClientToScreen([IntPtr]$Hwnd, [ref]$pt)
    $sx = $pt.X; $sy = $pt.Y
}
[void][Win32Click]::SetCursorPos($sx, $sy)
Start-Sleep -Milliseconds 120
[Win32Click]::mouse_event([Win32Click]::LEFTDOWN, 0, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 80
[Win32Click]::mouse_event([Win32Click]::LEFTUP, 0, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 250
Write-Host ("clicked screen=({0},{1}) client=({2},{3}) hwnd={4} {5}" -f $sx, $sy, $X, $Y, $Hwnd, $Label)
