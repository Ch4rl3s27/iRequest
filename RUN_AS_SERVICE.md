# Run iRequest even when the terminal is closed (44.223.68.230)

To keep the site running **all the time** and not stop when you close PowerShell/terminal, run the app as a **systemd service** on the server.

---

## First-time setup (on server 44.223.68.230)

### 1. SSH into the server

```bash
ssh ubuntu@44.223.68.230
```

(Replace `ubuntu` if your username is different.)

### 2. Go to the app folder and activate the venv

```bash
cd /home/ubuntu/iRequest
source venv/bin/activate
```

(If you don't have venv yet: `python3 -m venv venv` then `source venv/bin/activate`.)

### 3. Install gunicorn (if not already installed)

```bash
pip install gunicorn==21.2.0
```

### 4. Copy the service file and enable it

**If you have already pulled the latest code** (and have the `deploy/` folder):

```bash
sudo cp /home/ubuntu/iRequest/deploy/irequest.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable irequest
sudo systemctl start irequest
```

**If the path or username is different**, edit the service file first:

```bash
sudo nano /etc/systemd/system/irequest.service
```

- Replace `User=ubuntu` and `Group=ubuntu` if your user is different.
- Replace all `/home/ubuntu/iRequest` if the app folder is different.
- Replace the `venv` path if your virtualenv path is different.

Save (Ctrl+O, Enter, Ctrl+X), then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable irequest
sudo systemctl start irequest
```

### 5. Check that it is running

```bash
sudo systemctl status irequest
```

You should see "active (running)". Open in your browser: `http://44.223.68.230:5000`

---

## Useful commands

| Action              | Command                          |
|---------------------|-----------------------------------|
| Check status        | `sudo systemctl status irequest`  |
| Stop                | `sudo systemctl stop irequest`   |
| Start               | `sudo systemctl start irequest`  |
| Restart (after deploy) | `sudo systemctl restart irequest` |
| View logs           | `sudo journalctl -u irequest -f`  |

---

## After deploying new code

```bash
cd /home/ubuntu/iRequest
git pull origin main
sudo systemctl restart irequest
```

After this, even if you close PowerShell/terminal, the app keeps running on the server because it is running as a systemd service.
