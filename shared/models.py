from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# ── Candidate Model ─────────────────────────────────────────────
class Candidate(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    applied_role: str
    job_id: Optional[str] = None
    resume_blob_url: str = ""
    resume_text: str = ""
    status: str = "applied"
    created_at: str = datetime.utcnow().isoformat()
    profile_type: Optional[str] = None

    # AI Scores
    resume_score:        Optional[float] = None
    coding_score:        Optional[float] = None
    malpractice_score:   Optional[float] = None
    malpractice_flagged: bool = False
    ai_interview_score:  Optional[float] = None
    final_score:         Optional[float] = None
    confidence:          Optional[float] = None

    # Human Round Scores (supports N rounds)
    human_round_scores: List[Dict] = []
    human_tech_score:   Optional[float] = None
    human_culture_score: Optional[float] = None
    agreed_salary:       Optional[str] = None

    # Extracted info
    skills:           List[str] = []
    experience_years: Optional[int] = None
    expected_ctc:     Optional[str] = None

    # Analysis
    ai_profile:   Optional[Dict] = None
    ai_analysis:  Optional[Dict] = None
    round_scores: Optional[Dict] = None

    # Scheduling
    interview_slots:    List[Dict] = []
    human_briefing:     Optional[Dict] = None
    hr_briefing:        Optional[Dict] = None

    # Decision
    decision:         Optional[str] = None
    decision_reasons: List[str] = []
    human_notes:      Optional[str] = None

    # Flags
    email_sent:          bool = False
    growth_report_sent:  bool = False
    added_to_talent_pool: bool = False

# ── Human Round Configuration ───────────────────────────────────
class HumanRound(BaseModel):
    round_number:    int
    round_name:      str
    interviewer_name: str
    interviewer_email: str
    duration_minutes: int = 60
    focus:           str = ""
    instructions:    str = ""
    is_required:     bool = True
    position:        int = 1  # Order in pipeline

# ── Job Configuration Model ─────────────────────────────────────
class JobConfig(BaseModel):
    id: str
    title: str
    department: str = ""
    jd_text: str = ""
    created_at: str = datetime.utcnow().isoformat()
    status: str = "active"

    # Interview Mode
    interview_mode: str = "standard"
    # standard / executive / express / custom

    # Round Toggles
    coding_round_enabled:    bool = True
    ai_interview_enabled:    bool = True

    # Human Rounds (flexible N rounds in any order)
    human_rounds: List[HumanRound] = []

    # Seniority Rules
    skip_ai_above_level:     str = ""
    require_approval_above:  str = ""

    # TalentBlitz Config
    is_talentblitz:          bool = False
    talentblitz_config:      Optional[Dict] = None

    # JD Analysis Results
    jd_quality_score:        Optional[float] = None
    jd_issues:               List[Dict] = []
    role_category:           Optional[str] = None
    role_seniority:          Optional[str] = None
    tech_stack:              List[str] = []

    # Scoring Thresholds
    screening_threshold:     float = 60.0
    human_interview_threshold: float = 70.0
    hire_threshold:          float = 65.0

    # Salary
    salary_min:  str = ""
    salary_max:  str = ""
    location:    str = ""
    team_size:   int = 0

# ── TalentBlitz Event Model ─────────────────────────────────────
class TalentBlitzEvent(BaseModel):
    id: str
    job_id: str
    event_name: str
    event_date: str
    venue: str = "Online"
    mode: str = "online"
    # online / hybrid / kiosk

    target_hires:    int = 0
    expected_apps:   int = 0
    max_concurrent:  int = 100

    registration_open:  str = ""
    registration_close: str = ""
    assessment_open:    str = ""
    assessment_close:   str = ""

    show_leaderboard:   bool = False
    status:             str = "draft"
    # draft / active / completed

    candidates_registered: int = 0
    candidates_processed:  int = 0
    candidates_shortlisted: int = 0

# ── Audit Entry ─────────────────────────────────────────────────
class AuditEntry(BaseModel):
    id: str
    candidate_id: str
    agent: str
    action: str
    data: Dict = {}
    timestamp: str = datetime.utcnow().isoformat()

# ── Talent Pool Entry ───────────────────────────────────────────
class TalentPoolEntry(BaseModel):
    id: str
    candidate_id: str
    name: str
    email: str
    skills: List[str] = []
    score: Optional[float] = None
    role_applied: str = ""
    added_at: str = datetime.utcnow().isoformat()
    contacted_again: bool = False