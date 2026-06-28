# Silent kitchen printing with QZ Tray

Chrome **always** shows a Print dialog. QZ Tray prints directly to your thermal printer with **no dialog**.

## Quick setup

1. **Install QZ Tray** — https://qz.io/download/ (keep it running in system tray)
2. **Open POS** in normal Chrome: `http://127.0.0.1:8000/pos/`
3. **Hard refresh** — `Ctrl+F5`
4. Wait for green bar: **Silent kitchen print ready (QZ Tray)**
5. Place a test order

## Printer name (optional)

Settings → Receipt Settings → **Kitchen printer name**:
```text
BlackCopper 80mm Series
```
Leave blank to use Windows default printer.

## First connection

QZ may show **Allow** once for localhost — click **Allow** and **Remember**.

## If you still see Chrome Print dialog

That means QZ is **not connected**. Check:

1. QZ Tray icon is in system tray (bottom-right)
2. Green bar shows on POS (not yellow warning)
3. Hard refresh POS (`Ctrl+F5`)
4. Open browser console (F12) — look for QZ errors

## Do NOT use

- Chrome kiosk `.bat` file (not needed with QZ)
- Regular print from browser when QZ is disconnected

## Production

Same steps on `https://rev1.pbpos.online/pos/` — allow the site once in QZ Tray.
