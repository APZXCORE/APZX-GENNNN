# APZX G3NNNN v1.0

**Discord token & email-verified account generator**

![APZX G3NNNN](assets/legionproxy-logo.png)

*Made by 4iuc | APZXCORE*

---

## ⚡ Features

- **Token Generation** — Request-based Discord account creation with full fingerprint spoofing
- **Email Verification** — 7 mail providers: DuckMail, CyberTemp, TempMail.lol, Hotmail007, Zeus, Draxono, Mailcow
- **Humanizer Engine** — Auto-sets display name, bio, pronouns, avatar, and HypeSquad
- **Utility Tools** — Server Joiner, Auth Joiner, Token Checker, Token Onliner, and Proxy Checker
- **Proxy Rotation** — Auto-cycles proxies with IP burn detection
- **9Captcha Solver** — Extension or Request mode support
- **WebSocket Keepalive** — Maintains gateway presence to prevent instant disable
- **Local IP Mode** — Use your own IP with 90s cooldown between accounts

---

## 🚀 Quick Start

```
Start-GUI.bat   # Opens the dark cyberpunk GUI (recommended)
Start-CLI.bat   # Terminal version
```

Or manually:

```bash
pip install -r requirements.txt
python start.py
```

---

## ⚙️ Config

Edit `config.json` or use the Settings menu:

| Setting | Description |
|---------|-------------|
| **9Captcha API Key** | Get yours at [9captcha.pridesmp.fun](https://9captcha.pridesmp.fun) |
| **Mail Services** | Toggle providers on/off, set API keys/passwords |
| **Solver Mode** | Extension (proxyless OK) or Request (requires residential proxies) |
| **Threads** | Concurrent generation count |
| **Humanizer** | Enable/disable profile customization |
| **Local IP Mode** | Use your own IP instead of proxies (90s cooldown between accounts) |
| **Cloudflare WARP** | Rotate IP via WARP (Windows only) |

---

## 🌐 Proxies

Add proxies to `input/proxies.txt` in any of these formats (auto-detected):

| Format | Example |
|--------|---------|
| `ip:port:user:pass` | `123.45.67.89:8080:uorder123:pass123` |
| `user:pass@ip:port` | `uorder123:pass123@123.45.67.89:8080` |
| `ip:port` (no auth) | `123.45.67.89:8080` |

> **Note:** Request solver requires quality **residential** proxies. Datacenter IPs are blocked by Discord. Extension solver works proxyless. Local IP mode auto-enables when no proxies are found.

---

## 🛡️ Proxies Powered & Sponsored By LegionProxy

![LegionProxy](assets/legionproxy-logo.png)

This project is proudly sponsored by **[LegionProxy](https://legionproxy.io)** — high-quality residential proxies optimized for Discord automation.

### Why LegionProxy?

- ✅ **Rotating Residential IPs** — Fresh IP per request, perfect for Discord
- ✅ **`uorder` format** — Use your LegionProxy dashboard username as the `uorder` user
- ✅ **Auto-compatible** — Works with the `ip:port:user:pass` format out of the box
- ✅ **Fast & Reliable** — Low latency, high uptime
- ✅ **Discord-Optimized** — Specifically configured to bypass Discord's proxy detection

### How to Get Started

1. Sign up at [legionproxy.io](https://legionproxy.io)
2. Create a **Rotating / HTTP / Fast** proxy plan
3. Copy your credentials from the dashboard
4. Add to `input/proxies.txt` in this format:
   ```
   your-ip:port:uorder:your-password
   ```
   (Where `uorder` is literally the username from your LegionProxy dashboard)

### Other Supported Providers

| Provider | Format |
|----------|--------|
| **Smartproxy** | `ip:port:user:pass` or `user:pass@ip:port` |
| **Bright Data** | `ip:port:user:pass` |
| **Soax** | `ip:port:user:pass` |

---

## 🐛 Troubleshooting

### "Invalid Form Body" / "EMAIL_INVALID"
Your temp mail domains are flagged by Discord. Switch to a different provider:
- Try **Zeus** or **Lution** — Microsoft Outlook domains are most trusted
- Or enable **DuckMail** — it uses `duckmail.sbs` which works well

### "Rate Limited" / 429
Your proxies are banned. Use residential proxies, not datacenter. LegionProxy rotating proxies work best for this.

### Proxy Connection Errors
If you see "Unsupported proxy syntax" or curl errors:
1. Make sure your proxy format is one of the three listed above
2. The app auto-converts `ip:port:user:pass` → `http://user:pass@ip:port`
3. If still failing, try the `user:pass@ip:port` format in your proxy file

### Debug Logs
Check `debug_register.txt` for full request/response details.

---

## 🔑 9Captcha API

Get your API key at [9captcha.pridesmp.fun](https://9captcha.pridesmp.fun)

Two modes available:
- **Extension Mode** — Works without proxies
- **Request Mode** — Requires residential proxies

---

## 📂 Project Structure

```
gen/
├── main.py              # Core generator engine
├── start.py             # CLI menu & settings
├── gui_start.py         # Flask + pywebview GUI server
├── config.json          # All settings (edit directly or via GUI)
├── requirements.txt     # Python dependencies
├── Start-CLI.bat        # Run CLI version
├── Start-GUI.bat        # Run GUI version
├── README.md            # This file
├── .gitignore           # Git ignore rules
├── assets/              # Logos & images
│   └── legionproxy-logo.png
├── engine/              # Bypasses, joiner, proxy checker, extensions
├── gui_templates/       # Web UI templates
├── gui_static/          # CSS & static assets
├── input/               # Proxies go here (proxies.txt)
├── output/              # Generated tokens & emails
└── extension/           # 9Captcha browser extension
```

---

## ⚖️ Disclaimer

This tool is created for **educational, development, and security testing** purposes only. The developer (**APZX** / **4iuc | APZXCORE**) and any associated organizations or contributors are **not responsible** for any misuse, damage, bans, or unlawful actions conducted with this software. The end user accepts full and sole responsibility for all actions taken.

By downloading, accessing, or running this repository, you explicitly accept and agree to these terms and rules.

---

**v1.0 — Made by 4iuc | APZXCORE** · Proxies powered by [LegionProxy](https://legionproxy.io) · Join their [Discord](https://discord.gg/wQbqecjc8b)
