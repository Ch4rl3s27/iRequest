# SSH access sa 44.223.68.230 (Permission denied fix)

Ang server ay naka-configure para sa **key-based login** lang. Gamitin ang **.pem key** na nasa project folder.

---

## 1. Key file sa project

Ang SSH key ay naka-save na sa project:

- **`C:\Users\Abel\Desktop\iRequest\irequest.pem`**

(Huwag i-commit ang .pem — naka-ignore na sa `.gitignore`.)

---

## 2. Gamitin ang key sa SSH

Sa PowerShell:

```powershell
ssh -i "C:\Users\Abel\Desktop\iRequest\irequest.pem" ubuntu@44.223.68.230
```

**Kung "key too open" / "bad permissions" ang error**, ayusin muna ang permissions:

```powershell
icacls "C:\Users\Abel\Desktop\iRequest\irequest.pem" /inheritance:r /grant:r "Abel:(R)"
```

(Palitan ang `Abel` kung iba ang username mo sa Windows. Para malaman: `whoami`)

O patakbuhin ang script:

```powershell
cd C:\Users\Abel\Desktop\iRequest
.\fix-pem-permissions.ps1
```

---

## 3. (Optional) SSH config para hindi na type lagi

Buksan o gawa: `C:\Users\Abel\.ssh\config` (walang extension).

Idagdag:

```
Host irequest
    HostName 44.223.68.230
    User ubuntu
    IdentityFile C:\Users\Abel\Desktop\iRequest\irequest.pem
```

Pagkatapos, pwede na lang:

```powershell
ssh irequest
```

---

## Kung wala ka na talagang .pem key

1. **AWS Console** → EC2 → Instances → piliin ang instance → **Connect**.
2. Gamitin **EC2 Instance Connect** (browser) para makapasok nang walang .pem sa PC.
3. Sa loob ng server, idagdag ang bagong public key mo sa `~/.ssh/authorized_keys` (kung may bagong key ka na), o gumawa ng bagong key pair sa AWS at i-associate sa instance (mas masinsinan ang steps).

---

## Access key (iba sa .pem)

Ang **`irequest_accessKeys.csv`** ay para sa **AWS API** (S3, etc.), hindi sa SSH. Ilagay ang laman nito sa **`.env`** bilang `AWS_ACCESS_KEY_ID` at `AWS_SECRET_ACCESS_KEY`. Huwag i-commit ang CSV.
