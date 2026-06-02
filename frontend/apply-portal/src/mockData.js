export const MOCK_JOBS = [
  {
    id: 'job-1',
    title: 'Senior AI Engineer',
    department: 'Engineering',
    location: 'Bangalore (Hybrid)',
    salary_min: '18', salary_max: '24',
    experience_required: '3-5 years',
    employment_type: 'Full-time',
    work_mode: 'Hybrid',
    interview_mode: 'standard',
    role_category: 'AI / ML',
    posted_days_ago: 2,
    tech_stack: ['Python', 'Azure', 'ML', 'FastAPI', 'Docker', 'LangChain'],
    company_about: 'We are a fast-growing AI company building intelligent automation tools used by 200+ enterprises worldwide. Our mission is to make AI accessible, fair, and genuinely useful.',
    team_name: 'AI Platform Team',
    team_size: '8 engineers',
    reports_to: 'Head of AI',
    why_work_here: [
      'Work on cutting-edge multi-agent AI systems',
      'Flexible hybrid working with 2 days in office',
      'Annual learning budget of ₹1,00,000',
      'ESOP for all senior engineers',
    ],
    benefits: ['Health Insurance', 'ESOP', 'Flexible Hours', 'Learning Budget', 'Remote Friendly', 'Annual Retreat'],
    hiring_timeline: [
      { stage: 'Resume Screening', time: 'Within 1 hour' },
      { stage: 'AI Interview', time: 'Within 24 hours' },
      { stage: 'Technical Round', time: '2-3 days' },
      { stage: 'Final Decision', time: 'Within 5 days' },
    ],
    jd_text: `We are looking for a Senior AI Engineer to join our AI Platform Team.

You will design and build production-grade AI agent systems that power our enterprise products. This is a hands-on role with significant ownership and the chance to shape our AI architecture.

Responsibilities:
- Design and build multi-agent AI systems
- Deploy and optimize ML models in production
- Collaborate with product to define AI features
- Mentor junior engineers on best practices

Requirements:
- 3-5 years of Python experience
- Strong experience with Azure AI services
- Production ML systems experience
- Understanding of LLMs and agent frameworks
- Excellent problem-solving skills`,
    screening_questions: [
      { question: 'Are you authorized to work in India?', type: 'yesno', knockout: true, knockout_answer: 'No' },
      { question: 'What is your notice period?', type: 'text', knockout: false },
    ],
  },
  {
    id: 'job-2',
    title: 'Data Scientist',
    department: 'Data Platform',
    location: 'Mumbai (Remote)',
    salary_min: '15', salary_max: '22',
    experience_required: '2-4 years',
    employment_type: 'Full-time',
    work_mode: 'Remote',
    interview_mode: 'standard',
    role_category: 'Data',
    posted_days_ago: 5,
    tech_stack: ['Python', 'SQL', 'TensorFlow', 'Statistics', 'Pandas'],
    company_about: 'A data-first organization helping businesses make smarter decisions through analytics and machine learning.',
    team_name: 'Data Science Guild',
    team_size: '12 members',
    reports_to: 'Director of Data',
    why_work_here: [
      'Fully remote with quarterly meetups',
      'Work with petabyte-scale datasets',
      'Top-tier compute resources',
    ],
    benefits: ['Health Insurance', 'Remote First', 'Flexible Hours', 'Learning Budget'],
    hiring_timeline: [
      { stage: 'Resume Screening', time: 'Within 2 hours' },
      { stage: 'AI Interview', time: 'Within 24 hours' },
      { stage: 'Technical Round', time: '2-3 days' },
      { stage: 'Final Decision', time: 'Within 4 days' },
    ],
    jd_text: `Join our Data Science Guild to build models that drive real business impact.

You will work on forecasting, recommendation systems, and experimentation across our product suite.

Requirements:
- 2-4 years in data science
- Strong Python and SQL
- Experience with ML frameworks
- Solid statistics foundation`,
    screening_questions: [],
  },
  {
    id: 'job-3',
    title: 'DevOps Engineer',
    department: 'Infrastructure',
    location: 'Hyderabad (Hybrid)',
    salary_min: '12', salary_max: '18',
    experience_required: '3-6 years',
    employment_type: 'Full-time',
    work_mode: 'Hybrid',
    interview_mode: 'standard',
    role_category: 'Infrastructure',
    posted_days_ago: 1,
    tech_stack: ['Docker', 'Kubernetes', 'Terraform', 'Azure', 'CI/CD'],
    company_about: 'We build the infrastructure backbone that keeps modern applications running at scale.',
    team_name: 'Platform Reliability',
    team_size: '6 engineers',
    reports_to: 'VP Engineering',
    why_work_here: [
      'Own infrastructure for millions of users',
      'Modern cloud-native stack',
      'On-call compensation',
    ],
    benefits: ['Health Insurance', 'ESOP', 'On-call Bonus', 'Learning Budget'],
    hiring_timeline: [
      { stage: 'Resume Screening', time: 'Within 1 hour' },
      { stage: 'AI Interview', time: 'Within 24 hours' },
      { stage: 'Technical Round', time: '2-3 days' },
      { stage: 'Final Decision', time: 'Within 5 days' },
    ],
    jd_text: `We need a DevOps Engineer to scale and harden our cloud infrastructure.

Requirements:
- 3-6 years in DevOps/SRE
- Strong Kubernetes and Docker
- Infrastructure as Code (Terraform)
- Azure or AWS experience`,
    screening_questions: [],
  },
];

export const FILTER_OPTIONS = {
  locations: ['All Locations', 'Bangalore', 'Mumbai', 'Hyderabad'],
  departments: ['All Departments', 'Engineering', 'Data Platform', 'Infrastructure'],
  experience: ['All Levels', '0-2 years', '2-4 years', '3-5 years', '5+ years'],
};