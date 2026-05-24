import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

def create_pdf(filename: str, content: str):
    doc    = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story  = []

    for line in content.strip().split("\n"):
        if line.strip():
            if line.isupper() and len(line) < 40:
                story.append(Paragraph(
                    line, styles["Heading2"]
                ))
            else:
                story.append(Paragraph(
                    line, styles["Normal"]
                ))
        story.append(Spacer(1, 0.1 * inch))

    doc.build(story)
    print(f"✓ Created: {filename}")

# ── Strong Candidate Resume ──────────────────────────────
strong = """
ARJUN MEHTA
arjun.mehta@email.com | 9876543210 | Bangalore

SUMMARY
Senior AI Engineer with 6 years of experience
building production ML systems on Azure.
Expert in Python, Azure OpenAI, and multi-agent
AI system design.

SKILLS
Python, Azure ML, Azure OpenAI, Azure AI Foundry,
FastAPI, Docker, Kubernetes, PostgreSQL,
Machine Learning, NLP, LangChain, GPT-4,
REST APIs, Git, CI/CD, Terraform, Redis

EXPERIENCE

Senior AI Engineer — TechCorp India (2022-2026)
Built ML pipelines processing 1 million records daily
using Azure ML and Python. Deployed GPT-4 powered
applications on Azure OpenAI. Led team of 5 engineers.
Reduced model inference time by 60 percent through
optimization. Designed multi-agent AI systems for
automated document processing.

AI Engineer — AI Startup (2020-2022)
Built NLP models for text classification achieving
94 percent accuracy. Deployed models using Docker
and Kubernetes. Developed FastAPI backends for ML
model serving. Worked with PostgreSQL and Redis
for data storage and caching.

Software Engineer — IT Company (2018-2020)
Python development and REST API design.
Azure cloud services integration.
Agile development with cross-functional teams.

EDUCATION
M.Tech Artificial Intelligence — IIT Hyderabad (2018)
B.Tech Computer Science — NIT Warangal (2016)

CERTIFICATIONS
Microsoft Azure AI Engineer Associate
Google Professional ML Engineer
AWS Machine Learning Specialty

ACHIEVEMENTS
Published 2 research papers on NLP in IEEE conferences
Reduced hiring costs by 40 percent using AI automation
Led successful migration of ML platform to Azure
Open source contributor to Hugging Face transformers
"""

# ── Borderline Candidate Resume ──────────────────────────
borderline = """
PRIYA SHARMA
priya.sharma@email.com | 9876543211 | Mumbai

SUMMARY
Python developer with 3 years of experience
in web development and basic data analysis.
Looking to transition into AI/ML roles.

SKILLS
Python, Django, Flask, MySQL, JavaScript,
HTML, CSS, Git, Linux, Basic SQL,
Some experience with pandas and numpy

EXPERIENCE

Python Developer — WebTech Solutions (2023-2026)
Built web applications using Django framework.
Worked with MySQL databases for data storage.
Created REST APIs for mobile applications.
Basic data analysis using pandas.

Junior Developer — Digital Agency (2021-2023)
Frontend development using JavaScript and React.
Basic Python scripting for automation tasks.
Maintained existing web applications.

EDUCATION
B.Tech Information Technology — Mumbai University (2021)

ACHIEVEMENTS
Built internal tool that saved 2 hours per week
Learned basic machine learning from online courses
Completed Python for Data Science course on Coursera
"""

# ── Reject Candidate Resume ───────────────────────────────
reject = """
RAVI KUMAR
ravi.kumar@email.com | 9876543212 | Delhi

SUMMARY
Experienced accountant with 8 years in financial
reporting and tax compliance. Strong Excel skills
and attention to detail. Looking for new opportunities.

SKILLS
Microsoft Excel, Tally ERP, SAP Finance,
Financial Reporting, Tax Compliance,
GST Filing, Accounts Payable, Accounts Receivable,
MS Office, Basic Computer Skills

EXPERIENCE

Senior Accountant — Manufacturing Company (2020-2026)
Managed monthly financial reporting and reconciliation.
Filed GST returns and income tax for the company.
Handled accounts payable and receivable processes.
Coordinated with auditors during annual audit.

Accountant — Trading Company (2018-2020)
Maintained books of accounts using Tally ERP.
Prepared profit and loss statements.
Bank reconciliation and petty cash management.

Junior Accountant — CA Firm (2016-2018)
Assisted in tax filing and audit support.
Data entry and bookkeeping tasks.

EDUCATION
B.Com Accounting — Delhi University (2016)
CA Inter — Institute of Chartered Accountants (2018)

ACHIEVEMENTS
Reduced accounts processing time by 20 percent
Implemented new expense tracking system
Zero errors in 3 years of financial reporting
"""

# Create output directory
os.makedirs("data/synthetic", exist_ok=True)

# Create all 3 PDFs
create_pdf("data/synthetic/strong_resume.pdf",    strong)
create_pdf("data/synthetic/borderline_resume.pdf", borderline)
create_pdf("data/synthetic/reject_resume.pdf",     reject)

print("\n✓ All 3 resumes created in data/synthetic/")
print("Now run: python scripts/generate_candidates.py")