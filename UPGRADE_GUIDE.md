# Sanjeevani Smart Clinic — Consolidated Upgrade

## 1. Important privacy rule
- Patient: only own data.
- Doctor: only patients who have an appointment with that doctor.
- Admin: full medical access.
- Manager: operational/aggregate dashboard only; no patient medical history/report/prescription access.

The restriction is enforced in backend authorization, not only in the UI.

## 2. Database migration
Open MySQL and run:

`sql/clinic_upgrade.sql`

If your MySQL version rejects `ADD COLUMN IF NOT EXISTS`, check `DESCRIBE doctors;` and `DESCRIBE payments;` and run only missing ALTER statements.

## 3. Doctor login linking
A doctor account must have role `doctor` and be linked to its doctor row:

```sql
UPDATE doctors SET user_id = <DOCTOR_USER_ID> WHERE id = <DOCTOR_ID>;
```

The backend also falls back to matching the doctor's email to the user email.

## 4. Install/sync
```powershell
uv sync
```

The project now includes ReportLab for PDF receipt generation and pytest for automated tests.

## 5. Run
```powershell
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## 6. Useful routes
- `/clinic/dashboard`
- `/clinic/admin`
- `/clinic/admin/settings`
- `/clinic/calendar`
- `/clinic/faq`
- `/clinic/notifications`
- `/clinic/patient/<patient_id>`
- `/clinic/patient/<patient_id>/ai-summary`
- `/clinic/patient/<patient_id>/risk`
- `/clinic/patient/<patient_id>/compare-reports`
- `/clinic/medical-report/<report_id>/print`
- `/clinic/payment/<payment_id>/receipt.pdf`

## 7. Clinic identity
Admin can set clinic name, owner, licence number, address and phone at `/clinic/admin/settings`.

Official stamp/signature/licence information must be supplied by the authorized clinic. Do not use fabricated official details.

## 8. Email
Email delivery is optional and activates when SMTP environment variables are configured:
- SMTP_HOST
- SMTP_PORT
- SMTP_FROM
- SMTP_USERNAME
- SMTP_PASSWORD

In-app notifications work without SMTP.

## 9. AI safety
The AI features are informational/analytics support only. They must not diagnose, prescribe, change medicines, or make emergency decisions.

## 10. Secrets
Do not include `.env`, API keys, payment secrets, `.venv`, uploads or personal medical files in ZIPs shared publicly.
