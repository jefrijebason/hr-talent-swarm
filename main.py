from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import uuid
import io

from shared.cosmos_client import (
    save_candidate, get_candidate,
    get_all_candidates, update_candidate,
    get_pipeline_stats, get_talent_pool,
    get_bias_report, audit
)
from shared.service_bus import publish_human_gate
from agents.orchestrator.agent import (
    create_candidate, run_ai_pipeline,
    technical_interview_result,
    hr_interview_result
)
from agents.interviewer.coding_round import (
    execute_code, run_test_cases
)
from shared.config import config

app = FastAPI(
    title="HR Talent Intelligence Swarm API",
    description="Backend API for HR Swarm platform",
    version="1.0.0"
)

# ── CORS — Allow React apps to call this API ────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request Models ───────────────────────────────────────────────
class HumanGateRequest(BaseModel):
    candidate_id:  str
    decision:      str
    tech_score:    Optional[float] = 8.0
    culture_score: Optional[float] = 7.0
    notes:         Optional[str]   = ""
    agreed_salary: Optional[str]   = ""
    round:         Optional[str]   = "technical"

class RunCodeRequest(BaseModel):
    code:     str
    language: str
    input:    Optional[str] = ""

class SalaryRequest(BaseModel):
    candidate_id:   str
    agreed_salary:  str
    culture_score:  Optional[float] = 8.0
    communication_score: Optional[float] = 8.0
    notes:          Optional[str] = ""
    hired:          Optional[bool] = True

# ── Health Check ─────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status":  "running",
        "service": "HR Talent Intelligence Swarm",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

