from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Candidate(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    applied_role: str
    resume_blob_url: str = ""
    resume_text: str = ""
    status: str = "applied"
    created_at: str = datetime.utcnow().isoformat()

    # Scores
    resume_score:        Optional[float] = None
    coding_score:        Optional[float] = None
    ai_interview_score:  Optional[float] = None
    human_tech_score:    Optional[float] = None
    human_culture_score: Optional[float] = None
    final_score:         Optional[float] = None
    confidence:          Optional[float] = None

    # Extracted info
    skills:           List[str] = []
    experience_years: Optional[int] = None
    expected_ctc:     Optional[str] = None

    # Human round
    interview_slot:        Optional[str] = None
    interview_meeting_url: Optional[str] = None
    human_notes:           Optional[str] = None
    agreed_salary:         Optional[str] = None

    # Decision
    decision:         Optional[str] = None
    decision_reasons: List[str] = []

class Job(BaseModel):
    id: str
    title: str
    department: str = ""
    required_skills: List[str] = []
    experience_years: int = 0
    budget_min: str = ""
    budget_max: str = ""
    status: str = "active"
    created_at: str = datetime.utcnow().isoformat()