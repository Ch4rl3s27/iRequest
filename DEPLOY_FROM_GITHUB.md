# Deploy to the instance from GitHub

To have your new changes appear on the live site (e.g. **http://18.212.214.225:5000**): (1) push to GitHub from your PC, (2) on the server/instance, pull from GitHub and restart the app.

---

## Step 1 – On your PC (Windows)

1. Open PowerShell and go to the project folder:
   ```powershell
   cd c:\Users\Abel\Desktop\iRequest
   ```

2. Commit and push everything you want to deploy:
   ```powershell
   git add .
   git status
   git commit -m "Update Student Signup (login link, Data Privacy date)"
   git push origin main
   ```
   (Replace `main` with your branch name if different, e.g. `master`.)

---

## Step 2 – On the instance (server)

Using your instance IP (e.g. **18.212.214.225**):

1. **SSH into the server**
   ```bash
   ssh ubuntu@18.212.214.225
   ```
   (Replace `ubuntu` if your username is different; if you use a `.pem` key: `ssh -i "path\to\key.pem" ubuntu@18.212.214.225`.)

2. **Go to the app folder**
   ```bash
   cd /home/ubuntu/iRequest
   ```
   (Replace the path if iRequest is in a different location on the server.)

3. **Pull the latest from GitHub**
   ```bash
   git pull origin main
   ```
   (Replace `main` if your branch is different.)

4. **Restart the app** (choose according to how it is run):
   - **If using systemd service (irequest):**
     ```bash
     sudo systemctl restart irequest
     ```
   - **If using gunicorn:**
     ```bash
     sudo systemctl restart gunicorn
     ```
   - **If running manually (python):** Stop the process (Ctrl+C) in the terminal where it is running, then start again, e.g. `python app.py` or `gunicorn ...`.

---

## After deploying

Open the live site in your browser, e.g. **http://18.212.214.225:5000/Student_Signup.html**, and do a **hard refresh** (Ctrl + Shift + R). You should see the new updates (e.g. new login link and Data Privacy date).

---

## If the IP or path on the server is different

- **IP:** Replace `18.212.214.225` in the SSH command and in the URL.
- **App path:** If the repo is cloned to a different folder (e.g. `/var/www/iRequest`), use that path in the `cd` command and in the service file if you use systemd.
