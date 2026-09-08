# 🏛️ Dean's Email Automation & WhatsApp Digest

An automated executive assistant system designed for a College Dean. It ingests incoming emails, categorizes them by college function (Admissions, Finance, Faculty, Academics, Urgent), extracts arrival timestamps, generates concise 1-sentence summaries, and delivers a consolidated daily digest directly to WhatsApp.

---

## 🚀 Key Features

* **Zero Dean Overhead:** The Dean does not need to open any laptop or app. The report arrives directly on their WhatsApp on their phone.
* **Smart Categorization:** Automatically groups emails into:
  * 🎓 **Admissions & Enrollment**
  * 💳 **Finance & Accounts**
  * 📚 **Academics & Examinations**
  * 👥 **Faculty & HR**
  * 🏛️ **Student Affairs & Campus**
  * 🚨 **Urgent & Action Required**
* **Time Tracking:** Extracts exact arrival timestamps (e.g. `[09:30 AM]`) for every email.
* **1-Sentence Executive Summaries:** Uses Google Gemini (or rule-based heuristics) to condense long emails into a 1-sentence action summary.
* **Dual Deployment:**
  1. **n8n Workflow (`dean_email_digest_workflow.json`)** for visual, scheduled cloud orchestration.
  2. **Python Runner (`main.py`)** for immediate local testing, CLI execution, and dry-runs.

---

## 📱 Sample WhatsApp Digest Output

```text
🏛️ DEAN'S EMAIL DIGEST
📍 College of Engineering & Technology
📅 Date: Tuesday, Sep 8, 2026
📬 Total Inbound: 6 emails
──────────────────────
📊 Category Summary:
  🚨 Urgent: 1 email
  🎓 Admission: 2 emails
  💳 Finance: 1 email
  👥 Faculty: 1 email
  🏛️ Student Affairs: 1 email
──────────────────────
🚨 ACTION REQUIRED / URGENT:
• [10:05 AM] State University Registrar: Mandatory Accreditation Audit Committee Visit scheduled for Friday
──────────────────────
📋 Detailed Highlights:

🎓 ADMISSIONS & ENROLLMENT (2)
• [08:15 AM] Rohan Deshmukh (Applicant): Inquiry regarding B.Tech Computer Science Quota Admission & Eligibility
• [02:50 PM] State Counselling Board (DTE): Round 2 Seat Allotment Matrix & Vacancy Verification for Engineering

💳 FINANCE & ACCOUNTS (1)
• [09:30 AM] Accounts Department: Approval needed: Chemistry Lab Equipment Vendor Invoice #INV-8821

👥 FACULTY & HR (1)
• [01:20 PM] Dr. A. K. Verma (HOD Mech): Faculty Leave Application & Guest Lecture arrangement for next week

🏛️ STUDENT AFFAIRS & CAMPUS (1)
• [11:45 AM] Shreya Patel (Final Year CS): Application for Merit-cum-Means Post-Matric Scholarship Endorsement

──────────────────────
📌 Auto-categorized & tagged in your inbox folders.
```

---

## ⚡ Quickstart (Test Locally in 10 Seconds)

You can test the entire pipeline right now using the built-in mock simulation (no credentials needed):

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run simulation with dry-run preview
python main.py --mock --dry-run
```

---

## ⚙️ Configuration (.env)

When you are ready to connect live services, copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Fill in your credentials:
1. **Email (IMAP / Gmail):**
   * Go to your Google Account $\rightarrow$ Security $\rightarrow$ 2-Step Verification $\rightarrow$ **App Passwords**.
   * Create an App Password and set `EMAIL_PASSWORD`.
2. **AI (Google Gemini):**
   * Visit [Google AI Studio](https://aistudio.google.com/) and grab a free API key. Set `GEMINI_API_KEY`.
3. **WhatsApp (Twilio):**
   * Create a free [Twilio Account](https://www.twilio.com/).
   * Navigate to **Messaging $\rightarrow$ Try it out $\rightarrow$ Send a WhatsApp message** (Twilio Sandbox).
   * Fill in `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `DEAN_WHATSAPP_TO`.

Then run in live mode:
```bash
python main.py --live
```

---

## 🌐 Deploying with n8n

If you are using n8n:

1. Open your n8n web instance (e.g. `http://localhost:5678` or your cloud n8n URL).
2. Click **Workflows $\rightarrow$ Import from File**.
3. Select [`dean_email_digest_workflow.json`](./dean_email_digest_workflow.json).
4. Click on the **Gmail Node** and connect the Dean's Google account via OAuth2.
5. In the **Gemini AI Node**, ensure the `GEMINI_API_KEY` environment variable is set.
6. In the **Twilio Node**, select your Twilio credentials.
7. Toggle the workflow to **Active**!

The workflow will now wake up automatically every morning at 8:00 AM, process the emails, and send the WhatsApp digest directly to the Dean's phone.
