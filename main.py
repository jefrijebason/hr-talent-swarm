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
    get_bias_report, audit, write_audit,
    get_job
)
from shared.service_bus import publish_human_gate
from agents.orchestrator.agent import (
    create_candidate, run_ai_pipeline,
    technical_interview_result,
    hr_interview_result,
    resume_pipeline_after_coding
)
from agents.interviewer.coding_round import (
    execute_code, run_test_cases,
    generate_coding_problem, evaluate_code_quality
)
from agents.interviewer.anti_malpractice import (
    generate_interrogation_questions,
    evaluate_interrogation_answers
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

class CodingInterrogationRequest(BaseModel):
    candidate_id:   str
    submitted_code: str
    language:       str = "python"

class EvaluateInterrogationRequest(BaseModel):
    candidate_id: str
    answers:      dict

class CodingCompleteRequest(BaseModel):
    candidate_id:     str
    coding_score:     float
    malpractice_score: float

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

@app.get("/api/coding-problem")
def get_coding_problem(candidate_id: str):
    """Fetch or generate a coding assignment for the candidate."""
    try:
        candidate = get_candidate(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        problem = candidate.get("coding_problem")
        if not problem:
            job = get_job(candidate.get("job_id", ""))
            jd_text = job.get("jd_text", "Senior AI Engineer role requiring Python and Azure") if job else "Senior AI Engineer role requiring Python and Azure"
            tech_stack = job.get("tech_stack") or candidate.get("skills", ["Python"])
            coding_type = job.get("coding_type", "algorithms_and_design")
            seniority = job.get("seniority_level", "mid")

            problem = generate_coding_problem(
                jd_text,
                tech_stack,
                coding_type,
                seniority
            )
            update_candidate(candidate_id, {"coding_problem": problem})

        return {"success": True, "problem": problem}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/submit-code")
def submit_code(
    candidate_id: str = Form(...),
    code:         str = Form(...),
    language:     str = Form("python")
):
    """Submit final code solution."""
    try:
        candidate = get_candidate(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        job = get_job(candidate.get("job_id", ""))
        jd_text = job.get("jd_text", "Senior AI Engineer role requiring Python and Azure") if job else "Senior AI Engineer role requiring Python and Azure"
        tech_stack = job.get("tech_stack") or candidate.get("skills", ["Python"])
        coding_type = job.get("coding_type", "algorithms_and_design")
        seniority = job.get("seniority_level", "mid")

        problem = candidate.get("coding_problem")
        if not problem:
            problem = generate_coding_problem(
                jd_text,
                tech_stack,
                coding_type,
                seniority
            )
            update_candidate(candidate_id, {"coding_problem": problem})

        test_results = run_test_cases(
            code,
            language,
            problem.get("test_cases", [])
        )

        quality = evaluate_code_quality(code, problem, test_results)
        coding_score = quality.get("overall_coding_score")
        if coding_score is None:
            coding_score = test_results.get("score", 0)

        update_candidate(candidate_id, {
            "coding_submission": code,
            "coding_language": language,
            "coding_score": coding_score,
            "coding_test_results": test_results,
            "coding_quality": quality,
            "status": "coding_sent"
        })

        return {
            "success":      True,
            "coding_score": coding_score,
            "test_results": test_results,
            "quality":      quality
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── JD Analysis API ──────────────────────────────────────────────
@app.post("/api/coding/interrogation")
def coding_interrogation(request: CodingInterrogationRequest):
    """Generate targeted questions for the candidate's submitted code."""
    try:
        candidate = get_candidate(request.candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        job = get_job(candidate.get("job_id", ""))
        role_category = job.get("role_category", "software_development") if job else candidate.get("role_category", "software_development")

        questions = generate_interrogation_questions(
            request.submitted_code,
            "code",
            role_category
        )

        update_candidate(request.candidate_id, {
            "coding_submission": request.submitted_code,
            "coding_language": request.language,
            "interrogation_questions": questions
        })

        return {
            "success":   True,
            "questions": questions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/coding/evaluate-interrogation")
def evaluate_interrogation(request: EvaluateInterrogationRequest):
    """Score the candidate's answers to anti-malpractice questions."""
    try:
        candidate = get_candidate(request.candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        questions = candidate.get("interrogation_questions", [])
        if not questions:
            raise HTTPException(status_code=400, detail="No interrogation questions found for this candidate")

        answer_list = []
        for q in questions:
            key = str(q.get("question_number") or q.get("id") or q.get("question_index") or "")
            answer_list.append(request.answers.get(key, ""))

        result = evaluate_interrogation_answers(
            questions,
            answer_list,
            candidate.get("coding_submission", ""),
            "code"
        )

        update_candidate(request.candidate_id, {
            "malpractice_review": result,
            "malpractice_score": result.get("overall_score")
        })

        return {
            "success": True,
            **result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/coding/complete")
def coding_complete(request: CodingCompleteRequest):
    """Complete coding assessment and resume the pipeline once malpractice review is done."""
    try:
        candidate = get_candidate(request.candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        final_score = round(
            (request.coding_score * 0.7) +
            (request.malpractice_score * 0.3),
            1
        )

        update_candidate(request.candidate_id, {
            "coding_score": request.coding_score,
            "malpractice_score": request.malpractice_score,
            "final_score": final_score,
            "status": "coding_complete"
        })

        resume_pipeline_after_coding(request.candidate_id)

        return {
            "success":     True,
            "final_score": final_score
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

@app.post("/api/ai-interview/evaluate-answer")
def evaluate_ai_answer(
    candidate_id: str = Form(...),
    question: str = Form(...),
    answer: str = Form(...),
    round_num: int = Form(1)
):
    """Evaluate a single answer during the interview in real-time."""
    try:
        # Import the evaluator function (actual name in agent is evaluate_answer)
        from agents.interviewer.answer_evaluator import evaluate_answer

        # Call evaluator — it returns a detailed dict (including 'overall')
        eval_result = evaluate_answer(question, answer, "", "", round_num)

        # Persist evaluation to candidate record
        try:
            candidate = get_candidate(candidate_id)
            if candidate is not None:
                answers = candidate.get("ai_answers", [])
                answers.append({
                    "round": round_num,
                    "question": question,
                    "answer": answer,
                    "evaluation": eval_result
                })
                update_candidate(candidate_id, {"ai_answers": answers})
                write_audit(candidate_id, "EVALUATOR", "answer_evaluated", {"round": round_num, "overall": eval_result.get("overall")})

        except Exception as e:
            print(f"[API] Could not persist eval for {candidate_id}: {e}")

        print(f"[API] Eval result for {candidate_id} round {round_num}: {eval_result}")
        return {"success": True, "result": eval_result}

    except Exception as e:
        print(f"[API] Answer evaluation error: {e}")
        # Non-blocking — return safe default result
        fallback = {"overall": 50, "verdict": "Acceptable"}
        return {"success": True, "result": fallback}

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
        # Persist any answers passed in (frontend may send them)
        parsed_answers = json.loads(answers) if answers else []
        try:
            candidate = get_candidate(candidate_id)
            if candidate is None:
                return {"success": False, "message": "Candidate not found"}

            # Merge frontend-provided answers into stored ai_answers if present
            stored = candidate.get("ai_answers", [])
            if parsed_answers:
                # Append any answers that are not already present (naive append)
                for a in parsed_answers:
                    stored.append({
                        "round": a.get("round"),
                        "question": a.get("question"),
                        "answer": a.get("answer"),
                        "evaluation": a.get("evaluation") if a.get("evaluation") else None
                    })
                update_candidate(candidate_id, {"ai_answers": stored})

            # Compute final ai score from stored evaluations if available
            evals = [s.get("evaluation") for s in stored if s.get("evaluation")]
            ai_score = None
            if evals:
                # Average the 'overall' field across evals
                total = 0.0
                count = 0
                for e in evals:
                    try:
                        val = float(e.get("overall") or e.get("score") or 0)
                    except Exception:
                        val = 0.0
                    total += val
                    count += 1
                if count > 0:
                    ai_score = round(total / count, 1)

            # If no evaluations present, fall back to frontend score
            final_score = ai_score if ai_score is not None else float(score)

            # Update candidate record
            update_candidate(candidate_id, {
                "status": "ai_interview_complete",
                "ai_interview_score": final_score,
                "ai_answers": stored
            })

            write_audit(candidate_id, "EVALUATOR", "interview_completed", {"final_score": final_score})

            # Resume pipeline in background
            from agents.orchestrator.agent import resume_pipeline_after_interview
            import threading
            def resume():
                try:
                    resume_pipeline_after_interview(candidate_id, final_score)
                except Exception as e:
                    print(f"[API] Resume pipeline error: {e}")

            thread = threading.Thread(target=resume)
            thread.daemon = True
            thread.start()

            print(f"[API] Interview complete for {candidate_id}. Final score: {final_score}")
            return {"success": True, "message": "Interview complete. Pipeline resumed.", "final_score": final_score}

        except Exception as e:
            print(f"[API] Error processing complete_ai_interview for {candidate_id}: {e}")
            return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": "Interview recorded with error."}
    
# ── Live Agent Feed ──────────────────────────────────────────────
from shared.agent_feed import get_feed, log_agent

@app.get("/api/agent-feed")
def agent_feed(limit: int = 50):
    return get_feed(limit)

from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# ── Interviewer Scoring ──────────────────────────────────────────

@app.get("/interview/score/{assignment_id}", response_class=HTMLResponse)
def scoring_page(assignment_id: str):
    """Serve the interviewer scoring form."""
    from shared.cosmos_client import get_assignment, get_candidate
    assignment = get_assignment(assignment_id)
    if not assignment:
        return HTMLResponse("<h2>Assignment not found</h2>", status_code=404)

    candidate = get_candidate(assignment.get("candidate_id", ""))
    cand_name = candidate.get("name", "Candidate") if candidate else "Candidate"
    role = candidate.get("applied_role", "") if candidate else ""

    if assignment.get("feedback_submitted"):
        return HTMLResponse(f"""
        <div style="font-family:Segoe UI,sans-serif;max-width:600px;margin:80px auto;text-align:center">
          <div style="font-size:48px">✅</div>
          <h2>Feedback Already Submitted</h2>
          <p style="color:#64748b">Thank you for evaluating {cand_name}. Your feedback has been recorded.</p>
        </div>""")

    return HTMLResponse(_scoring_html(assignment_id, cand_name, role, candidate))


def _scoring_html(assignment_id, name, role, candidate):
    ai_score = candidate.get("ai_interview_score", "N/A") if candidate else "N/A"
    resume_score = candidate.get("resume_score", "N/A") if candidate else "N/A"
    coding_score = candidate.get("coding_score", "N/A") if candidate else "N/A"

    def score_row(label, field):
        opts = "".join(f'<option value="{i}">{i}</option>' for i in range(1, 11))
        return f"""
        <div style="margin-bottom:16px">
          <label style="display:block;font-weight:600;margin-bottom:6px;color:#374151">{label}</label>
          <select name="{field}" required style="width:100%;padding:10px;border:1px solid #e2e8f0;border-radius:8px;font-size:14px">
            <option value="">Select score (1-10)</option>{opts}
          </select>
        </div>"""

    return f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Interview Scorecard — {name}</title></head>
<body style="font-family:Segoe UI,sans-serif;background:#f1f5f9;margin:0;padding:24px">
<div style="max-width:680px;margin:0 auto;background:#fff;border-radius:16px;padding:32px;box-shadow:0 4px 20px rgba(0,0,0,0.08)">
  <h1 style="color:#0f172a;margin:0 0 4px">Interview Scorecard</h1>
  <p style="color:#64748b;margin:0 0 8px">Candidate: <strong>{name}</strong> — {role}</p>
  <div style="background:#eff6ff;border-radius:10px;padding:12px;margin-bottom:24px;font-size:13px;color:#1e40af">
    AI Pre-Screening → Resume: {resume_score}/100 · AI Interview: {ai_score}/100 · Coding: {coding_score}/100<br>
    <em>Focus your scoring on areas the AI could not assess.</em>
  </div>

  <form id="f" onsubmit="submitForm(event)">
    <h3 style="color:#6366f1;border-bottom:2px solid #eff6ff;padding-bottom:6px">Technical Assessment</h3>
    {score_row("Technical Depth", "tech_depth")}
    {score_row("Problem Solving", "problem_solving")}
    {score_row("System Design", "system_design")}

    <h3 style="color:#6366f1;border-bottom:2px solid #eff6ff;padding-bottom:6px">Soft Skills</h3>
    {score_row("Communication", "communication")}
    {score_row("Collaboration", "collaboration")}

    <h3 style="color:#6366f1;border-bottom:2px solid #eff6ff;padding-bottom:6px">Cultural Fit</h3>
    {score_row("Values Alignment", "culture_fit")}
    {score_row("Growth Mindset", "growth_mindset")}

    <h3 style="color:#6366f1;border-bottom:2px solid #eff6ff;padding-bottom:6px">Feedback</h3>
    <div style="margin-bottom:16px">
      <label style="display:block;font-weight:600;margin-bottom:6px;color:#374151">Key Strengths</label>
      <textarea name="strengths" rows="3" style="width:100%;padding:10px;border:1px solid #e2e8f0;border-radius:8px;box-sizing:border-box"></textarea>
    </div>
    <div style="margin-bottom:16px">
      <label style="display:block;font-weight:600;margin-bottom:6px;color:#374151">Areas of Concern</label>
      <textarea name="concerns" rows="3" style="width:100%;padding:10px;border:1px solid #e2e8f0;border-radius:8px;box-sizing:border-box"></textarea>
    </div>

    <h3 style="color:#6366f1;border-bottom:2px solid #eff6ff;padding-bottom:6px">Recommendation</h3>
    <div style="margin-bottom:16px">
      <select name="recommendation" required style="width:100%;padding:10px;border:1px solid #e2e8f0;border-radius:8px;font-size:14px">
        <option value="">Select recommendation</option>
        <option value="strong_hire">Strong Hire</option>
        <option value="hire">Hire</option>
        <option value="maybe">Maybe</option>
        <option value="no_hire">No Hire</option>
        <option value="strong_no_hire">Strong No Hire</option>
      </select>
    </div>


    <button type="submit" style="width:100%;padding:14px;background:linear-gradient(135deg,#6366f1,#7c3aed);color:#fff;border:none;border-radius:10px;font-size:16px;font-weight:700;cursor:pointer">
      Submit Evaluation
    </button>
  </form>
  <div id="msg" style="display:none;text-align:center;padding:40px">
    <div style="font-size:48px">✅</div>
    <h2 style="color:#16a34a">Evaluation Submitted!</h2>
    <p style="color:#64748b">Thank you. The hiring manager has been notified.</p>
  </div>
</div>
<script>
async function submitForm(e) {{
  e.preventDefault();
  const form = document.getElementById('f');
  const data = {{ assignment_id: "{assignment_id}" }};
  new FormData(form).forEach((v,k) => data[k] = v);
  try {{
    const r = await fetch('/api/interview/submit-score', {{
      method: 'POST', headers: {{'Content-Type':'application/json'}},
      body: JSON.stringify(data)
    }});
    if (r.ok) {{ form.style.display='none'; document.getElementById('msg').style.display='block'; }}
    else {{ alert('Submission failed. Please try again.'); }}
  }} catch {{ alert('Network error. Please try again.'); }}
}}
</script>
</body></html>"""


class ScoreSubmission(BaseModel):
    assignment_id: str
    tech_depth: int = 5
    problem_solving: int = 5
    system_design: int = 5
    communication: int = 5
    collaboration: int = 5
    culture_fit: int = 5
    growth_mindset: int = 5
    strengths: str = ""
    concerns: str = ""
    recommendation: str = "maybe"
    


@app.post("/api/interview/submit-score")
def submit_score(sub: ScoreSubmission):
    """Receive interviewer scores, generate combined report, email HR."""
    from shared.cosmos_client import (get_assignment, update_assignment,
        get_candidate, update_candidate, get_job, get_hr_user)
    from agents.communicator.agent import send_email
    from shared.agent_feed import log_agent

    assignment = get_assignment(sub.assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    candidate_id = assignment.get("candidate_id", "")
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Compute human score (average of all dims × 10 → 0-100 scale)
    dims = [sub.tech_depth, sub.problem_solving, sub.system_design,
            sub.communication, sub.collaboration, sub.culture_fit, sub.growth_mindset]
    human_score = round(sum(dims) / len(dims) * 10, 1)

    # Combined AI score (already computed earlier in pipeline)
    ai_combined = candidate.get("combined_ai_score") or candidate.get("ai_interview_score", 0)

    # Final = AI 60% + Human 40%
    final_score = round((ai_combined * 0.6) + (human_score * 0.4), 1)

    rec_pass = sub.recommendation in ("strong_hire", "hire")

    update_candidate(candidate_id, {
        "human_score": human_score,
        "human_tech_score": sub.tech_depth,
        "human_scorecard": sub.dict(),
        "human_recommendation": sub.recommendation,
        "combined_final_score": final_score,
        "status": "technical_complete_pending_hr"
    })
    update_assignment(sub.assignment_id, {
        "feedback_submitted": True,
        "status": "completed"
    })

    log_agent("EVALUATOR", "human_feedback",
              f"Human: {human_score}/100 | Final: {final_score}/100 | {sub.recommendation}",
              candidate_id)

    # Email combined report to HR who posted the JD
    _email_combined_report(candidate, candidate_id, human_score, ai_combined,
                           final_score, sub, rec_pass)

    return {"success": True, "final_score": final_score}


def _email_combined_report(candidate, candidate_id, human_score, ai_combined,
                           final_score, sub, rec_pass):
    from shared.cosmos_client import get_hr_user
    from agents.communicator.agent import send_email

    hr_id = candidate.get("hr_id", "")
    hr = get_hr_user(hr_id) if hr_id else None
    hr_email = hr.get("email") if hr else "jefrijebason@gmail.com"
    hr_name = hr.get("name", "Hiring Manager") if hr else "Hiring Manager"

    base = getattr(config, "PUBLIC_URL", "http://localhost:8000")
    approve_url = f"{base}/api/hr/approve/{candidate_id}"
    decision_url = f"{base}/hr/decision/{candidate_id}"
    reject_url = f"{base}/api/hr/reject/{candidate_id}"

    rec_label = sub.recommendation.replace("_", " ").title()
    rec_color = "#16a34a" if rec_pass else "#dc2626"

    send_email(
        to_address=hr_email,
        subject=f"Evaluation Report: {candidate.get('name')} — {rec_label}",
        body_html=f"""
<div style="font-family:Segoe UI,sans-serif;max-width:600px">
<h2>Candidate Evaluation Report</h2>
<p>Hi {hr_name},</p>
<p>The technical interview for <strong>{candidate.get('name')}</strong>
({candidate.get('applied_role','')}) is complete.</p>

<table style="border-collapse:collapse;width:100%;margin:16px 0">
<tr style="background:#eff6ff"><td style="padding:10px;font-weight:bold">AI Score (Resume + Interview + Coding)</td>
<td style="padding:10px">{ai_combined:.1f}/100</td></tr>
<tr><td style="padding:10px;font-weight:bold">Human Score (Interviewer)</td>
<td style="padding:10px">{human_score}/100</td></tr>
<tr style="background:#f0fdf4"><td style="padding:10px;font-weight:bold">FINAL (AI 60% + Human 40%)</td>
<td style="padding:10px;font-size:18px;font-weight:bold">{final_score}/100</td></tr>
<tr><td style="padding:10px;font-weight:bold">Recommendation</td>
<td style="padding:10px;color:{rec_color};font-weight:bold">{rec_label}</td></tr>
<tr style="background:#eff6ff"><td style="padding:10px;font-weight:bold">Suggested Salary</td>
<td style="padding:10px">{sub.suggested_salary or 'Not specified'} LPA</td></tr>
</table>

<p><strong>Strengths:</strong> {sub.strengths or 'None noted'}</p>
<p><strong>Concerns:</strong> {sub.concerns or 'None noted'}</p>

<div style="margin:24px 0">
<a href="{approve_url}" style="display:inline-block;background:#16a34a;color:#fff;
padding:12px 28px;text-decoration:none;border-radius:8px;font-weight:bold;margin-right:10px">
✓ Approve & Schedule HR Round</a>

<a href="{reject_url}" style="display:inline-block;background:#dc2626;color:#fff;
padding:12px 28px;text-decoration:none;border-radius:8px;font-weight:bold">
✗ Reject</a>
</div>

<p style="color:#94a3b8;font-size:12px">HR decision required to proceed.</p>
</div>
""")


@app.get("/api/hr/approve/{candidate_id}", response_class=HTMLResponse)
def hr_approve(candidate_id: str):
    """HR approves → schedule HR round → notify candidate."""
    from shared.cosmos_client import get_candidate, update_candidate
    from agents.scheduler.agent import run_scheduler
    from shared.agent_feed import log_agent

    candidate = get_candidate(candidate_id)
    if not candidate:
        return HTMLResponse("<h2>Candidate not found</h2>", status_code=404)

    update_candidate(candidate_id, {"status": "waiting_hr_interview"})
    log_agent("ORCHESTRATOR", "hr_approved", "HR approved — scheduling HR round", candidate_id)

    try:
        run_scheduler(candidate_id, "hr", send_candidate_email=True)
    except Exception as e:
        print(f"[HR APPROVE] Scheduler error: {e}")

    return HTMLResponse(f"""
    <div style="font-family:Segoe UI,sans-serif;max-width:600px;margin:80px auto;text-align:center">
      <div style="font-size:48px">✅</div>
      <h2 style="color:#16a34a">HR Round Scheduled</h2>
      <p style="color:#64748b">{candidate.get('name')} has been notified with the HR round details and meeting link.</p>
    </div>""")


@app.get("/api/hr/reject/{candidate_id}", response_class=HTMLResponse)
def hr_reject(candidate_id: str):
    """HR rejects → growth report to candidate."""
    from shared.cosmos_client import get_candidate, update_candidate
    from agents.orchestrator.agent import _send_rejection_with_growth
    from shared.agent_feed import log_agent

    candidate = get_candidate(candidate_id)
    if not candidate:
        return HTMLResponse("<h2>Candidate not found</h2>", status_code=404)

    update_candidate(candidate_id, {"status": "rejected"})
    log_agent("ORCHESTRATOR", "hr_rejected", "HR rejected after technical review", candidate_id)

    try:
        _send_rejection_with_growth(candidate_id)
    except Exception as e:
        print(f"[HR REJECT] error: {e}")

    return HTMLResponse(f"""
    <div style="font-family:Segoe UI,sans-serif;max-width:600px;margin:80px auto;text-align:center">
      <div style="font-size:48px">📋</div>
      <h2>Candidate Notified</h2>
      <p style="color:#64748b">{candidate.get('name')} has been sent a respectful rejection with a growth report.</p>
    </div>""")
# ── HR Decision Form ─────────────────────────────────────────────

@app.get("/hr/decision/{candidate_id}", response_class=HTMLResponse)
def hr_decision_form(candidate_id: str):
    from shared.cosmos_client import get_candidate
    candidate = get_candidate(candidate_id)
    if not candidate:
        return HTMLResponse("<h2>Candidate not found</h2>", status_code=404)

    if candidate.get("hr_decision_submitted"):
        return HTMLResponse(f"""
        <div style="font-family:Segoe UI,sans-serif;max-width:600px;
          margin:80px auto;text-align:center">
          <div style="font-size:48px">✅</div>
          <h2>Decision Already Submitted</h2>
          <p style="color:#64748b">A decision has already been recorded
          for {candidate.get('name')}.</p>
        </div>""")

    name = candidate.get("name", "")
    role = candidate.get("applied_role", "")
    resume_score = candidate.get("resume_score", "N/A")
    ai_score = candidate.get("ai_interview_score", "N/A")
    coding_score = candidate.get("coding_score", "N/A")
    human_score = candidate.get("human_score", "N/A")
    final_score = candidate.get("combined_final_score", "N/A")
    expected_ctc = candidate.get("expected_ctc", "")

    return HTMLResponse(f"""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HR Decision — {name}</title></head>
<body style="font-family:Segoe UI,sans-serif;background:#f1f5f9;
  margin:0;padding:24px">
<div style="max-width:680px;margin:0 auto;background:#fff;
  border-radius:16px;padding:32px;
  box-shadow:0 4px 20px rgba(0,0,0,0.08)">

  <h1 style="color:#0f172a;margin:0 0 4px">HR Decision Form</h1>
  <p style="color:#64748b;margin:0 0 20px">
    Candidate: <strong>{name}</strong> — {role}
  </p>

  <!-- Score Summary -->
  <div style="background:#eff6ff;border-radius:10px;
    padding:16px;margin-bottom:24px">
    <div style="font-weight:700;color:#1e40af;margin-bottom:10px">
      Complete Evaluation Summary
    </div>
    <div style="display:grid;grid-template-columns:repeat(5,1fr);
      gap:8px;text-align:center">
      {_score_box("Resume", resume_score)}
      {_score_box("AI Interview", ai_score)}
      {_score_box("Coding", coding_score)}
      {_score_box("Technical", human_score)}
      {_score_box("FINAL", final_score, highlight=True)}
    </div>
  </div>

  <!-- Decision Selector -->
  <div style="margin-bottom:24px">
    <label style="display:block;font-weight:700;font-size:16px;
      margin-bottom:12px;color:#0f172a">Select Decision</label>
    <div style="display:flex;gap:10px;flex-wrap:wrap">
      {_decision_btn("offer", "✅ Send Offer Letter", "#16a34a")}
      {_decision_btn("decline", "❌ Decline Candidate", "#dc2626")}
      {_decision_btn("talent_pool", "⭐ Add to Talent Pool", "#d97706")}
    </div>
  </div>

  <!-- Offer Letter Section -->
  <div id="offer_section" style="display:none;background:#f0fdf4;
    border:1px solid #86efac;border-radius:12px;padding:20px;
    margin-bottom:20px">
    <h3 style="color:#15803d;margin:0 0 16px">Offer Letter Details</h3>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div>
        <label style="display:block;font-weight:600;font-size:13px;
          margin-bottom:6px;color:#374151">Offered Salary (LPA)</label>
        <input id="salary" placeholder="e.g. 22"
          value="{expected_ctc}"
          style="width:100%;padding:10px;border:1px solid #e2e8f0;
          border-radius:8px;box-sizing:border-box">
      </div>
      <div>
        <label style="display:block;font-weight:600;font-size:13px;
          margin-bottom:6px;color:#374151">Start Date</label>
        <input id="start_date" type="date"
          style="width:100%;padding:10px;border:1px solid #e2e8f0;
          border-radius:8px;box-sizing:border-box">
      </div>
      <div>
        <label style="display:block;font-weight:600;font-size:13px;
          margin-bottom:6px;color:#374151">Role / Title</label>
        <input id="role_title" value="{role}"
          style="width:100%;padding:10px;border:1px solid #e2e8f0;
          border-radius:8px;box-sizing:border-box">
      </div>
      <div>
        <label style="display:block;font-weight:600;font-size:13px;
          margin-bottom:6px;color:#374151">Work Mode</label>
        <select id="work_mode" style="width:100%;padding:10px;
          border:1px solid #e2e8f0;border-radius:8px">
          <option>Hybrid</option>
          <option>Remote</option>
          <option>On-site</option>
        </select>
      </div>
      <div style="grid-column:1/-1">
        <label style="display:block;font-weight:600;font-size:13px;
          margin-bottom:6px;color:#374151">
          Additional Benefits / Notes
        </label>
        <textarea id="benefits" rows="3"
          placeholder="Health insurance, 25 days leave, etc."
          style="width:100%;padding:10px;border:1px solid #e2e8f0;
          border-radius:8px;box-sizing:border-box;resize:vertical">
        </textarea>
      </div>
    </div>
  </div>

  <!-- Decline / Talent Pool Notes -->
  <div id="notes_section" style="display:none;margin-bottom:20px">
    <label style="display:block;font-weight:600;font-size:13px;
      margin-bottom:6px;color:#374151">Notes (optional)</label>
    <textarea id="notes" rows="3"
      placeholder="Reason or message for the candidate..."
      style="width:100%;padding:10px;border:1px solid #e2e8f0;
      border-radius:8px;box-sizing:border-box;resize:vertical">
    </textarea>
  </div>

  <button id="submit_btn" onclick="submitDecision()"
    style="display:none;width:100%;padding:14px;
    background:linear-gradient(135deg,#6366f1,#7c3aed);
    color:#fff;border:none;border-radius:10px;font-size:16px;
    font-weight:700;cursor:pointer">
    Confirm Decision →
  </button>

  <div id="msg" style="display:none;text-align:center;padding:40px">
    <div style="font-size:48px">✅</div>
    <h2 style="color:#16a34a">Decision Submitted!</h2>
    <p style="color:#64748b">Candidate has been notified.</p>
  </div>
</div>

<script>
let selectedDecision = '';

function selectDecision(d) {{
  selectedDecision = d;
  document.querySelectorAll('.dec-btn').forEach(b => {{
    b.style.opacity = '0.5';
    b.style.transform = 'scale(0.98)';
  }});
  document.getElementById('btn_' + d).style.opacity = '1';
  document.getElementById('btn_' + d).style.transform = 'scale(1.02)';
  document.getElementById('offer_section').style.display =
    d === 'offer' ? 'block' : 'none';
  document.getElementById('notes_section').style.display =
    d !== 'offer' ? 'block' : 'none';
  document.getElementById('submit_btn').style.display = 'block';
  const colors = {{
    offer: 'linear-gradient(135deg,#16a34a,#15803d)',
    decline: 'linear-gradient(135deg,#dc2626,#b91c1c)',
    talent_pool: 'linear-gradient(135deg,#d97706,#b45309)'
  }};
  document.getElementById('submit_btn').style.background =
    colors[d];
}}

async function submitDecision() {{
  if (!selectedDecision) {{ alert('Please select a decision'); return; }}
  const payload = {{
    candidate_id: "{candidate_id}",
    decision: selectedDecision,
    salary: document.getElementById('salary')?.value || '',
    start_date: document.getElementById('start_date')?.value || '',
    role_title: document.getElementById('role_title')?.value || '',
    work_mode: document.getElementById('work_mode')?.value || '',
    benefits: document.getElementById('benefits')?.value || '',
    notes: document.getElementById('notes')?.value || ''
  }};
  try {{
    const r = await fetch('/api/hr/decision/submit', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(payload)
    }});
    if (r.ok) {{
      document.querySelector('form') &&
        (document.querySelector('form').style.display = 'none');
      document.getElementById('msg').style.display = 'block';
      document.getElementById('submit_btn').style.display = 'none';
    }} else {{ alert('Submission failed. Try again.'); }}
  }} catch {{ alert('Network error. Try again.'); }}
}}
</script>
</body></html>""")


def _score_box(label, val, highlight=False):
    bg = "#4f46e5" if highlight else "#fff"
    color = "#fff" if highlight else "#1e40af"
    return f"""<div style="background:{bg};border-radius:8px;
      padding:10px;border:1px solid #bfdbfe">
      <div style="font-size:18px;font-weight:800;color:{color}">
        {val}
      </div>
      <div style="font-size:10px;color:{'#c7d2fe' if highlight else '#64748b'}">
        {label}
      </div>
    </div>"""


def _decision_btn(key, label, color):
    return f"""<button id="btn_{key}" class="dec-btn"
      onclick="selectDecision('{key}')"
      style="flex:1;min-width:160px;padding:12px 16px;
      border:2px solid {color};border-radius:10px;
      background:transparent;color:{color};
      font-weight:700;font-size:14px;cursor:pointer;
      transition:all 0.2s">
      {label}
    </button>"""


class HRDecisionRequest(BaseModel):
    candidate_id: str
    decision: str
    salary: str = ""
    start_date: str = ""
    role_title: str = ""
    work_mode: str = ""
    benefits: str = ""
    notes: str = ""


@app.post("/api/hr/decision/submit")
def hr_decision_submit(req: HRDecisionRequest):
    from shared.cosmos_client import get_candidate, update_candidate
    from agents.communicator.agent import send_email
    from shared.agent_feed import log_agent

    candidate = get_candidate(req.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    name = candidate.get("name", "")
    role = candidate.get("applied_role", "")
    email = candidate.get("email", "")

    update_candidate(req.candidate_id, {
        "hr_decision": req.decision,
        "hr_decision_submitted": True,
        "agreed_salary": req.salary,
        "status": "hired" if req.decision == "offer"
                  else "rejected" if req.decision == "decline"
                  else "talent_pool"
    })

    log_agent("ORCHESTRATOR", f"hr_decision_{req.decision}",
              f"{name} — {req.decision}", req.candidate_id)

    if req.decision == "offer":
        _send_offer_letter(candidate, req)
    elif req.decision == "decline":
        from agents.orchestrator.agent import _send_rejection_with_growth
        _send_rejection_with_growth(req.candidate_id)
    else:  # talent_pool
        _send_talent_pool_email(candidate, req.notes)

    return {"success": True, "decision": req.decision}


def _send_offer_letter(candidate: dict, req: HRDecisionRequest):
    from agents.communicator.agent import send_email
    send_email(
        to_address=candidate.get("email"),
        subject=f"🎉 Offer Letter — {req.role_title}",
        body_html=f"""
<div style="font-family:Segoe UI,sans-serif;max-width:600px;
  border:2px solid #6366f1;border-radius:16px;padding:32px">
  <div style="text-align:center;margin-bottom:24px">
    <div style="font-size:48px">🎉</div>
    <h1 style="color:#4f46e5;margin:8px 0">Congratulations!</h1>
    <p style="color:#64748b">We are delighted to offer you a position.</p>
  </div>

  <h2 style="color:#0f172a;border-bottom:2px solid #eff6ff;
    padding-bottom:8px">Official Offer Letter</h2>

  <p>Dear <strong>{candidate.get('name')}</strong>,</p>
  <p>After a thorough evaluation process, we are pleased to extend
  this formal offer of employment.</p>

  <table style="border-collapse:collapse;width:100%;margin:20px 0">
    <tr style="background:#eff6ff">
      <td style="padding:12px;font-weight:bold">Position</td>
      <td style="padding:12px">{req.role_title}</td>
    </tr>
    <tr>
      <td style="padding:12px;font-weight:bold">Salary</td>
      <td style="padding:12px;font-size:18px;
        color:#16a34a;font-weight:bold">
        ₹{req.salary} LPA
      </td>
    </tr>
    <tr style="background:#eff6ff">
      <td style="padding:12px;font-weight:bold">Start Date</td>
      <td style="padding:12px">{req.start_date or 'To be confirmed'}</td>
    </tr>
    <tr>
      <td style="padding:12px;font-weight:bold">Work Mode</td>
      <td style="padding:12px">{req.work_mode}</td>
    </tr>
    <tr style="background:#eff6ff">
      <td style="padding:12px;font-weight:bold">Benefits</td>
      <td style="padding:12px">{req.benefits or 'Standard package'}</td>
    </tr>
  </table>

  <div style="background:#f0fdf4;border:1px solid #86efac;
    border-radius:10px;padding:16px;margin:20px 0">
    <p style="color:#15803d;font-weight:600;margin:0 0 8px">
      Next Steps:
    </p>
    <ol style="color:#166534;margin:0;padding-left:20px">
      <li>Reply to this email to accept the offer</li>
      <li>Complete the onboarding form (link to follow)</li>
      <li>We will send your joining kit 3 days before start date</li>
    </ol>
  </div>

  <p>Please respond within <strong>5 business days</strong>.
  We look forward to having you on the team!</p>

  <p>Warm regards,<br><strong>HR Team</strong></p>
</div>
""")


def _send_talent_pool_email(candidate: dict, notes: str = ""):
    from agents.communicator.agent import send_email
    from shared.cosmos_client import add_to_talent_pool
    add_to_talent_pool(candidate)
    send_email(
        to_address=candidate.get("email"),
        subject=f"Your Application — {candidate.get('applied_role', '')}",
        body_html=f"""
<div style="font-family:Segoe UI,sans-serif;max-width:600px">
  <h2>Thank You, {candidate.get('name')}</h2>
  <p>While we are not moving forward with your application for
  <strong>{candidate.get('applied_role', '')}</strong> at this time,
  we were genuinely impressed by your profile.</p>
  <p>We have added you to our <strong>Priority Talent Pool</strong>.
  You will be among the first we contact when a matching role opens.</p>
  <p>{notes}</p>
  <p>Thank you for the time you invested in our process.</p>
  <p>Best regards,<br>HR Team</p>
</div>
""")

# ── Run Server ───────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )