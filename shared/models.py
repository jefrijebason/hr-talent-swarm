from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# ── HR User Model ────────────────────────────────────────────────
class HRUser(BaseModel):
    id:           str
    name:         str
    email:        str
    role:         str = "hr_manager"
    # hr_manager / hr_admin / recruiter
    department:   str = ""
    phone:        Optional[str] = None
    is_active:    bool = True
    created_at:   str = datetime.utcnow().isoformat()
    posted_jobs:  List[str] = []
    # Track which JDs this HR posted

# ── Interviewer Model ────────────────────────────────────────────
class Interviewer(BaseModel):
    id:               str
    name:             str
    email:            str
    role:             str = ""
    department:       str = ""
    seniority:        str = "mid"
    # intern/junior/mid/senior/lead/manager
    status:           str = "pending"
    # pending/active/inactive/busy
    expertise_skills: List[str] = []
    max_per_week:     int = 3
    current_booked:   int = 0
    total_done:       int = 0
    avg_rating:       float = 0.0
    response_rate:    float = 100.0
    avg_response_hrs: float = 0.0
    timezone:         str = "Asia/Kolkata"
    joined_at:        Optional[str] = None
    last_interview:   Optional[str] = None
    skills_updated_at: Optional[str] = None
    satisfaction_score: float = 5.0
    invite_token:     Optional[str] = None
    added_by_hr_id:   Optional[str] = None

# ── Interview Assignment Model ───────────────────────────────────
class InterviewAssignment(BaseModel):
    id:                  str
    candidate_id:        str
    job_id:              str
    hr_id:               str
    # HR who posted this JD
    interview_type:      str = "technical"
    # technical / hr_round
    primary_interviewer_id:  Optional[str] = None
    backup_1_id:             Optional[str] = None
    backup_2_id:             Optional[str] = None
    assigned_to:             Optional[str] = None
    # Currently assigned interviewer id
    status:              str = "pending"
    # pending/invited/accepted/declined/completed/failed
    escalation_level:    int = 0
    # 0=primary, 1=backup1, 2=backup2, 3=hr_alerted
    created_at:          str = datetime.utcnow().isoformat()
    assigned_at:         Optional[str] = None
    response_deadline:   Optional[str] = None
    accepted_at:         Optional[str] = None
    completed_at:        Optional[str] = None
    meeting_url:         Optional[str] = None
    meeting_slot:        Optional[str] = None
    meeting_slot_human:  Optional[str] = None
    hr_alerted:          bool = False
    hr_alerted_at:       Optional[str] = None
    candidate_last_updated: Optional[str] = None
    # Last time candidate was informed of status
    feedback_submitted:  bool = False
    feedback_deadline:   Optional[str] = None
    custom_assignee_email: Optional[str] = None
    custom_assignee_name:  Optional[str] = None
    timeline:            List[Dict] = []
    # Full audit trail of every action

# ── Candidate Model ──────────────────────────────────────────────
class Candidate(BaseModel):
    id:           str
    name:         str
    email:        str
    phone:        Optional[str] = None
    applied_role: str
    job_id:       Optional[str] = None
    hr_id:        Optional[str] = None
    # HR who posted the job
    resume_blob_url:    str = ""
    resume_text:        str = ""
    status:             str = "applied"
    created_at:         str = datetime.utcnow().isoformat()
    profile_type:       Optional[str] = None

    # AI Scores
    resume_score:        Optional[float] = None
    coding_score:        Optional[float] = None
    malpractice_score:   Optional[float] = None
    malpractice_flagged: bool = False
    ai_interview_score:  Optional[float] = None
    final_score:         Optional[float] = None
    confidence:          Optional[float] = None

    # Human Round Scores
    human_round_scores:  List[Dict] = []
    human_tech_score:    Optional[float] = None
    human_culture_score: Optional[float] = None
    agreed_salary:       Optional[str] = None

    # Info
    skills:           List[str] = []
    experience_years: Optional[int] = None
    expected_ctc:     Optional[str] = None

    # Analysis
    ai_profile:   Optional[Dict] = None
    ai_analysis:  Optional[Dict] = None
    round_scores: Optional[Dict] = None

    # Scheduling
    interview_slots:  List[Dict] = []
    human_briefing:   Optional[Dict] = None
    hr_briefing:      Optional[Dict] = None

    # Decision
    decision:         Optional[str] = None
    decision_reasons: List[str] = []
    human_notes:      Optional[str] = None

    # Flags
    email_sent:           bool = False
    growth_report_sent:   bool = False
    added_to_talent_pool: bool = False

    # SLA Tracking
    sla_deadline:         Optional[str] = None
    sla_breached:         bool = False
    last_candidate_update: Optional[str] = None

# ── Job Config Model ─────────────────────────────────────────────
class JobConfig(BaseModel):
    id:             str
    title:          str
    department:     str = ""
    jd_text:        str = ""
    posted_by_hr_id: str = ""
    # HR who posted this job
    posted_by_hr_name:  str = ""
    posted_by_hr_email: str = ""
    created_at:     str = datetime.utcnow().isoformat()
    status:         str = "active"

    interview_mode:          str = "standard"
    coding_round_enabled:    bool = True
    ai_interview_enabled:    bool = True
    human_rounds:            List[Dict] = []

    # SLA config per job
    primary_response_hrs:    int = 2
    # How long to wait for primary
    escalation_response_hrs: int = 2
    # How long to wait for each backup
    hr_alert_hrs:            int = 5
    # When to alert HR

    seniority_skip_ai:       str = ""
    require_approval_above:  str = ""
    is_talentblitz:          bool = False
    talentblitz_config:      Optional[Dict] = None

    jd_quality_score:        Optional[float] = None
    jd_issues:               List[Dict] = []
    role_category:           Optional[str] = None
    role_seniority:          Optional[str] = None
    tech_stack:              List[str] = []

    screening_threshold:     float = 60.0
    human_interview_threshold: float = 70.0
    hire_threshold:          float = 65.0

    salary_min:  str = ""
    salary_max:  str = ""
    location:    str = ""
    team_size:   int = 0

# ── Human Round Config ───────────────────────────────────────────
class HumanRound(BaseModel):
    round_number:      int
    round_name:        str
    interviewer_name:  str
    interviewer_email: str
    duration_minutes:  int = 60
    focus:             str = ""
    instructions:      str = ""
    is_required:       bool = True
    position:          int = 1

# ── TalentBlitz Event ────────────────────────────────────────────
class TalentBlitzEvent(BaseModel):
    id:           str
    job_id:       str
    event_name:   str
    event_date:   str
    venue:        str = "Online"
    mode:         str = "online"
    target_hires:    int = 0
    expected_apps:   int = 0
    max_concurrent:  int = 100
    registration_open:  str = ""
    registration_close: str = ""
    assessment_open:    str = ""
    assessment_close:   str = ""
    show_leaderboard:   bool = False
    status:             str = "draft"
    candidates_registered:  int = 0
    candidates_processed:   int = 0
    candidates_shortlisted: int = 0

# ── Audit Entry ──────────────────────────────────────────────────
class AuditEntry(BaseModel):
    id:           str
    candidate_id: str
    agent:        str
    action:       str
    data:         Dict = {}
    timestamp:    str = datetime.utcnow().isoformat()

# ── Talent Pool Entry ────────────────────────────────────────────
class TalentPoolEntry(BaseModel):
    id:           str
    candidate_id: str
    name:         str
    email:        str
    skills:       List[str] = []
    score:        Optional[float] = None
    role_applied: str = ""
    added_at:     str = datetime.utcnow().isoformat()
    contacted_again: bool = False