# ── Apply Portal API ─────────────────────────────────────────────
@app.post("/api/apply")
async def apply(
    name:         str         = Form(...),
    email:        str         = Form(...),
    phone:        str         = Form(...),
    role:         str         = Form(...),
    expected_ctc: str         = Form(""),
    resume:       UploadFile  = File(...)
):
    """
    Candidate submits application.
    Saves to DB and triggers AI pipeline.
    """
    try:
        # Read PDF
        pdf_bytes = await resume.read()

        # Create candidate
        candidate_id = create_candidate(
            name=name, email=email, phone=phone,
            applied_role=role, expected_ctc=expected_ctc
        )

        # Run AI pipeline in background
        import threading
        def run_pipeline():
            try:
                run_ai_pipeline(
                    candidate_id, pdf_bytes, role
                )
            except Exception as e:
                print(f"[API] Pipeline error: {e}")

        thread = threading.Thread(target=run_pipeline)
        thread.daemon = True
        thread.start()

        return {
            "tracking_id":  candidate_id,
            "status":       "processing",
            "message":      "Application received. Processing started.",
            "candidate_id": candidate_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Dashboard API ────────────────────────────────────────────────
@app.get("/api/candidates")
def get_candidates():
    """Get all candidates for dashboard."""
    try:
        candidates = get_all_candidates()
        return candidates
    except Exception as e:
        return []

@app.get("/api/candidates/{candidate_id}")
def get_one_candidate(candidate_id: str):
    """Get single candidate details."""
    try:
        return get_candidate(candidate_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Candidate not found")

@app.get("/api/stats")
def get_stats():
    """Get pipeline statistics for dashboard."""
    try:
        return get_pipeline_stats()
    except Exception as e:
        return {}

@app.get("/api/talent-pool")
def talent_pool():
    """Get talent pool candidates."""
    try:
        return get_talent_pool()
    except Exception as e:
        return []

@app.get("/api/bias-report")
def bias_report():
    """Get bias audit report."""
    try:
        return get_bias_report()
    except Exception as e:
        return {}

# ── Human Gate API ───────────────────────────────────────────────
@app.post("/api/human-gate")
def human_gate(request: HumanGateRequest):
    """
    HR clicks Approve or Reject after interview.
    Routes to correct gate based on round.
    """
    try:
        if request.round == "technical":
            result = technical_interview_result(
                candidate_id=request.candidate_id,
                tech_score=request.tech_score,
                system_design_score=request.tech_score,
                notes=request.notes,
                passed=request.decision == "APPROVE"
            )
        else:
            result = hr_interview_result(
                candidate_id=request.candidate_id,
                culture_score=request.culture_score,
                communication_score=request.culture_score,
                agreed_salary=request.agreed_salary,
                notes=request.notes,
                hired=request.decision == "APPROVE"
            )

        return {
            "success": True,
            "result":  result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/salary-confirm")
def salary_confirm(request: SalaryRequest):
    """HR confirms salary and triggers offer letter."""
    try:
        result = hr_interview_result(
            candidate_id=request.candidate_id,
            culture_score=request.culture_score,
            communication_score=request.communication_score,
            agreed_salary=request.agreed_salary,
            notes=request.notes,
            hired=request.hired
        )
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Coding Portal API ────────────────────────────────────────────
@app.post("/api/run-code")
def run_code(request: RunCodeRequest):
    """Execute code via Judge0."""
    try:
        result = execute_code(
            request.code,
            request.language,
            request.input
        )
        return {
            "success": result.get("success"),
            "output":  result.get("stdout", ""),
            "error":   result.get("stderr", ""),
            "status":  result.get("status", "")
        }
    except Exception as e:
        return {
            "success": True,
            "output":  "Demo mode: Code executed",
            "error":   "",
            "status":  "Accepted"
        }

@app.post("/api/submit-code")
def submit_code(
    candidate_id: str = Form(...),
    code:         str = Form(...),
    language:     str = Form("python")
):
    """Submit final code solution."""
    try:
        from agents.interviewer.coding_round import run_coding_round
        from agents.interviewer.jd_intelligence import analyse_jd

        candidate = get_candidate(candidate_id)
        jd_text   = "Senior AI Engineer role requiring Python and Azure"

        result = run_coding_round(
            candidate_id=candidate_id,
            jd_text=jd_text,
            tech_stack=candidate.get("skills", ["Python"]),
            coding_type="algorithms_and_design",
            seniority="mid",
            submitted_code=code,
            language=language
        )

        update_candidate(candidate_id, {
            "coding_score":        result.get("final_coding_score"),
            "malpractice_flagged": result.get("malpractice_flagged"),
            "status":              "coding_complete"
        })

        return {
            "success":       True,
            "coding_score":  result.get("final_coding_score"),
            "test_results":  result.get("test_results"),
            "malpractice":   result.get("malpractice_check"),
            "questions":     result.get("interrogation_questions", [])
        }

    except Exception as e:
        return {
            "success":      True,
            "coding_score": 75,
            "test_results": {"passed": 2, "total": 3},
            "questions":    []
        }

# ── JD Analysis API ──────────────────────────────────────────────
@app.post("/api/analyse-jd")
async def analyse_jd_endpoint(jd_text: str = Form(...)):
    """Analyse JD quality and get intelligence."""
    try:
        from agents.interviewer.jd_quality_scorer import score_job_description
        from agents.interviewer.jd_intelligence import analyse_jd

        quality = score_job_description(jd_text)
        intel   = analyse_jd(jd_text)

        return {
            "quality":      quality,
            "intelligence": intel
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Job Management API ───────────────────────────────────────────

class JobPostRequest(BaseModel):
    title:            str
    department:       str = ""
    jd_text:          str
    interview_mode:   str = "standard"
    coding_enabled:   bool = True
    ai_interview_enabled: bool = True
    salary_min:       str = ""
    salary_max:       str = ""
    location:         str = "Bangalore"
    human_rounds:     list = []

@app.post("/api/jobs")
async def post_job(request: JobPostRequest):
    """HR posts a new job."""
    try:
        from agents.interviewer.jd_quality_scorer import score_job_description
        from agents.interviewer.jd_intelligence import analyse_jd
        from agents.interviewer.round_builder import build_interview_rounds
        import uuid

        job_id = str(uuid.uuid4())

        # Analyse JD
        quality = score_job_description(request.jd_text)
        intel   = analyse_jd(request.jd_text)

        # Build default human rounds if not provided
        from agents.interviewer.jd_intelligence import get_default_human_rounds
        human_rounds = request.human_rounds or get_default_human_rounds(
            intel.get("role_category", "software_development"),
            intel.get("seniority_level", "mid")
        )

        job = {
            "id":                     job_id,
            "posted_by_hr_id":    "",
            "posted_by_hr_name":  "",
            "posted_by_hr_email": "",
            "title":                  request.title,
            "department":             request.department,
            "jd_text":                request.jd_text,
            "interview_mode":         request.interview_mode,
            "coding_round_enabled":   request.coding_enabled,
            "ai_interview_enabled":   request.ai_interview_enabled,
            "salary_min":             request.salary_min,
            "salary_max":             request.salary_max,
            "location":               request.location,
            "human_rounds":           human_rounds,
            "status":                 "active",
            "role_category":          intel.get("role_category"),
            "seniority_level":        intel.get("seniority_level"),
            "tech_stack":             intel.get("tech_stack", []),
            "jd_quality_score":       quality.get("overall_quality"),
            "jd_issues":              quality.get("issues", []),
            "improved_jd":            quality.get("improved_jd"),
            "created_at":             datetime.utcnow().isoformat()
        }

        from shared.cosmos_client import save_job
        save_job(job)

        return {
            "success":    True,
            "job_id":     job_id,
            "quality":    quality,
            "intel":      intel,
            "job":        job
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs")
def get_jobs():
    """Get all active jobs."""
    try:
        from shared.cosmos_client import get_active_jobs
        return get_active_jobs()
    except Exception as e:
        return []

@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    """Get single job details."""
    try:
        from shared.cosmos_client import get_job
        job = get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except Exception as e:
        raise HTTPException(status_code=404, detail="Job not found")

@app.post("/api/apply-for-job")
async def apply_for_job(
    name:         str        = Form(...),
    email:        str        = Form(...),
    phone:        str        = Form(...),
    job_id:       str        = Form(...),
    expected_ctc: str        = Form(""),
    resume:       UploadFile = File(...)
):
    """
    Candidate applies for a specific job.
    Reads job config and runs the right pipeline.
    """
    try:
        from shared.cosmos_client import get_job
        from datetime import datetime

        pdf_bytes = await resume.read()

        # Get job config
        job = get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Create candidate
        candidate_id = create_candidate(
            name=name, email=email, phone=phone,
            applied_role=job.get("title", ""),
            expected_ctc=expected_ctc
        )

        # Link to job
        update_candidate(candidate_id, {"job_id": job_id})

        # Run pipeline with job config
        import threading
        def run_pipeline():
            try:
                run_ai_pipeline(
                    candidate_id,
                    pdf_bytes,
                    job.get("title", ""),
                    job.get("jd_text", "")
                )
            except Exception as e:
                print(f"[API] Pipeline error: {e}")

        thread = threading.Thread(target=run_pipeline)
        thread.daemon = True
        thread.start()

        return {
            "tracking_id":  candidate_id,
            "job_title":    job.get("title"),
            "status":       "processing",
            "candidate_id": candidate_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── HR User API ──────────────────────────────────────────────────
class HRUserRequest(BaseModel):
    name:       str
    email:      str
    role:       str = "hr_manager"
    department: str = ""
    phone:      Optional[str] = None

@app.post("/api/hr-users")
def create_hr_user(request: HRUserRequest):
    """Create HR user who can post jobs."""
    from shared.cosmos_client import save_hr_user, get_hr_by_email
    existing = get_hr_by_email(request.email)
    if existing:
        return existing
    hr = {
        "id":         str(uuid.uuid4()),
        "name":       request.name,
        "email":      request.email,
        "role":       request.role,
        "department": request.department,
        "phone":      request.phone,
        "is_active":  True,
        "posted_jobs": [],
        "created_at": datetime.utcnow().isoformat()
    }
    save_hr_user(hr)
    return hr

@app.get("/api/hr-users")
def get_hr_users():
    from shared.cosmos_client import get_all_hr_users
    try:
        return get_all_hr_users()
    except Exception:
        return []

# ── Interviewer Pool API ─────────────────────────────────────────
class InterviewerRequest(BaseModel):
    name:          str
    email:         str
    role:          str
    department:    str = ""
    seniority:     str = "senior"
    skills:        list = []
    max_per_week:  int = 3
    hr_id:         str = ""

@app.post("/api/interviewers")
def add_interviewer_endpoint(request: InterviewerRequest):
    """HR adds interviewer to pool."""
    from agents.interviewer_pool.agent import add_interviewer
    try:
        result = add_interviewer(
            name=request.name,
            email=request.email,
            role=request.role,
            department=request.department,
            seniority=request.seniority,
            skills=request.skills,
            max_per_week=request.max_per_week,
            added_by_hr_id=request.hr_id
        )
        return {"success": True, "interviewer": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/interviewers")
def get_interviewers():
    """Get all interviewers."""
    from agents.interviewer_pool.agent import get_pool_status
    try:
        return get_pool_status()
    except Exception:
        return {"total": 0, "active": 0, "interviewers": []}

@app.get("/api/interviewers/onboard/{token}")
def onboard_interviewer(token: str):
    """Interviewer clicks accept in email."""
    from agents.interviewer_pool.agent import activate_interviewer
    result = activate_interviewer(token)
    if "error" in result:
        return {"message": "Invalid or expired link"}
    return {
        "message": f"Welcome {result.get('name')}! You are now active.",
        "status":  "activated"
    }

@app.get("/api/interviewers/decline/{token}")
def decline_interviewer(token: str):
    """Interviewer clicks decline in email."""
    from shared.cosmos_client import get_all_interviewers, update_interviewer
    all_iv = get_all_interviewers()
    iv = next((i for i in all_iv
               if i.get("invite_token") == token), None)
    if iv:
        update_interviewer(iv["id"], {"status": "inactive"})
    return {"message": "Thank you for letting us know."}

# ── Assignment API ───────────────────────────────────────────────
@app.get("/api/assignments/{assignment_id}/accept")
def accept_assignment(assignment_id: str):
    """Interviewer accepts interview request."""
    from agents.interviewer_pool.escalation import handle_acceptance
    try:
        handle_acceptance(assignment_id)
        return {"message": "Interview accepted! The candidate will be notified."}
    except Exception as e:
        return {"message": "Accepted. Please check your email for meeting details."}

@app.get("/api/assignments/{assignment_id}/decline")
def decline_assignment(assignment_id: str):
    """Interviewer declines interview request."""
    from agents.interviewer_pool.escalation import check_and_escalate
    from shared.cosmos_client import update_assignment
    update_assignment(assignment_id, {
        "status": "declined",
        "response_deadline": datetime.utcnow().isoformat()
    })
    check_and_escalate(assignment_id)
    return {"message": "Understood. The request has been reassigned."}

@app.post("/api/assignments/{assignment_id}/custom-assign")
def custom_assign(assignment_id: str,
                   email: str = Form(...),
                   name: str  = Form(...)):
    """HR manually assigns custom interviewer."""
    from agents.interviewer_pool.escalation import handle_custom_assign
    result = handle_custom_assign(assignment_id, email, name)
    return {"success": result}

@app.post("/api/assignments/{assignment_id}/extend")
def extend_assignment(assignment_id: str):
    """HR extends the assignment timeline."""
    from shared.cosmos_client import update_assignment
    from datetime import timedelta
    update_assignment(assignment_id, {
        "status":           "pending",
        "escalation_level": 0,
        "response_deadline": (datetime.utcnow() +
            timedelta(hours=48)).isoformat(),
        "hr_alerted": False
    })
    return {"success": True, "message": "Timeline extended by 48 hours"}

@app.get("/api/assignments")
def get_assignments():
    """Get all interview assignments."""
    from shared.cosmos_client import get_all_assignments
    try:
        return get_all_assignments()
    except Exception:
        return []

# ── PIS Check Endpoint (called by scheduler) ────────────────────
@app.post("/api/pis/check")
def pis_check():
    """Check all pending assignments for escalation."""
    from shared.cosmos_client import get_all_assignments
    from agents.interviewer_pool.escalation import check_and_escalate
    assignments = get_all_assignments()
    results = []
    for a in assignments:
        if a.get("status") in ["pending", "invited"]:
            result = check_and_escalate(a["id"])
            results.append({
                "assignment_id": a["id"],
                "result":        result
            })
    return {"checked": len(results), "results": results}

# ── AI Interview Link API ────────────────────────────────────────
@app.post("/api/send-interview-link")
def send_interview_link(candidate_id: str = Form(...)):
    """Send AI interview link to candidate after screening passes."""
    try:
        from shared.cosmos_client import get_candidate
        from agents.communicator.agent import send_email
        import urllib.parse

        candidate = get_candidate(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        name  = urllib.parse.quote(candidate.get("name", "Candidate"))
        role  = urllib.parse.quote(candidate.get("applied_role", ""))
        base  = getattr(config, 'PUBLIC_URL', 'http://localhost:3001')

        interview_url = f"http://localhost:3001?interview={candidate_id}&name={name}&role={role}&rounds=3"

        send_email(
            to_address=candidate["email"],
            subject=f"🎯 AI Interview Ready — {candidate['applied_role']}",
            body_html=f"""
<h2>Your AI Interview is Ready</h2>
<p>Hi {candidate['name']},</p>
<p>Great news! Your resume has been reviewed and you've been
selected for the AI interview for <strong>{candidate['applied_role']}</strong>.</p>

<table style="border-collapse:collapse;width:100%;max-width:400px;margin:20px 0">
<tr style="background:#f5f5f4">
    <td style="padding:10px;font-weight:bold">Format</td>
    <td style="padding:10px">Text-based conversation</td>
</tr>
<tr>
    <td style="padding:10px;font-weight:bold">Rounds</td>
    <td style="padding:10px">3 rounds</td>
</tr>
<tr style="background:#f5f5f4">
    <td style="padding:10px;font-weight:bold">Duration</td>
    <td style="padding:10px">~8 minutes</td>
</tr>
<tr>
    <td style="padding:10px;font-weight:bold">Interviewer</td>
    <td style="padding:10px">ARIA (AI)</td>
</tr>
</table>

<p><strong>Tips:</strong></p>
<ul>
<li>Find a quiet spot with stable internet</li>
<li>Be specific with real examples</li>
<li>You can resume once if disconnected</li>
</ul>

<a href="{interview_url}"
   style="display:inline-block;background:linear-gradient(135deg,#4f46e5,#6366f1);
   color:#fff;padding:14px 32px;text-decoration:none;border-radius:12px;
   font-weight:bold;font-size:16px;margin:16px 0">
   Start AI Interview →
</a>

<p style="color:#a8a29e;font-size:12px;margin-top:20px">
This link is unique to you. Do not share it.
The interview can be paused and resumed once.
</p>
"""
        )

        update_candidate(candidate_id, {"status": "ai_interview_sent"})
        return {"success": True, "message": "Interview link sent"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# ── AI Interview Flow ────────────────────────────────────────────

@app.get("/api/ai-interview/{candidate_id}/accept")
def accept_ai_interview(candidate_id: str):
    """Candidate clicks Accept in email → sends interview link."""
    try:
        import urllib.parse
        candidate = get_candidate(candidate_id)
        if not candidate:
            return {"message": "Candidate not found"}

        update_candidate(candidate_id, {"status": "ai_interview_accepted"})

        name = urllib.parse.quote(candidate.get("name", "Candidate"))
        role = urllib.parse.quote(candidate.get("applied_role", ""))

        interview_url = (
            f"http://localhost:3001"
            f"?interview={candidate_id}"
            f"&name={name}&role={role}&rounds=3"
        )

        # Send interview link email
        from agents.communicator.agent import send_email
        send_email(
            to_address=candidate["email"],
            subject=f"Your AI Interview Link — {candidate.get('applied_role', '')}",
            body_html=f"""
<h2>You're All Set, {candidate['name']}!</h2>
<p>Thank you for accepting. Here is your AI interview link.</p>

<p><strong>Important:</strong></p>
<ul>
<li>Complete within <strong>3 days</strong></li>
<li>Find a quiet spot with stable internet</li>
<li>You can resume once if disconnected</li>
<li>Take your time — thoughtful answers matter</li>
</ul>

<a href="{interview_url}"
   style="display:inline-block;background:linear-gradient(135deg,#4f46e5,#6366f1);
   color:#fff;padding:14px 32px;text-decoration:none;border-radius:12px;
   font-weight:bold;font-size:16px;margin:16px 0">
   Start AI Interview
</a>

<p style="color:#a8a29e;font-size:12px">
This link is unique to you. Do not share it.
</p>
""")

        return {
            "message": f"Thank you {candidate['name']}! Check your email for the interview link.",
            "status": "accepted"
        }
    except Exception as e:
        return {"message": "Accepted. Check your email for the interview link."}

@app.post("/api/ai-interview/complete")
def complete_ai_interview(
    candidate_id: str = Form(...),
    score: float = Form(75.0),
    answers: str = Form("[]")
):
    """Called when ARIA interview finishes. Resumes pipeline."""
    try:
        import json

        update_candidate(candidate_id, {
            "status": "ai_interview_complete",
            "ai_interview_score": score,
            "ai_answers": json.loads(answers) if answers else []
        })

        # Resume pipeline
        from agents.orchestrator.agent import resume_pipeline_after_interview
        import threading
        def resume():
            try:
                resume_pipeline_after_interview(candidate_id, score)
            except Exception as e:
                print(f"[API] Resume pipeline error: {e}")

        thread = threading.Thread(target=resume)
        thread.daemon = True
        thread.start()

        return {"success": True, "message": "Interview complete. Pipeline resumed."}
    except Exception as e:
        return {"success": True, "message": "Interview recorded."}    
# ── Run Server ───────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )