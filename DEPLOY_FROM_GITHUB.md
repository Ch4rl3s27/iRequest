# Ilagay sa instance ang mga na-push sa GitHub

Para lumabas sa live site (hal. **http://18.212.214.225:5000**) ang mga bagong changes, gawin: (1) push sa GitHub mula sa PC, (2) sa server/instance, pull mula sa GitHub at i-restart ang app.

---

## Step 1 – Sa PC mo (Windows)

1. Buksan PowerShell at pumunta sa project folder:
   ```powershell
   cd c:\Users\Abel\Desktop\iRequest
   ```

2. I-commit at i-push ang lahat ng gusto mong ma-deploy:
   ```powershell
   git add .
   git status
   git commit -m "Update Student Signup (login link, Data Privacy date)"
   git push origin main
   ```
   (Palitan ang `main` kung iba ang branch mo, hal. `master`.)

---

## Step 2 – Sa instance (server)

Gamit ang IP ng instance mo (hal. **18.212.214.225**):

1. **SSH sa server**
   ```bash
   ssh ubuntu@18.212.214.225
   ```
   (Palitan ang `ubuntu` kung iba ang username; kung may `.pem` key: `ssh -i "path\to\key.pem" ubuntu@18.212.214.225`.)

2. **Pumunta sa folder ng app**
   ```bash
   cd /home/ubuntu/iRequest
   ```
   (Palitan ang path kung iba ang location ng iRequest sa server.)

3. **Kunin ang latest mula sa GitHub**
   ```bash
   git pull origin main
   ```
   (Palitan ang `main` kung iba ang branch.)

4. **I-restart ang app** (piliin kung paano naka-run):
   - **Kung naka-systemd service (irequest):**
     ```bash
     sudo systemctl restart irequest
     ```
   - **Kung naka-gunicorn:**
     ```bash
     sudo systemctl restart gunicorn
     ```
   - **Kung manual (python):** Patayin ang process (Ctrl+C) sa terminal kung saan tumatakbo, tapos start ulit, hal. `python app.py` o `gunicorn ...`.

---

## Pagkatapos

Buksan sa browser ang live site, hal. **http://18.212.214.225:5000/Student_Signup.html**, at gawin **hard refresh** (Ctrl + Shift + R). Dapat makita na ang mga bagong updates (hal. bagong login link at Data Privacy date).

---

## Kung iba ang IP o path sa server

- **IP:** Palitan ang `18.212.214.225` sa SSH command at sa URL.
- **App path:** Kung naka-clone ang repo sa ibang folder (hal. `/var/www/iRequest`), gamitin iyon sa `cd` at sa service file kung naka-systemd ka.
