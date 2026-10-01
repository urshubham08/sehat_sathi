from datetime import datetime, timedelta
from html import escape
from pathlib import Path
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.models import (
    User, Doctor, Appointment, MedicalHistory, MedicalReport,
    PrescriptionPhoto, Payment, PatientProfile
)
from src.ai_chat.services import ask_gemini, explain_medical_report

router = APIRouter(prefix="/clinic", tags=["Clinic Intelligence"])


def current_user(request: Request, db: Session):
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(401, "Please login first.")
    user = db.query(User).filter(User.id == uid, User.is_active == True).first()
    if not user:
        request.session.clear()
        raise HTTPException(401, "User not found.")
    return user


def doctor_for_user(user: User, db: Session):
    if user.role != "doctor":
        return None
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        doctor = db.query(Doctor).filter(Doctor.email == user.email).first()
    return doctor


def can_access_patient(user: User, patient_id: int, db: Session):
    if user.role == "admin":
        return True
    if user.role == "patient":
        return user.id == patient_id
    if user.role == "doctor":
        doctor = doctor_for_user(user, db)
        if not doctor:
            return False
        return db.query(Appointment.id).filter(
            Appointment.doctor_id == doctor.id,
            Appointment.patient_id == patient_id,
        ).first() is not None
    return False


def require_patient_access(user: User, patient_id: int, db: Session):
    if not can_access_patient(user, patient_id, db):
        raise HTTPException(403, "You are not authorized to access this patient's data.")


def patient_snapshot(patient_id: int, db: Session):
    user = db.query(User).filter(User.id == patient_id).first()
    if not user:
        raise HTTPException(404, "Patient not found.")
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == patient_id).first()
    history = db.query(MedicalHistory).filter(MedicalHistory.user_id == patient_id).order_by(MedicalHistory.visit_date.desc()).all()
    appointments = db.query(Appointment).filter(Appointment.patient_id == patient_id).order_by(Appointment.appointment_date.desc()).all()
    reports = db.query(MedicalReport).filter(MedicalReport.patient_id == patient_id).order_by(MedicalReport.uploaded_at.desc()).all()
    prescriptions = db.query(PrescriptionPhoto).filter(PrescriptionPhoto.patient_id == patient_id).order_by(PrescriptionPhoto.uploaded_at.desc()).all()
    payments = db.query(Payment).filter(Payment.patient_id == patient_id).order_by(Payment.created_at.desc()).all()
    return user, profile, history, appointments, reports, prescriptions, payments


def html_page(title: str, body: str):
    return f'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title>
