# Silent kitchen printing (no Print button click)

Web browsers **do not allow** JavaScript to print without permission unless the browser is started in **kiosk printing** mode. This is normal browser security.

Your POS already calls `window.print()` automatically after each order. To skip the print dialog on every kitchen slip:

## 1. Set default printer

In Windows (or Linux):

1. Open **Settings → Bluetooth & devices → Printers & scanners**
2. Select your **kitchen thermal printer**
3. Click **Set as default**

All auto kitchen prints will go to that printer.

## 2. Close ALL Chrome/Edge windows first

Kiosk flags only work in a **new dedicated browser profile**. Close every Chrome/Edge window before launching.

## 3. Open POS using kiosk printing (required)

**Do not** use a normal Chrome tab, Cursor browser, or regular shortcut.

### Windows — local test

```bat
scripts\start-pos-kiosk-print-local.bat
```

This opens **full-screen kiosk Chrome** with:

- `--kiosk` (required for silent print)
- `--kiosk-printing` (no Print dialog)
- `--disable-print-preview`
- Separate profile (`%LOCALAPPDATA%\PB-POS-Kiosk`)

### Windows — production

```bat
scripts\start-pos-kiosk-print.bat
```

### Linux (counter PC with display)

```bash
chmod +x scripts/start-pos-kiosk-print.sh
./scripts/start-pos-kiosk-print.sh https://rev1.pbpos.online/pos/
```

### Manual Chrome command

```bat
"C:\Program Files\Google\Chrome\Application\chrome.exe" --kiosk-printing --app=https://rev1.pbpos.online/pos/
```

## 3. Pin shortcut on cashier desktop

1. Right-click `scripts\start-pos-kiosk-print.bat` → **Send to → Desktop (create shortcut)**
2. Rename to **PB POS**
3. Cashiers always open POS from this shortcut

## Result

- Order placed → kitchen slips print **automatically**
- One **separate small slip per category** (BBQ, Naan, etc.)
- **No print dialog** on each slip (when `--kiosk-printing` is used)

## Exit kiosk mode

Press **Alt+F4** to close the full-screen browser.

## Troubleshooting

| Problem | Fix |
|--------|-----|
| Print dialog still appears | Close **all** Chrome windows → run `start-pos-kiosk-print-local.bat` again |
| Yellow banner on POS | You opened POS in normal browser — use the `.bat` file |
| Wrong printer | Set kitchen printer as **default** in Windows |
| Nothing prints | Check printer USB/network, paper, and driver |
| Only first slip prints | Hard refresh (`Ctrl+F5`) after updating the app |

## Note

This is a **browser/PC setup**, not a server change. Each cashier PC that prints kitchen tickets needs the kiosk shortcut and default printer configured once.
