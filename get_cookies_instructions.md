# How to get LinkedIn Cookies

To avoid login issues and 2FA, we will use your existing browser session.

1.  **Open LinkedIn** in your desktop browser (Chrome/Edge/Firefox) and make sure you are logged in.
2.  **Open Developer Tools** (F12 or Right Click -> Inspect).
3.  Go to the **Application** tab (Chrome/Edge) or **Storage** tab (Firefox).
4.  On the left, look for **Cookies** and select `https://www.linkedin.com`.
5.  Find the cookie named `li_at`.
6.  Copy its **Value**.
7.  Create a file named `cookies.json` in the `jobs/` folder with this format:

```json
[
  {
    "name": "li_at",
    "value": "YOUR_COPIED_VALUE_HERE",
    "domain": ".linkedin.com",
    "path": "/",
    "httpOnly": true,
    "secure": true,
    "sameSite": "None"
  }
]
```

**Paste the value here in the chat**, and I can create the file for you.