<style>body{{font-family:Arial;margin:0;background:#f4f7fb;color:#172033}}.wrap{{max-width:1200px;margin:25px auto;padding:20px}}.card{{background:#fff;border-radius:14px;padding:20px;margin:14px 0;box-shadow:0 5px 20px #0000000d}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}}.btn{{display:inline-block;padding:10px 14px;border-radius:8px;background:#0f766e;color:#fff;text-decoration:none;border:0}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border-bottom:1px solid #e5e7eb;text-align:left}}.muted{{color:#64748b}}.risk{{font-weight:700}}@media(max-width:700px){{.wrap{{padding:10px}}table{{font-size:13px}}}}</style></head><body><div class="wrap"><h1>{escape(title)}</h1>{body}</div></body></html>'''


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if user.role == "doctor":
        doctor = doctor_for_user(user, db)
        if not doctor:
            return HTMLResponse(html_page("Doctor Dashboard", '<div class="card">Doctor account is not linked to a doctor profile yet.</div>'))
        today = datetime.now().date()
        appointments = db.query(Appointment).filter(Appointment.doctor_id == doctor.id, Appointment.appointment_date >= today).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
        rows = ''.join(f'<tr><td>{a.appointment_date}</td><td>{a.appointment_time}</td><td>Patient #{a.patient_id}</td><td>{escape(a.status)}</td><td><a class="btn" href="/clinic/patient/{a.patient_id}">Open</a></td></tr>' for a in appointments)
        body = f'<div class="card"><b>Doctor:</b> {escape(doctor.name)}<br><span class="muted">{escape(doctor.specialty)}</span></div><div class="card"><h2>My appointments</h2><table><tr><th>Date</th><th>Time</th><th>Patient</th><th>Status</th><th></th></tr>{rows or "<tr><td colspan=5>No appointments.</td></tr>"}</table></div>'
        return HTMLResponse(html_page("Doctor Dashboard", body))
    if user.role == "patient":
        return RedirectResponse("/clinic/patient/%s" % user.id, 303)
    patients = db.query(User).filter(User.role == "patient").count()
    doctors = db.query(Doctor).count()
    appointments = db.query(Appointment).count()
    paid = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.payment_status == "paid").scalar()
    body = f'<div class="grid"><div class="card"><h2>{patients}</h2><div>Patients</div></div><div class="card"><h2>{doctors}</h2><div>Doctors</div></div><div class="card"><h2>{appointments}</h2><div>Appointments</div></div><div class="card"><h2>₹{paid}</h2><div>Paid revenue</div></div></div><div class="card"><a class="btn" href="/clinic/admin">Open Admin Analytics</a></div>'
    return HTMLResponse(html_page("Clinic Dashboard", body))


@router.get("/patient/{patient_id}", response_class=HTMLResponse)
def patient_360(patient_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    require_patient_access(user, patient_id, db)
    patient, profile, history, appointments, reports, prescriptions, payments = patient_snapshot(patient_id, db)
    h = ''.join(f'<li>{x.visit_date}: {escape(x.symptoms or "")} — {escape(x.diagnosis or "")} — {escape(x.treatment or "")}</li>' for x in history) or '<li>No history.</li>'
    a = ''.join(f'<li>{x.appointment_date} {x.appointment_time} — doctor #{x.doctor_id} — {escape(x.status)}</li>' for x in appointments) or '<li>No appointments.</li>'
    r = ''.join(f'<li>{escape(x.original_filename)} — <a href="/medical-reports/{x.id}/view">View</a></li>' for x in reports) or '<li>No reports.</li>'
    p = ''.join(f'<li>{escape(x.original_filename)} — <a href="/prescriptions/{x.id}/view">View</a></li>' for x in prescriptions) or '<li>No prescriptions.</li>'
    pay = ''.join(f'<li>₹{x.amount} — {escape(x.payment_status)} — {escape(x.transaction_reference or "")}</li>' for x in payments) or '<li>No payments.</li>'
    profile_text = f'Blood group: {escape(profile.blood_group or "N/A")} · Allergies: {escape(profile.allergies or "N/A")} · Conditions: {escape(profile.existing_conditions or "N/A")}' if profile else 'No profile details.'
    body = f'<div class="card"><h2>{escape(patient.name)}</h2><div>{profile_text}</div></div><div class="grid"><div class="card"><h3>Medical History</h3><ul>{h}</ul></div><div class="card"><h3>Appointments</h3><ul>{a}</ul></div><div class="card"><h3>Reports</h3><ul>{r}</ul></div><div class="card"><h3>Prescriptions</h3><ul>{p}</ul></div><div class="card"><h3>Payments</h3><ul>{pay}</ul></div></div><div class="card"><a class="btn" href="/clinic/patient/{patient_id}/ai-summary">🤖 AI Summary</a> <a class="btn" href="/clinic/patient/{patient_id}/risk">Health Analytics</a></div>'
    return HTMLResponse(html_page("Patient 360", body))


@router.get("/patient/{patient_id}/ai-summary", response_class=HTMLResponse)
def ai_summary(patient_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db); require_patient_access(user, patient_id, db)
    patient, profile, history, appointments, reports, prescriptions, payments = patient_snapshot(patient_id, db)
    report_texts = []
    from src.medical_reports.routes import extract_pdf_text
    for report in reports[:5]:
        try: report_texts.append(extract_pdf_text(report.file_path))
        except Exception: pass
    context = f'''Patient: {patient.name}\nProfile: {profile.existing_conditions if profile else ""}\nAllergies: {profile.allergies if profile else ""}\nHistory: {[{"date":str(x.visit_date),"symptoms":x.symptoms,"diagnosis":x.diagnosis,"treatment":x.treatment} for x in history[:10]]}\nAppointments: {[str(x.appointment_date) for x in appointments[:10]]}\nReports: {report_texts}'''
    prompt = 'Create a concise patient information summary. Do not diagnose, prescribe, or recommend treatment changes. Highlight documented history, report findings, appointments, and items a clinician may review.\n\n' + context
    try: summary = ask_gemini(prompt)
    except Exception: summary = 'AI summary is temporarily unavailable.'
    return HTMLResponse(html_page('AI Patient Summary', f'<div class="card"><pre style="white-space:pre-wrap">{escape(summary)}</pre></div>'))


@router.get("/patient/{patient_id}/risk", response_class=HTMLResponse)
def risk(patient_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db); require_patient_access(user, patient_id, db)
    _, profile, history, appointments, reports, prescriptions, _ = patient_snapshot(patient_id, db)
    score = 0
    score += min(len(history), 5)
    score += min(len(reports), 3)
    score += min(len(appointments), 2)
    if profile and profile.existing_conditions: score += 2
    if profile and profile.allergies: score += 1
    level = 'Low' if score <= 2 else 'Medium' if score <= 5 else 'High'
    return HTMLResponse(html_page('Health Risk Analytics', f'<div class="card"><div class="risk">Indicator: {level}</div><p>This is an information/analytics indicator, not a diagnosis or medical decision.</p><p>Data points considered: history {len(history)}, reports {len(reports)}, appointments {len(appointments)}.</p></div>'))


@router.get("/patient/{patient_id}/compare-reports", response_class=HTMLResponse)
def compare_reports(patient_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db); require_patient_access(user, patient_id, db)
    reports = db.query(MedicalReport).filter(MedicalReport.patient_id == patient_id).order_by(MedicalReport.uploaded_at.desc()).limit(2).all()
    if len(reports) < 2: return HTMLResponse(html_page('Report Comparison', '<div class="card">At least two reports are required.</div>'))
    from src.medical_reports.routes import extract_pdf_text
    texts=[]
    for r in reports:
        try: texts.append(extract_pdf_text(r.file_path))
        except Exception: texts.append('')
    prompt=f'''Compare these two medical reports in simple language. Do not diagnose or prescribe. Clearly separate what is documented, what changed, and what is unclear. Older report:\n{texts[1]}\n\nLatest report:\n{texts[0]}'''
    try: result=ask_gemini(prompt)
    except Exception: result='AI comparison is temporarily unavailable.'
    return HTMLResponse(html_page('AI Report Comparison', f'<div class="card"><pre style="white-space:pre-wrap">{escape(result)}</pre></div>'))


@router.get("/admin", response_class=HTMLResponse)
def admin_analytics(request: Request, db: Session = Depends(get_db)):
    user=current_user(request,db)
    if user.role != 'admin': raise HTTPException(403,'Admin access required.')
    patients=db.query(User).filter(User.role=='patient').count(); doctors=db.query(Doctor).count(); appts=db.query(Appointment).count(); paid=db.query(func.coalesce(func.sum(Payment.amount),0)).filter(Payment.payment_status=='paid').scalar(); cancelled=db.query(Appointment).filter(Appointment.status=='cancelled').count()
    body=f'<div class="grid"><div class="card"><h2>{patients}</h2>Patients</div><div class="card"><h2>{doctors}</h2>Doctors</div><div class="card"><h2>{appts}</h2>Appointments</div><div class="card"><h2>{cancelled}</h2>Cancelled</div><div class="card"><h2>₹{paid}</h2>Paid Revenue</div></div>'
    return HTMLResponse(html_page('Advanced Admin Analytics',body))


@router.get("/calendar", response_class=HTMLResponse)
def calendar(request: Request, db: Session=Depends(get_db)):
    user=current_user(request,db)
    q=db.query(Appointment)
    if user.role=='patient': q=q.filter(Appointment.patient_id==user.id)
    elif user.role=='doctor':
        doctor=doctor_for_user(user,db)
        if not doctor: q=q.filter(Appointment.id==-1)
        else: q=q.filter(Appointment.doctor_id==doctor.id)
    elif user.role != 'admin': raise HTTPException(403,'Not authorized.')
    appts=q.order_by(Appointment.appointment_date,Appointment.appointment_time).limit(100).all()
    rows=''.join(f'<tr><td>{a.appointment_date}</td><td>{a.appointment_time}</td><td>Patient #{a.patient_id}</td><td>Doctor #{a.doctor_id}</td><td>{escape(a.status)}</td></tr>' for a in appts)
    return HTMLResponse(html_page('Calendar',f'<div class="card"><table><tr><th>Date</th><th>Time</th><th>Patient</th><th>Doctor</th><th>Status</th></tr>{rows or "<tr><td colspan=5>No appointments.</td></tr>"}</table></div>'))


@router.get("/medical-report/{report_id}/print", response_class=HTMLResponse)
def printable_report(report_id:int, request:Request, db:Session=Depends(get_db)):
    user=current_user(request,db); report=db.query(MedicalReport).filter(MedicalReport.id==report_id).first()
    if not report: raise HTTPException(404,'Report not found.')
    require_patient_access(user,report.patient_id,db)
    patient=db.query(User).filter(User.id==report.patient_id).first()
    settings=db.query(ClinicSetting).filter(ClinicSetting.id==1).first()
    clinic_name=(settings.clinic_name if settings else 'Sanjeevani Smart Clinic')
    owner=(settings.owner_name if settings and settings.owner_name else 'Authorized Clinic Owner')
    license_no=(settings.license_number if settings and settings.license_number else 'DEMO / NOT VALID')
    return HTMLResponse(html_page('Printable Medical Report',f'''<div class="card"><h2>{escape(clinic_name)}</h2><p><b>Patient:</b> {escape(patient.name)}</p><p><b>Report:</b> {escape(report.original_filename)}</p><p><b>Uploaded:</b> {report.uploaded_at}</p><hr><p><a class="btn" href="/medical-reports/{report.id}/view">Open Original PDF</a></p><hr><p><b>Clinic Owner:</b> {escape(owner)}</p><p><b>Licence No.:</b> {escape(license_no)}</p><p style="margin-top:45px"><b>[AUTHORIZED CLINIC STAMP]</b></p><p>Authorized Signature: ____________________</p><p class="muted">Official licence/stamp/signature must be supplied by the authorized clinic.</p><button class="btn" onclick="window.print()">🖨️ Print</button></div>'''))


@router.get("/payment/{payment_id}/receipt.pdf")
def pdf_receipt(payment_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(404, "Payment not found.")
    if user.role != "admin" and payment.patient_id != user.id:
        raise HTTPException(403, "You are not authorized to access this receipt.")
    if payment.payment_status != "paid":
        raise HTTPException(400, "Receipt is available only after successful payment.")
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    out_dir = Path("artifacts") / "receipts"; out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"receipt_{payment.id}.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20); c.drawString(50, height-60, "Sanjeevani Smart Clinic")
    c.setFont("Helvetica", 11); c.drawString(50, height-85, "Payment Receipt")
    lines = [
        f"Receipt ID: {payment.id}",
        f"Patient ID: {payment.patient_id}",
        f"Appointment ID: {payment.appointment_id or 'N/A'}",
        f"Amount Paid: INR {payment.amount}",
        f"Payment Method: {payment.payment_method}",
        f"Status: {payment.payment_status}",
        f"Razorpay Order ID: {payment.transaction_reference or 'N/A'}",
        f"Razorpay Payment ID: {payment.razorpay_payment_id or 'N/A'}",
        f"Payment Date: {payment.payment_date or payment.created_at}",
    ]
    y=height-130
    for line in lines:
        c.drawString(60,y,line); y-=24
    c.setFont("Helvetica-Oblique",9); c.drawString(60,80,"Computer-generated receipt. Test Mode payments are not real-money transactions.")
    c.save()
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@router.get("/admin/settings", response_class=HTMLResponse)
def clinic_settings_page(request: Request, db: Session = Depends(get_db)):
    user=current_user(request,db)
    if user.role != "admin": raise HTTPException(403,"Admin access required.")
    setting=db.query(ClinicSetting).filter(ClinicSetting.id==1).first()
    if not setting:
        setting=ClinicSetting(id=1); db.add(setting); db.commit(); db.refresh(setting)
    body=(
        '<div class="card"><form method="post" action="/clinic/admin/settings">'
        f'<p>Clinic name<br><input name="clinic_name" value="{escape(setting.clinic_name or "")}" required></p>'
        f'<p>Owner<br><input name="owner_name" value="{escape(setting.owner_name or "")}"></p>'
        f'<p>Licence number<br><input name="license_number" value="{escape(setting.license_number or "")}"></p>'
        f'<p>Address<br><textarea name="address">{escape(setting.address or "")}</textarea></p>'
        f'<p>Phone<br><input name="phone" value="{escape(setting.phone or "")}"></p>'
        '<button class="btn">Save</button></form></div>'
    )
    return HTMLResponse(html_page("Clinic Settings", body))


@router.post("/admin/settings")
def save_clinic_settings(request: Request, clinic_name:str=Form(...), owner_name:str=Form(""), license_number:str=Form(""), address:str=Form(""), phone:str=Form(""), db:Session=Depends(get_db)):
    user=current_user(request,db)
    if user.role!="admin": raise HTTPException(403,"Admin access required.")
    setting=db.query(ClinicSetting).filter(ClinicSetting.id==1).first()
    if not setting: setting=ClinicSetting(id=1); db.add(setting)
    setting.clinic_name=clinic_name.strip(); setting.owner_name=owner_name.strip() or None; setting.license_number=license_number.strip() or None; setting.address=address.strip() or None; setting.phone=phone.strip() or None
    db.commit(); return RedirectResponse('/clinic/admin/settings',303)


class DoctorDocumentIn(BaseModel):
    doctor_id:int
    patient_id:int
    document_type:str=Field(min_length=2,max_length=50)
    title:str=Field(min_length=2,max_length=200)
    content:str=Field(min_length=1,max_length=8000)


@router.post('/doctor-documents')
def create_doctor_document(payload:DoctorDocumentIn, request:Request, db:Session=Depends(get_db)):
    user=current_user(request,db)
    if user.role not in {'doctor','admin'}: raise HTTPException(403,'Only doctor/admin can create documents.')
    if user.role=='doctor':
        doctor=doctor_for_user(user,db)
        if not doctor or doctor.id!=payload.doctor_id: raise HTTPException(403,'Doctor can create documents only for their own profile.')
    if not can_access_patient(user,payload.patient_id,db): raise HTTPException(403,'Patient is not assigned to this doctor.')
    item=DoctorDocument(doctor_id=payload.doctor_id,patient_id=payload.patient_id,created_by=user.id,document_type=payload.document_type,title=payload.title,content=payload.content)
    db.add(item); db.commit(); db.refresh(item); return {'id':item.id}


class FeedbackIn(BaseModel):
    appointment_id:int
    rating:int=Field(ge=1,le=5)
    comment:str=Field(default='',max_length=2000)


@router.post('/feedback')
def feedback(payload:FeedbackIn, request:Request, db:Session=Depends(get_db)):
    user=current_user(request,db)
    if user.role!='patient': raise HTTPException(403,'Only patients can submit feedback.')
    appt=db.query(Appointment).filter(Appointment.id==payload.appointment_id,Appointment.patient_id==user.id).first()
    if not appt: raise HTTPException(404,'Appointment not found.')
    # Store in audit log until optional dedicated feedback table migration is applied.
    log=AuditLog(user_id=user.id,action='feedback',target_type='appointment',target_id=appt.id,details=f'rating={payload.rating};comment={payload.comment}')
    db.add(log); db.commit()
    return {'success':True}


class FollowupIn(BaseModel):
    patient_id:int
    reminder_at:datetime
    note:str=Field(min_length=1,max_length=1000)


@router.post('/followups')
def followup(payload:FollowupIn, request:Request, db:Session=Depends(get_db)):
    user=current_user(request,db); require_patient_access(user,payload.patient_id,db)
    f=FollowUp(patient_id=payload.patient_id,created_by=user.id,reminder_at=payload.reminder_at,note=payload.note,status='pending')
    db.add(f); db.commit(); db.refresh(f); return {'id':f.id,'status':f.status}


@router.get('/notifications')
def notifications(request:Request,db:Session=Depends(get_db)):
    user=current_user(request,db)
    return [{'id':n.id,'title':n.title,'message':n.message,'is_read':n.is_read,'created_at':n.created_at} for n in db.query(Notification).filter(Notification.user_id==user.id).order_by(Notification.created_at.desc()).limit(50).all()]


@router.get('/faq', response_class=HTMLResponse)
def faq(request:Request,db:Session=Depends(get_db)):
    current_user(request,db)
    return HTMLResponse(html_page('Clinic AI FAQ','<div class="card"><p>Ask the clinic assistant about timings, doctors, fees, booking, payment and cancellation policy.</p><form method="post" action="/clinic/faq"><input name="question" style="width:80%;padding:12px" required><button class="btn">Ask</button></form></div>'))


@router.post('/faq', response_class=HTMLResponse)
def faq_answer(request:Request,question:str=Form(...),db:Session=Depends(get_db)):
    current_user(request,db)
    context='Clinic FAQ: explain only clinic operations. Do not diagnose, prescribe, or provide emergency medical decisions. If medical advice is requested, direct to a qualified clinician. Known policy: cancellation refunds 24+100%, 12-24 90%, 6-12 75%, 2-6 50%, 0-2 20%, past 0%.'
    try: answer=ask_gemini(context+'\nQuestion: '+question.strip())
    except Exception: answer='FAQ assistant is temporarily unavailable.'
    return HTMLResponse(html_page('Clinic AI FAQ',f'<div class="card"><b>Question:</b> {escape(question)}<hr><pre style="white-space:pre-wrap">{escape(answer)}</pre></div><a class="btn" href="/clinic/faq">Ask another</a>'))


# Models are imported late to keep this module readable.
from src.database.models import Notification, FollowUp, AuditLog, ClinicSetting, DoctorDocument
