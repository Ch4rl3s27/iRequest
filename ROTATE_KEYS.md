# How to Rotate API Keys & Passwords (If Exposed)

If your `.env` or API keys were shared (e.g. in chat, logs, or public repo), rotate them and update `.env` (and on EC2 if you deploy there).

---

## 1. AWS (Access Key & Secret)

1. Log in to **AWS Console** → **IAM** → **Users** → select your user.
2. **Security credentials** tab → **Access keys**.
3. **Create access key** → choose use case (e.g. Application running outside AWS) → Create.
4. **Copy** the new Access Key ID and Secret (shown once).
5. In your `.env`, replace:
   - `AWS_ACCESS_KEY_ID=` with the new key.
   - `AWS_SECRET_ACCESS_KEY=` with the new secret.
6. (Optional) In IAM, **Delete** the old access key after the app works with the new one.

---

## 2. Groq (API Key)

1. Go to **https://console.groq.com** → **API Keys**.
2. **Create API Key** → name it (e.g. `irequest`) → Create.
3. **Copy** the new key (starts with `gsk_...`).
4. In your `.env`, set:
   - `GROQ_API_KEY=` to the new key.
5. (Optional) Delete the old key in Groq console.

---

## 3. RDS / MySQL (optional)

If you also want to change the DB password:

1. **AWS Console** → **RDS** → your DB instance → **Modify**.
2. Set a new **Master password** → Apply.
3. In `.env`, set `MYSQL_PASSWORD=` to the new password.
4. Restart your app (and EC2 app if deployed).

---

## 4. After Updating `.env`

- **Local:** Restart the Flask app (`python app.py` or your run command).
- **EC2:** Copy the updated `.env` to the server (e.g. `scp` or paste via `nano`), then restart the app (`python app.py`).

Never commit `.env` to Git. Use `env.example` as a template with placeholders only.
