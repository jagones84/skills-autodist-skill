---
name: "prime-video"
description: "Opens Prime Video in the user's real Chrome profile, fullscreen on the secondary monitor (DISPLAY2, 3440x1440 at X=-3440), and resumes playback from the 'Continue watching' row. Invoke when the user asks to open Prime Video, resume a series, 'metti la serie', or 'continua a guardare'."
---

# Prime Video — resume su monitor secondario

Procedura VALIDATA (2026-09-01): apertura → fullscreen monitor 2 → resume "Lucky S1 E5" in ~20 comandi. La prima esecuzione senza skill ha perso tempo su 3 trappole (documentate qui sotto): questa skill le evita.

## Ambiente fisso (rilevato)

| Fatto | Valore |
|---|---|
| Monitor secondario | DISPLAY2, **3440x1440, X NEGATIVA** (a sinistra del primario 5120x1440) |
| Browser | Chrome, profilo default **già loggato ad Amazon** |
| CDP/DOM automation | **IMPOSSIBILE**: Chrome ≥136 blocca `--remote-debugging-port` sul profilo default → automazione SOLO sintetica (mouse/tastiera) |
| MCP omniparser | `screenshot_raw`/`screenshot_parse` monitor `"2"` = OK; **`click_by_caption` = BUGGATO su monitor a X negativa** (clicca sul primario: le coordinate sono nello spazio immagine, non schermo) |
| OCR | spesso sbaglia caption delle copertine: "LUGKY"=LUCKY, "Continur"=Continue, "Uuqan"=Sugar |

## Coordinate: conversione obbligatoria

1. `screenshot_raw` monitor `"2"` (max_width 2560) → leggi il PNG → individua l'elemento e le sue coordinate **nell'immagine di preview** (es. 1024 px di larghezza).
2. Normalizza: `nx = x_preview / larghezza_preview`, `ny = y_preview / altezza_preview`.
3. Converti a coordinate **schermo**: `X = -3440 + nx*3440`, `Y = ny*1440`.

## Procedura

### 1) Apri Prime Video in una nuova finestra del Chrome reale
```powershell
Start-Process "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" -ArgumentList '--new-window','https://www.primevideo.com/'
```

### 2) Sposta sul monitor 2 + fullscreen (F11) — script completo
```powershell
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
  public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder t, int n);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder t, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
}
"@
$target = [IntPtr]::Zero
$deadline = (Get-Date).AddSeconds(15)
while ($target -eq [IntPtr]::Zero -and (Get-Date) -lt $deadline) {
  $cb = [W+EnumWindowsProc]{ param($h, $l)
    if ([W]::IsWindowVisible($h)) {
      $t = New-Object System.Text.StringBuilder 512; [void][W]::GetWindowText($h, $t, 512)
      $c = New-Object System.Text.StringBuilder 256; [void][W]::GetClassName($h, $c, 256)
      if ($c.ToString() -eq 'Chrome_WidgetWin_1' -and $t.ToString() -match 'Prime Video') { $script:target = $h; return $false }
    }
    return $true
  }
  [void][W]::EnumWindows($cb, [IntPtr]::Zero)
  if ($target -eq [IntPtr]::Zero) { Start-Sleep -Milliseconds 500 }
}
if ($target -eq [IntPtr]::Zero) { exit 1 }
[void][W]::SetWindowPos($target, [IntPtr]::Zero, -3440, 0, 3440, 1440, 0x0040)
[void][W]::ShowWindow($target, 3)          # SW_MAXIMIZE sul monitor dove si trova
[void][W]::SetForegroundWindow($target)
Start-Sleep -Milliseconds 800
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait('{F11}')
```
F11 (fullscreen browser) **persiste tra le navigazioni**: non ripeterlo nel player.

### 3) Scroll con wheel virtuale (funziona SENZA focus tastiera)
La riga "Continue watching" sta sotto la piega; PageDown NON scrolla (focus nel carosello hero). Usare la rotellina:
```powershell
# SetCursorPos + mouse_event (0x0800 = MOUSEEVENTF_WHEEL, negativo = giù)
SetCursorPos(-1700, 700)   # punto neutro del monitor 2
for ($i=0; $i -lt 10; $i++) { mouse_event(0x0800, 0, 0, -120, [UIntPtr]::Zero); Start-Sleep -Milliseconds 60 }
```

### 4) Click nativo (MAI click_by_caption)
```powershell
SetCursorPos($x, $y)               # coordinate reali schermo (X negativa!)
Start-Sleep -Milliseconds 400      # attesa hover/overlay
mouse_event(0x0002, 0, 0, 0, 0)    # LEFTDOWN
Start-Sleep -Milliseconds 80
mouse_event(0x0004, 0, 0, 0, 0)    # LEFTUP
```

### 5) Scegli la serie e avvia
- **La PRIMA card della riga "Continue watching" = contenuto più recente** (quello che l'utente stava vedendo).
- Click sulla card → pagina dettaglio → click sul bottone **"Resume S1 EN"** (o "Watch now"): stesso metodo al punto 4.
- Nel dettaglio Apple TV+/Channels il bottone è in basso a sinistra (y ≈ 0.88 normalizzato).

### 6) Verifica finale
`screenshot_raw` dopo 3-4 s: frame pieno senza overlay play e senza controlli (auto-nascosti) = **riproduzione attiva**. Con controlli visibili, controllare che la timeline avanzi con un secondo screenshot.

## Regole d'oro

1. **MAI** usare `click_by_caption` per cliccare: su DISPLAY2 (X negativa) clicca nel posto sbagliato e riporta `success: true` — silenziosamente inutile. Solo screenshot MCP; click SOLO PowerShell nativo.
2. **MAI** tentare CDP/agent-browser su Chrome profilo default (bloccato ≥136, e Chrome già in esecuzione senza porta debug).
3. Titoli di riga dello storefront ("Continue watching") NON sono link: non cliccarli, cliccare le CARD.
4. OCR della copertina può essere sbagliato: leggere il titolo DALL'IMMAGINE letta con i propri occhi, non fidarsi della caption del parse.
5. Se non risulta loggato (presenza di "Sign in"): FERMARSI e chiedere all'utente — mai cercare credenziali per conto proprio.
6. Non toccare le finestre Chrome esistenti dell'utente: si apre solo una nuova finestra e la si muove; `--new-window` non disturba l'istanza in corso.
