# Patakbuhin ang iRequest kahit nakasara ang terminal (44.223.68.230)

Para tumakbo ang site **palagi** at hindi mamatay kapag isinara ang PowerShell/terminal, kailangan i-run ang app bilang **systemd service** sa server.

---

## Unang beses na setup (sa server 44.223.68.230)

### 1. SSH sa server

```bash
ssh ubuntu@44.223.68.230
```

(Palitan ang `ubuntu` kung iba ang username.)

### 2. Pumunta sa folder ng app at i-activate ang venv

```bash
cd /home/ubuntu/iRequest
source venv/bin/activate
```

(Kung wala pa ang venv: `python3 -m venv venv` then `source venv/bin/activate`.)

### 3. I-install ang gunicorn (kung wala pa)

```bash
pip install gunicorn==21.2.0
```

### 4. I-copy ang service file at i-enable

**Kung naka-git pull na ang latest code** (may folder na `deploy/`):

```bash
sudo cp /home/ubuntu/iRequest/deploy/irequest.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable irequest
sudo systemctl start irequest
```

**Kung iba ang path o username**, i-edit muna ang service file:

```bash
sudo nano /etc/systemd/system/irequest.service
```

- Palitan ang `User=ubuntu` at `Group=ubuntu` kung iba ang user.
- Palitan ang lahat ng `/home/ubuntu/iRequest` kung iba ang folder ng app.
- Palitan ang `venv` path kung iba ang virtualenv path.

Save (Ctrl+O, Enter, Ctrl+X), tapos:

```bash
sudo systemctl daemon-reload
sudo systemctl enable irequest
sudo systemctl start irequest
```

### 5. I-check kung tumatakbo

```bash
sudo systemctl status irequest
```

Dapat may "active (running)". Buksan sa browser: `http://44.223.68.230:5000`

---

## Mga useful na command

| Gawain              | Command                    |
|---------------------|----------------------------|
| Tingnan status      | `sudo systemctl status irequest` |
| I-stop              | `sudo systemctl stop irequest`   |
| I-start             | `sudo systemctl start irequest`  |
| I-restart (after deploy) | `sudo systemctl restart irequest` |
| View logs           | `sudo journalctl -u irequest -f`  |

---

## Pagkatapos mag-deploy ng bagong code

```bash
cd /home/ubuntu/iRequest
git pull origin main
sudo systemctl restart irequest
```

Pagkatapos nito, kahit isara mo ang PowerShell/terminal, ang app ay tumatakbo pa rin sa server dahil naka-systemd service na siya.
