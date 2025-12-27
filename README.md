

````markdown
# GhostIG — Silent Instagram OSINT (Developer h4cker_fawad)

> A lightweight and efficient command-line tool for gathering publicly available Instagram profile intelligence.

---

## Overview

GhostIG is designed for security researchers, OSINT analysts, and developers who need to collect Instagram profile data using official mobile API endpoints. It requires a **valid Instagram session ID** and provides structured output in both human-readable and JSON formats.

---

## Features

| Feature | Description |
|---------|-------------|
| Profile Extraction | Username, user ID, full name, biography, external URL |
| Account Stats | Followers, following, posts, IGTV videos |
| Account Type | Verified, private, business |
| Contact Info | Public email & phone (if available) |
| Advanced Lookup | Obfuscated email/phone (optional) |
| Output | Human-readable table or JSON |
| Reliability | Error handling and rate-limit awareness |
| Optional Enrichment | Phone country formatting using `phonenumbers` & `pycountry` |

---

## Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.7+ |
| requests | Any |
| phonenumbers (optional) | Any |
| pycountry (optional) | Any |

*Optional libraries enhance phone formatting but are not required.*

---


````

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/fawadqureshi007/ghostig.git
cd ghostig
pip install -r requirements.txt
```
---

## Usage

GhostIG requires a valid Instagram session ID cookie. You can provide either a username or numeric ID.

### Lookup by Username

```bash
python ghostig.py -s SESSION_ID -u exampleuser
```

### Lookup by Numeric ID

```bash
python ghostig.py -s SESSION_ID -i 1234567890
```

### Skip Advanced Lookup (Optional)

```bash
python ghostig.py -s SESSION_ID -u exampleuser --skip-lookup
```

### JSON Output

```bash
python ghostig.py -s SESSION_ID -u exampleuser --json
```

---

## Example Output

```
INSTAGRAM PROFILE INSIGHTS
============================================================
Username           : exampleuser
User ID            : 123456789
Verified           : No
Business Account   : Yes
Private Account    : No
Followers          : 12,340
Following          : 321
Posts              : 87
IGTV Videos        : 2
External URL       : https://example.com
Public Email       : contact@example.com
Public Phone       : +1 555-1234 (USA)
Profile Picture    : https://...
Biography:
    Enthusiast | Developer | Contributor
============================================================
```

---

## Configuration

GhostIG relies on headers to access Instagram’s private mobile API. If requests fail:

1. Update `User-Agent` strings
2. Update Instagram app IDs
3. Check for rate limits

---

## Limitations

* Instagram API changes may break functionality
* Session ID may expire or be restricted
* Advanced lookup may trigger rate limits

---

## Contributing

* Follow the existing code style
* Open an issue before submitting pull requests
* Submit clear and documented PRs

---

## License

MIT License

---

## Disclaimer

GhostIG is intended **solely for lawful OSINT research and ethical purposes**.

* Use a **valid Instagram session ID** you control
* Tool does **not bypass authentication**
* The author is **not responsible for misuse**

Use responsibly and comply with applicable laws and Instagram’s Terms of Service.
