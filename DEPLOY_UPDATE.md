# How to update the instance (44.223.68.230)

To deploy changes (e.g. remove the Dark Mode button from the student dashboard on the server), you need to deploy the updated `student_dashboard.html`.

---

## Method 1: Git (if the project on the server uses git)

### Step 1 – On your PC (local)

1. Commit and push your changes:
   ```powershell
   cd c:\Users\Abel\Desktop\iRequest
   git add app/templates/student_dashboard.html
   git commit -m "Remove dark mode from student dashboard"
   git push origin main
   ```

### Step 2 – On the server (44.223.68.230)

1. SSH into the server:
   ```bash
   ssh ubuntu@44.223.68.230
   ```
   (Replace `ubuntu` if your username is different.)

2. Go to the app folder and pull:
   ```bash
   cd /home/ubuntu/iRequest
   git pull origin main
   ```
   (Replace the path if the project is in a different location.)

3. Restart the app. Depends on how it is run:
   - **Systemd:**
     ```bash
     sudo systemctl restart irequest
     ```
   - **Manual (gunicorn):**
     ```bash
     sudo systemctl restart gunicorn
     ```
   - **Manual (python):** Stop the process (Ctrl+C) then start again, e.g. `python app.py` or `gunicorn ...`.

---

## Method 2: Copy file (if there is no git on the server)

### On your PC

1. Copy the file to the server using SCP (replace `ubuntu` and path if different):
   ```powershell
   scp "c:\Users\Abel\Desktop\iRequest\app\templates\student_dashboard.html" ubuntu@44.223.68.230:/home/ubuntu/iRequest/app/templates/
   ```

### On the server

1. Restart the app (same options as Step 2 in Method 1).

---

## After updating

Open in your browser: `http://44.223.68.230:5000/student_dashboard.html`  
Do a hard refresh: **Ctrl + Shift + R**. The Dark Mode button should no longer appear in the sidebar.
