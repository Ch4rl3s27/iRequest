# SSH access to 44.223.68.230 (Permission denied fix)

The server is configured for **key-based login** only. Use the **.pem key** in the project folder.

---

## 1. Key file in the project

The SSH key is already saved in the project:

- **`C:\Users\Abel\Desktop\iRequest\irequest.pem`**

(Do not commit the .pem file — it is already in `.gitignore`.)

---

## 2. Using the key for SSH

In PowerShell:

```powershell
ssh -i "C:\Users\Abel\Desktop\iRequest\irequest.pem" ubuntu@44.223.68.230
```

**If you get "key too open" / "bad permissions"**, fix the permissions first:

```powershell
icacls "C:\Users\Abel\Desktop\iRequest\irequest.pem" /inheritance:r /grant:r "Abel:(R)"
```

(Replace `Abel` with your Windows username if different. To check: `whoami`)

Or run the script:

```powershell
cd C:\Users\Abel\Desktop\iRequest
.\fix-pem-permissions.ps1
```

---

## 3. (Optional) SSH config so you don't have to type the key path every time

Open or create: `C:\Users\Abel\.ssh\config` (no file extension).

Add:

```
Host irequest
    HostName 44.223.68.230
    User ubuntu
    IdentityFile C:\Users\Abel\Desktop\iRequest\irequest.pem
```

Then you can simply run:

```powershell
ssh irequest
```

---

## If you no longer have the .pem key

1. **AWS Console** → EC2 → Instances → select the instance → **Connect**.
2. Use **EC2 Instance Connect** (browser) to connect without the .pem on your PC.
3. On the server, add your new public key to `~/.ssh/authorized_keys` (if you have a new key), or create a new key pair in AWS and associate it with the instance (see AWS docs for steps).

---

## Access key (different from .pem)

The **`irequest_accessKeys.csv`** file is for **AWS API** (S3, etc.), not for SSH. Put its contents in **`.env`** as `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. Do not commit the CSV.
