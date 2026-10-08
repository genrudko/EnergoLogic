# EnergoLogic P0-B - standalone TEST overlay for an already-open desktop Visio.
# Usage (Windows PowerShell 5.1, same user/integrity as Visio):
# powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File .\p0b_live_overlay_probe.ps1
# Experimental ONLY. Never saves, edits, or closes a Visio document.
# No network access. Writes diagnostic JSONL only to %TEMP%.
param(
    [string]$DocumentName = 'EnergoLogic_Protection_Live_Test_20261008.vsdm',
    [string]$PageName = 'MCP-v2',
    [int]$BreakerId = 66,
    [int]$BusId = 101
)

$ErrorActionPreference = 'Stop'
if ([System.Threading.Thread]::CurrentThread.GetApartmentState().ToString() -ne 'STA') {
    throw 'Run with powershell.exe -STA (COM and Windows Forms require single-threaded apartment).'
}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$source = @'
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using System.Collections.Generic;
using System.Text;

namespace EnergoLogicP0B
{
    public struct P { public int X; public int Y; }
    public struct R { public int Left; public int Top; public int Right; public int Bottom; }

    public sealed class ChildRect
    {
        public string WindowClass { get; set; }
        public int Left { get; set; }
        public int Top { get; set; }
        public int Width { get; set; }
        public int Height { get; set; }
    }

    public static class Native
    {
        [DllImport("user32.dll", SetLastError=true)]
        public static extern bool ClientToScreen(IntPtr hwnd, ref P pt);
        [DllImport("user32.dll", SetLastError=true)]
        public static extern bool GetClientRect(IntPtr hwnd, out R rect);
        [DllImport("user32.dll", SetLastError=true)]
        public static extern bool IsWindow(IntPtr hwnd);
        [DllImport("user32.dll")]
        public static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")]
        public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint processId);
        [DllImport("user32.dll")]
        public static extern uint GetDpiForWindow(IntPtr hwnd);
        [UnmanagedFunctionPointer(CallingConvention.Winapi)]
        public delegate bool EnumWindowsProc(IntPtr hwnd, IntPtr lParam);
        [DllImport("user32.dll")]
        private static extern bool EnumChildWindows(IntPtr parent, EnumWindowsProc callback, IntPtr lParam);
        [DllImport("user32.dll", CharSet=CharSet.Unicode)]
        private static extern int GetClassName(IntPtr hwnd, StringBuilder builder, int capacity);
        [DllImport("user32.dll")]
        private static extern bool IsWindowVisible(IntPtr hwnd);

        // Read-only HWND geometry survey; no foreground changes or Visio mutation.
        public static ChildRect[] InspectChildWindows(IntPtr parent)
        {
            List<ChildRect> children = new List<ChildRect>();
            EnumWindowsProc callback = (hwnd, param) => {
                if (!IsWindowVisible(hwnd)) return true;
                R bounds;
                if (!GetClientRect(hwnd, out bounds)) return true;
                int width = bounds.Right - bounds.Left;
                int height = bounds.Bottom - bounds.Top;
                if (width < 200 || height < 200) return true;
                P origin = new P();
                if (!ClientToScreen(hwnd, ref origin)) return true;
                StringBuilder buffer = new StringBuilder(128);
                GetClassName(hwnd, buffer, buffer.Capacity);
                children.Add(new ChildRect {
                    WindowClass = buffer.ToString(),
                    Left = origin.X,
                    Top = origin.Y,
                    Width = width,
                    Height = height
                });
                return true;
            };
            EnumChildWindows(parent, callback, IntPtr.Zero);
            return children.ToArray();
        }
        public static IntPtr FromVisioHandle(int handle32) {
            return new IntPtr((long)unchecked((uint)handle32));
        }
    }

    public sealed class ProbeOverlay : Form
    {
        public PointF BreakerPoint { get; private set; }
        public PointF BusLeft { get; private set; }
        public PointF BusRight { get; private set; }
        public ProbeOverlay()
        {
            FormBorderStyle = FormBorderStyle.None;
            ShowInTaskbar = false;
            TopMost = true;
            StartPosition = FormStartPosition.Manual;
            BackColor = Color.FromArgb(1, 2, 3);
            TransparencyKey = BackColor;
            DoubleBuffered = true;
        }
        protected override CreateParams CreateParams
        {
            get {
                CreateParams cp = base.CreateParams;
                cp.ExStyle |= 0x20 | 0x80000 | 0x08000000 | 0x80;
                return cp; // WS_EX_TRANSPARENT | LAYERED | NOACTIVATE | TOOLWINDOW
            }
        }
        protected override bool ShowWithoutActivation { get { return true; } }
        public void UpdateVisual(Rectangle screenBounds, PointF breaker, PointF busL, PointF busR)
        {
            if (screenBounds.Width < 40 || screenBounds.Height < 40) {
                Hide();
                return;
            }
            // Avoid periodic full-screen layered repaints while the
            // viewport remains stationary (previously blinked at 400 ms).
            if (Visible && Bounds.Equals(screenBounds) &&
                Math.Abs(BreakerPoint.X - breaker.X) < 0.35f &&
                Math.Abs(BreakerPoint.Y - breaker.Y) < 0.35f &&
                Math.Abs(BusLeft.X - busL.X) < 0.35f &&
                Math.Abs(BusLeft.Y - busL.Y) < 0.35f &&
                Math.Abs(BusRight.X - busR.X) < 0.35f &&
                Math.Abs(BusRight.Y - busR.Y) < 0.35f) {
                return;
            }
            Bounds = screenBounds;
            BreakerPoint = breaker;
            BusLeft = busL;
            BusRight = busR;
            if (!Visible) Show();
            Invalidate();
        }
        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            Graphics g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            using (Pen p = new Pen(Color.FromArgb(255, 255, 0, 180), 4f))
            {
                p.StartCap = LineCap.Round;
                p.EndCap = LineCap.Round;
                g.DrawLine(p, BusLeft, BusRight);
            }
            using (Pen p = new Pen(Color.FromArgb(255, 0, 210, 255), 2.5f))
            {
                p.DashStyle = DashStyle.Dash;
                g.DrawEllipse(p, BreakerPoint.X - 18f, BreakerPoint.Y - 18f, 36f, 36f);
                g.DrawLine(p, BreakerPoint.X - 25f, BreakerPoint.Y, BreakerPoint.X + 25f, BreakerPoint.Y);
                g.DrawLine(p, BreakerPoint.X, BreakerPoint.Y - 25f, BreakerPoint.X, BreakerPoint.Y + 25f);
            }
        }
    }
}
'@
Add-Type -TypeDefinition $source -Language CSharp -ReferencedAssemblies @('System.Windows.Forms.dll', 'System.Drawing.dll')

