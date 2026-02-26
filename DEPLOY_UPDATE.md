# Paano i-Update ang Instance (44.223.68.230)

Para mawala ang Dark Mode button sa student dashboard sa server, kailangan ma-deploy ang updated na `student_dashboard.html`.

---

## Paraan 1: Git (kung naka-git ang project sa server)

### Step 1 – Sa PC mo (local)

1. I-commit at i-push ang changes:
   ```powershell
   cd c:\Users\Abel\Desktop\iRequest
   git add app/templates/student_dashboard.html
   git commit -m "Remove dark mode from student dashboard"
   git push origin main
   ```

### Step 2 – Sa server (44.223.68.230)

1. SSH sa server:
   ```bash
   ssh ubuntu@44.223.68.230
   ```
   (Palitan ang `ubuntu` kung iba ang username.)

2. Pumunta sa folder ng app at mag-pull:
   ```bash
   cd /home/ubuntu/iRequest
   git pull origin main
   ```
   (Palitan ang path kung iba ang location ng project.)

3. I-restart ang app. Depende kung paano naka-run:
   - **Systemd:**
     ```bash
     sudo systemctl restart irequest
     ```
   - **Manual (gunicorn):**
     ```bash
     sudo systemctl restart gunicorn
     ```
   - **Manual (python):** Patayin ang process (Ctrl+C) tapos start ulit, hal. `python app.py` o `gunicorn ...`.

---

## Paraan 2: Copy file (kung walang git sa server)

### Sa PC mo

1. I-copy ang file papunta sa server gamit SCP (palitan ang `ubuntu` at path kung iba):
   ```powershell
   scp "c:\Users\Abel\Desktop\iRequest\app\templates\student_dashboard.html" ubuntu@44.223.68.230:/home/ubuntu/iRequest/app/templates/
   ```

### Sa server

1. I-restart ang app (same options sa Step 2 sa Paraan 1).

---

## Pagkatapos

Buksan sa browser: `http://44.223.68.230:5000/student_dashboard.html`  
Gawin hard refresh: **Ctrl + Shift + R**. Dapat wala na ang Dark Mode button sa sidebar.
