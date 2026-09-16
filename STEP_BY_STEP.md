# Zeramai HR — Step-by-Step Setup (Simple Guide)

No Docker, no Postgres, no Node.js needed for this version. Only Python.

## Step 1 — Install Python
Download from https://python.org (version 3.11 or higher). During install,
tick "Add Python to PATH".

## Step 2 — Extract the zip
Unzip `zeramai-hr.zip` anywhere, e.g. Desktop. You'll see a `backend` folder.

## Step 3 — Open a terminal in the backend folder
- Windows: open the `backend` folder, type `cmd` in the address bar, press Enter.
- Mac/Linux: right-click the `backend` folder → "Open Terminal here".

## Step 4 — Install dependencies (one time only)
```
pip install -r requirements.txt
```

## Step 5 — Set up the config file (one time only)
Copy `.env.example` and rename the copy to `.env` (same folder).
No edits needed to try it locally.

## Step 6 — Create demo logins (one time only)
```
python -m app.seed
```
This creates 4 logins:
- superadmin@zeramai.com
- hr@zeramai.com
- manager@zeramai.com
- finance@zeramai.com

Password for all: `ChangeMe123!`

## Step 7 — Start the app
```
uvicorn app.main:app --reload
```
Leave this terminal window open — it's running the app.

## Step 8 — Open it in your browser
Go to: **http://localhost:8000**

Log in with: `hr@zeramai.com` / `ChangeMe123!`

## Step 9 — Try the workflow
1. Fill "Add Candidate" and click **Create Candidate**.
2. In the table, click **Mark Selected** on that candidate.
3. Click **Convert to Trainee** — this creates the 6-month engagement
   with ₹5,000/month stipend and calculates the end date automatically.
4. Copy the Person ID shown in the message, paste it into "Upload a
   Document", pick a file, and click **Upload**.

## To stop the app
Go back to the terminal, press `Ctrl + C`.

## To run it again later
You only need Steps 7–8 (skip 4–6, already done).

## What's included vs. what's next
Included: login, roles, candidate creation, convert-to-trainee, document
upload/download, audit log (behind the scenes).
Not yet included: NDA/offer letter PDF generation, monthly evaluations,
stipend payment tracking, attendance, reports. Tell me to build the next
piece whenever you're ready.