# No new document, no COM mutation; acquire the already running Visio.
$visio = [Runtime.InteropServices.Marshal]::GetActiveObject('Visio.Application')
$log = Join-Path $env:TEMP ('EnergoLogic_P0B_viewport_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.jsonl')
$script:overlay = New-Object EnergoLogicP0B.ProbeOverlay
$script:lastLog = [DateTime]::MinValue
$script:lastError = ''
$script:done = $false
$script:tickCount = 0

$controller = New-Object System.Windows.Forms.Form
$controller.Text = 'EnergoLogic P0-B — проверка наложения'
$controller.StartPosition = 'CenterScreen'
$controller.Size = New-Object System.Drawing.Size(520, 190)
$controller.TopMost = $true
$controller.FormBorderStyle = 'FixedDialog'
$controller.MaximizeBox = $false
$controller.MinimizeBox = $false
$lbl = New-Object System.Windows.Forms.Label
$lbl.Location = New-Object System.Drawing.Point(14, 15)
$lbl.Size = New-Object System.Drawing.Size(485, 90)
$lbl.Text = 'Подключение к Visio...'
$controller.Controls.Add($lbl)
$stop = New-Object System.Windows.Forms.Button
$stop.Text = 'Завершить проверку'
$stop.Location = New-Object System.Drawing.Point(14, 115)
$stop.Size = New-Object System.Drawing.Size(170, 30)
$controller.Controls.Add($stop)
$stop.Add_Click({ $script:controller.Close() })
$script:controller = $controller

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 400
$timer.Add_Tick({
    try {
        # Do not switch Visio documents or activate a page.
        $win = $visio.ActiveWindow
        if ($null -eq $win -or $null -eq $win.Page) { $script:overlay.Hide(); return }
        $page = $win.Page
        $doc = $page.Document
        if ([string]$doc.Name -cne $DocumentName -or [string]$page.Name -cne $PageName -or
            [IO.Path]::GetFileName([string]$doc.FullName) -cne $DocumentName) {
            $script:overlay.Hide()
            $lbl.Text = 'Жду активную тестовую копию: ' + $DocumentName + ' / ' + $PageName
            return
        }

        $handle = [EnergoLogicP0B.Native]::FromVisioHandle([int]$win.WindowHandle32)
        if (-not [EnergoLogicP0B.Native]::IsWindow($handle)) {
            throw 'Visio window HWND is not valid'
        }

        $pageL = 0.0; $pageT = 0.0; $pageW = 0.0; $pageH = 0.0
        $win.GetViewRect([ref]$pageL, [ref]$pageT, [ref]$pageW, [ref]$pageH)
        $visioL = 0; $visioT = 0; $visioW = 0; $visioH = 0
        $win.GetWindowRect([ref]$visioL, [ref]$visioT, [ref]$visioW, [ref]$visioH)
        $rect = New-Object EnergoLogicP0B.R
        if (-not [EnergoLogicP0B.Native]::GetClientRect($handle, [ref]$rect)) {
            throw 'GetClientRect failed'
        }
        $clientW = $rect.Right - $rect.Left
        $clientH = $rect.Bottom - $rect.Top
        $origin = New-Object EnergoLogicP0B.P
        if (-not [EnergoLogicP0B.Native]::ClientToScreen($handle, [ref]$origin)) {
            throw 'ClientToScreen failed'
        }
        if ($pageW -le 0 -or $pageH -le 0 -or $clientW -le 50 -or $clientH -le 50) {
            throw 'Invalid viewport geometry'
        }
        $all = @($pageL, $pageT, $pageW, $pageH)
        foreach ($v in $all) { if ([double]::IsNaN($v) -or [double]::IsInfinity($v)) { throw 'Non-finite page rectangle' } }

        $fg = [EnergoLogicP0B.Native]::GetForegroundWindow()
        $pidForeground = [uint32]0
        [void][EnergoLogicP0B.Native]::GetWindowThreadProcessId($fg, [ref]$pidForeground)
        $pidVisio = [uint32]0
        [void][EnergoLogicP0B.Native]::GetWindowThreadProcessId($handle, [ref]$pidVisio)
        if ($pidForeground -ne $pidVisio -and $fg -ne $controller.Handle) {
            $script:overlay.Hide()
            return
        }

        $breaker = $page.Shapes.ItemFromID($BreakerId)
        $bus = $page.Shapes.ItemFromID($BusId)
        $bx = [double]$breaker.CellsU('PinX').ResultIU
        $by = [double]$breaker.CellsU('PinY').ResultIU
        $cx = [double]$bus.CellsU('PinX').ResultIU
        $cy = [double]$bus.CellsU('PinY').ResultIU
        $busW = [double]$bus.CellsU('Width').ResultIU
        $busLocX = [double]$bus.CellsU('LocPinX').ResultIU
        $busLocY = [double]$bus.CellsU('LocPinY').ResultIU
        $busAngle = [double]$bus.CellsU('Angle').ResultIU
        if ($busW -le 0 -or [math]::Abs($busAngle) -gt 0.00001) {
            throw 'Test bus shape requires positive width and zero rotation'
        }
        # Visio PinX/PinY point to LocPinX/LocPinY, NOT to the
        # geometric center. Bus 101 has LocPinX=0 (left endpoint).
        $busStartX = $cx - $busLocX
        $busEndX = $busStartX + $busW
        $busCenterY = $cy - $busLocY

        # GetViewRect spans a page-space drawing region, whereas the
        # WindowHandle32 client includes Visio chrome. The user's actual
        # telemetry showed 25.72 px excess client height at both zooms:
        # 1471/20.205 != 903/12.050. Never use unequal X/Y page scales.
        # Prefer a unique large child HWND whose aspect matches GetViewRect.
        $viewAspect = $pageW / $pageH
        $hostAspectError = [math]::Abs(($clientW / $clientH) / $viewAspect - 1.0)
        $childRects = [EnergoLogicP0B.Native]::InspectChildWindows($handle)
        $candidates = New-Object 'System.Collections.Generic.List[object]'
        foreach ($child in $childRects) {
            $ratioError = [math]::Abs(($child.Width / $child.Height) / $viewAspect - 1.0)
            $inside = $child.Left -ge ($origin.X - 2) -and
                $child.Top -ge ($origin.Y - 2) -and
                ($child.Left + $child.Width) -le ($origin.X + $clientW + 2) -and
                ($child.Top + $child.Height) -le ($origin.Y + $clientH + 2)
            if ($inside -and $child.Width -ge ($clientW * 0.70) -and
                $child.Height -ge ($clientH * 0.70) -and
                $ratioError -lt 0.012 -and $ratioError -lt ($hostAspectError * 0.5)) {
                [void]$candidates.Add([pscustomobject]@{
                    left=$child.Left; top=$child.Top; width=$child.Width
                    height=$child.Height; class_name=$child.WindowClass; error=$ratioError
                })
            }
        }
        if ($candidates.Count -eq 1) {
            $candidate = $candidates[0]
            $drawL = [double]$candidate.left
            $drawT = [double]$candidate.top
            $drawW = [double]$candidate.width
            $drawH = [double]$candidate.height
            $viewportSource = 'unique-child-hwnd:' + $candidate.class_name
        } else {
            # Diagnostic fallback only: choose a centered aspect-correct
            # region. Its exact top origin still needs a visual/live check.
            $drawL = [double]$origin.X
            $drawW = [double]$clientW
            $drawH = $drawW / $viewAspect
            if ($drawH -gt ($clientH + 1.0)) {
                throw 'Cannot fit a uniform page scale in the Visio client'
            }
            $drawT = [double]$origin.Y + ($clientH - $drawH) / 2.0
            $viewportSource = 'centered-aspect-estimate'
        }
        # Scale in X is the only source of physical page-to-pixel scale.
        # This avoids the prior 2.932% artificial vertical stretching.
        $screenScale = $drawW / $pageW
        $actualH = $drawW / $viewAspect
        if ([math]::Abs($actualH - $drawH) -gt 0.001) {
            $drawT += ($drawH - $actualH) / 2.0
            $drawH = $actualH
        }
        $toX = { param([double]$x) [single](($x - $pageL) * $screenScale) }
        $toY = { param([double]$y) [single](($pageT - $y) * $screenScale) }
        $br = [System.Drawing.PointF]::new((& $toX $bx), (& $toY $by))
        $bl = [System.Drawing.PointF]::new((& $toX $busStartX), (& $toY $busCenterY))
        $brr = [System.Drawing.PointF]::new((& $toX $busEndX), (& $toY $busCenterY))
        $bounds = [System.Drawing.Rectangle]::new(
            [int][math]::Round($drawL), [int][math]::Round($drawT),
            [int][math]::Round($drawW), [int][math]::Round($drawH)
        )
        $script:overlay.UpdateVisual($bounds, $br, $bl, $brr)
        $script:tickCount++
        $lbl.Text = "ТЕСТОВЫЙ СЛОЙ — только геометрия, не напряжение`r`n" +
                    "В-1-35 (ID=$BreakerId) + шина (ID=$BusId), 400 мс`r`n" +
                    "Прокрути схему и измени масштаб; проверь совпадение меток."

        if (((Get-Date) - $script:lastLog).TotalSeconds -ge 1.0) {
            $dpi = 'unsupported'
            try { $dpi = [string][EnergoLogicP0B.Native]::GetDpiForWindow($handle) } catch {}
            $row = [ordered]@{
                time = (Get-Date).ToString('o')
                doc = [string]$doc.Name; page = [string]$page.Name
                view_page = @($pageL, $pageT, $pageW, $pageH)
                visio_window_rect = @($visioL, $visioT, $visioW, $visioH)
                client_screen = @($origin.X, $origin.Y, $clientW, $clientH)
                dpi = $dpi
                viewport_source = $viewportSource
                drawing_screen = @($bounds.X, $bounds.Y, $bounds.Width, $bounds.Height)
                host_aspect_error = $hostAspectError
                excluded_client_height = [math]::Round($clientH - ($clientW / $viewAspect), 3)
                scale_x_y = @($screenScale, $screenScale)
                candidate_count = $candidates.Count
                child_rects = @($childRects | Select-Object -First 30)
                breaker_pixel = @($br.X, $br.Y)
                bus_pixels = @(@($bl.X,$bl.Y),@($brr.X,$brr.Y))
            }
            Add-Content -LiteralPath $log -Encoding UTF8 -Value (ConvertTo-Json -Compress -Depth 5 -InputObject $row)
            $script:lastLog = Get-Date
        }
        $script:lastError = ''
    } catch {
        $script:overlay.Hide()
        $msg = $_.Exception.Message
        $lbl.Text = 'Ошибка (без изменения документа): ' + $msg
        if ($msg -cne $script:lastError) {
            Add-Content -LiteralPath $log -Encoding UTF8 -Value (ConvertTo-Json -Compress -InputObject @{
                time=(Get-Date).ToString('o'); error=$msg
            })
            $script:lastError = $msg
        }
    }
})
$controller.Add_FormClosed({ $script:timer.Stop(); $script:overlay.Close(); $script:done=$true })
try {
    Write-Host 'EnergoLogic P0-B read-only transient viewport overlay'
    Write-Host ('Log: ' + $log)
    Write-Host 'No drawing modifications; close via the controller button.'
    $timer.Start()
    [System.Windows.Forms.Application]::Run($controller)
}
finally {
    $timer.Stop()
    $timer.Dispose()
    if (-not $script:overlay.IsDisposed) { $script:overlay.Close() }
    $script:overlay.Dispose()
    $controller.Dispose()
    Write-Host ('Geometry sample log: ' + $log)
    Write-Host ('Ticks (only active document): ' + $script:tickCount)
}
