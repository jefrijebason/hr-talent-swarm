"""
agents/aria_interviewer/question_pools.py

Pre-baked question banks across the 5 evaluation dimensions and 9 role archetypes.

WHY: Generating every question from scratch with GPT costs ~$0.10-0.20 per interview.
Reading from a pool + a small personalization call costs ~$0.02-0.04. ~60% savings.

The pools are intentionally hand-crafted to test:
  - first_principles  → Can they question assumptions and reason from atoms?
  - decomposition     → Can they break ambiguous problems into solvable pieces?
  - ai_fluency        → Are they using AI as a force-multiplier or do they fear it?
  - taste             → Can they tell good from great?
  - verification      → Can they catch AI mistakes / validate output?

Each question has:
  - text         : the question itself
  - difficulty   : 1-5 (1=warmup, 5=staff-engineer-level)
  - tags         : topical tags for matching to candidate's resume
  - depth_hooks  : follow-up probes ARIA can use if answer is shallow
"""

from typing import Any, Dict, List

# ════════════════════════════════════════════════════════════════════════
# UNIVERSAL POOLS — apply to all role archetypes
# ════════════════════════════════════════════════════════════════════════

FIRST_PRINCIPLES = [
    {
        "text": "Most companies do code reviews. Why? What's the actual problem code reviews solve, and is there a fundamentally better way to solve it?",
        "difficulty": 3,
        "tags": ["engineering", "process"],
        "depth_hooks": [
            "If AI does pre-review, what's left for humans to catch?",
            "Have you ever seen a code review catch something review process couldn't have caught any other way?",
            "What's the real cost of NOT doing them — not the surface answer.",
        ],
    },
    {
        "text": "If you had to redesign email from scratch in 2025, knowing what we know now — what would you keep, what would you throw out, and what doesn't exist today that should?",
        "difficulty": 4,
        "tags": ["product", "first_principles"],
        "depth_hooks": [
            "Why does that thing you kept actually matter?",
            "What's a feature email has only because of historical accident?",
            "Would your design work for grandparents AND for engineers?",
        ],
    },
    {
        "text": "Pick a process at your current company that everyone follows but no one questions. Why does it exist? What problem did it originally solve? Is that problem still real?",
        "difficulty": 3,
        "tags": ["meta", "self_aware"],
        "depth_hooks": [
            "What would happen tomorrow if you just stopped doing it?",
            "What would you replace it with?",
        ],
    },
    {
        "text": "Standups happen at 9 AM at most companies. Trace that all the way back — why 9 AM, why daily, why standing? Now: design the optimal sync ritual for a modern AI-augmented team.",
        "difficulty": 4,
        "tags": ["process", "teams"],
        "depth_hooks": [
            "How does async tooling change the math?",
            "What's the actual signal vs noise ratio at standup?",
        ],
    },
    {
        "text": "Why do we have file systems with folders? Trace it to its origin. If we designed storage from scratch today for AI-native apps, would folders still exist?",
        "difficulty": 4,
        "tags": ["technical", "first_principles"],
        "depth_hooks": [
            "What replaces 'where is this file' in your design?",
            "How do you handle a million 'files'?",
        ],
    },
    {
        "text": "Almost every B2B SaaS has the same login → dashboard → settings → billing structure. Why? If you were building a B2B product today, would you keep that pattern?",
        "difficulty": 3,
        "tags": ["product", "design"],
        "depth_hooks": [
            "What's lost when you break the pattern?",
            "What problem is the dashboard actually solving?",
        ],
    },
]

DECOMPOSITION = [
    {
        "text": "I'm going to give you a vague problem: 'Our app feels slow.' Walk me through how you'd approach diagnosing this from scratch — no tools assumed. What are your first 5 sub-questions?",
        "difficulty": 3,
        "tags": ["debugging", "diagnosis"],
        "depth_hooks": [
            "Which of those sub-questions is the cheapest to answer?",
            "Which sub-question, if wrong, invalidates the others?",
            "How do you avoid getting stuck in one branch?",
        ],
    },
    {
        "text": "You're told 'reduce infrastructure costs by 50% in one quarter.' Decompose that into 10 sub-problems, then tell me which 3 you'd actually work on first and why.",
        "difficulty": 4,
        "tags": ["systems", "leverage"],
        "depth_hooks": [
            "What did you NOT include and why?",
            "How would you measure progress on the 3 you chose?",
        ],
    },
    {
        "text": "A user reports 'the report shows wrong numbers.' That's all you have. How do you break that into a tractable investigation?",
        "difficulty": 2,
        "tags": ["debugging", "user_reports"],
        "depth_hooks": [
            "What's the minimum info you'd ask the user for?",
            "How do you decide whether it's a data, logic, or display bug?",
        ],
    },
    {
        "text": "I want to build 'a better Notion for engineers.' That's vague on purpose. Walk me through how you'd narrow it into something buildable in a quarter.",
        "difficulty": 4,
        "tags": ["product", "scope"],
        "depth_hooks": [
            "What's the single user problem you'd commit to?",
            "What would you intentionally NOT build?",
        ],
    },
    {
        "text": "Your team has 50 open bugs. You can fix 10 this sprint. How do you decide which 10 without spending half a day in triage?",
        "difficulty": 3,
        "tags": ["prioritization", "tradeoffs"],
        "depth_hooks": [
            "What's the cheapest signal that approximates real impact?",
            "Which 10 would your gut pick — and is that wrong?",
        ],
    },
]

AI_FLUENCY = [
    {
        "text": "Walk me through the last time you used AI to solve a non-trivial problem at work. Be specific: what was the problem, what was your first prompt, how did the conversation evolve, what did you do with the output?",
        "difficulty": 3,
        "tags": ["ai_usage", "workflow"],
        "depth_hooks": [
            "What did you tell the AI that made the difference?",
            "Where did the AI get it wrong, and how did you catch it?",
            "Would you trust the same approach tomorrow?",
        ],
    },
    {
        "text": "Where in your workflow is AI a force-multiplier vs. a crutch? How do you decide when to use it vs. think it through yourself?",
        "difficulty": 4,
        "tags": ["ai_usage", "judgment"],
        "depth_hooks": [
            "Give me a concrete example of each.",
            "What's a task you'd never delegate to AI? Why?",
        ],
    },
    {
        "text": "Show me your prompt structure for a hard technical problem. Don't tell me 'I just ask clearly' — actually walk me through what context you set, how you constrain the output, and how you handle iteration.",
        "difficulty": 4,
        "tags": ["prompt_engineering", "specific"],
        "depth_hooks": [
            "What's a prompt that worked surprisingly well?",
            "What's a prompt structure you've abandoned and why?",
        ],
    },
    {
        "text": "Tell me about a time the AI was confidently wrong. How did you spot it? What did that teach you about when to trust AI output?",
        "difficulty": 3,
        "tags": ["verification", "ai_failures"],
        "depth_hooks": [
            "Do you have a default verification routine now?",
            "What categories of tasks does AI hallucinate on most?",
        ],
    },
    {
        "text": "Imagine I'm a junior engineer asking you: 'How do I get good at using AI?' Don't give me platitudes — give me 3 concrete habits.",
        "difficulty": 3,
        "tags": ["teaching", "meta"],
        "depth_hooks": [
            "Which of these is hardest to actually do?",
            "What habit did you have to UNLEARN?",
        ],
    },
    {
        "text": "Pick a tool you use daily. Walk me through how you've changed your workflow with that tool because of AI in the past 12 months. Be specific about before/after.",
        "difficulty": 3,
        "tags": ["adoption", "workflow"],
        "depth_hooks": [
            "What changed about how you THINK, not just what you do?",
            "What's harder now than it was?",
        ],
    },
]

TASTE = [
    {
        "text": "I'm going to describe 3 different approaches to the same problem. Listen carefully and tell me which is best — and what 'best' even means here.",
        "difficulty": 4,
        "tags": ["judgment", "comparison"],
        "depth_hooks": [
            "What did the worst option get RIGHT?",
            "Under what conditions would the worst become the best?",
        ],
        "is_meta": True,  # ARIA will generate the 3 options at runtime
    },
    {
        "text": "Show me something — anything you've built, written, or designed — that you're embarrassed by now. What made it bad in hindsight? What would you do differently?",
        "difficulty": 3,
        "tags": ["self_awareness", "growth"],
        "depth_hooks": [
            "What did you THINK was good about it at the time?",
            "What does this say about how your taste has evolved?",
        ],
    },
    {
        "text": "Pick someone whose work you admire — engineer, designer, founder, anyone. What specifically do they do well that most people in their field don't?",
        "difficulty": 3,
        "tags": ["models", "specificity"],
        "depth_hooks": [
            "Can you teach that?",
            "What would they say about YOUR work?",
        ],
    },
    {
        "text": "Two API designs solve the same problem: one is REST with 6 endpoints, the other is a single GraphQL endpoint. Don't tell me 'it depends' — pick one and tell me when YOU would never choose the other.",
        "difficulty": 4,
        "tags": ["technical", "judgment"],
        "depth_hooks": [
            "What's the hidden cost of your choice 2 years from now?",
            "What's a third option you didn't get asked about?",
        ],
    },
    {
        "text": "Look at any popular product — pick one. Tell me one thing that is objectively poorly designed, and explain why it shipped that way.",
        "difficulty": 3,
        "tags": ["critique", "empathy"],
        "depth_hooks": [
            "What would it take to fix it now?",
            "Why has no one fixed it yet?",
        ],
    },
]

VERIFICATION = [
    {
        "text": "I'm going to describe a solution my AI assistant proposed for a problem. Listen carefully and tell me what could go wrong with it.",
        "difficulty": 4,
        "tags": ["verification", "ai_outputs"],
        "is_meta": True,  # ARIA generates a plausible-but-flawed proposal at runtime
        "depth_hooks": [
            "What kind of test would catch this?",
            "What's the worst-case if this ships unfixed?",
        ],
    },
    {
        "text": "Your AI assistant just produced 200 lines of code that 'looks right' and passes basic tests. Before you ship it, what's your validation routine?",
        "difficulty": 3,
        "tags": ["safety_net", "discipline"],
        "depth_hooks": [
            "What's the absolute minimum routine for trivial code?",
            "When do you skip the routine and ship faster?",
        ],
    },
    {
        "text": "Describe a time you trusted an output (from a tool, a person, or AI) and got burned. What was the FIRST signal you missed that should have warned you?",
        "difficulty": 3,
        "tags": ["calibration", "lessons"],
        "depth_hooks": [
            "Has your trust calibration changed since?",
            "Are you ever paranoid in the wrong direction now?",
        ],
    },
    {
        "text": "I tell you: 'Our user retention dropped 12% last week.' Before you do anything, what do you verify? You have 10 minutes.",
        "difficulty": 3,
        "tags": ["data", "skepticism"],
        "depth_hooks": [
            "What's the cheapest thing to check first?",
            "What if the data system itself is the bug?",
        ],
    },
    {
        "text": "AI generates a confident analysis: 'Switch to PostgreSQL — it'll be 3x faster for your workload.' What questions do you ask before you'd act on this?",
        "difficulty": 4,
        "tags": ["due_diligence", "ai_recommendations"],
        "depth_hooks": [
            "What if the AI is right? How do you confirm?",
            "What evidence would change your mind?",
        ],
    },
]

# ════════════════════════════════════════════════════════════════════════
# ROLE-SPECIFIC POOLS — supplement universal pools
# ════════════════════════════════════════════════════════════════════════

ROLE_SPECIFIC = {
    "engineer": [
        {
            "text": "Production is down. The error message is generic. You have 15 minutes before customer impact compounds. What's your decision tree in the first 5 minutes?",
            "difficulty": 4, "dimension": "decomposition",
            "depth_hooks": ["What if rolling back makes it worse?", "When do you stop and call for help?"],
        },
        {
            "text": "Pick a microservice you've owned. If you had to rewrite it knowing what you know now, what's the ONE architectural decision you'd reverse?",
            "difficulty": 4, "dimension": "first_principles",
            "depth_hooks": ["What signal did you miss originally?", "What was right about your original choice?"],
        },
    ],
    "pm": [
        {
            "text": "Engineering says your feature will take 6 weeks. Sales says they'll lose the deal without it in 2. You have to choose. Walk me through your decision.",
            "difficulty": 4, "dimension": "decomposition",
            "depth_hooks": ["What information would change your answer?", "What's the cost of being wrong each direction?"],
        },
        {
            "text": "Pick a product you use daily that has a feature no one talks about but everyone uses. What did the PM who shipped it figure out that others missed?",
            "difficulty": 3, "dimension": "taste",
            "depth_hooks": ["What's a feature like that you'd LIKE to ship?", "Why doesn't anyone talk about it?"],
        },
    ],
    "designer": [
        {
            "text": "Show me a design you killed even though stakeholders liked it. Why did you push back? What did you replace it with?",
            "difficulty": 4, "dimension": "taste",
            "depth_hooks": ["What signal told you it was wrong?", "Were you certain when you killed it?"],
        },
        {
            "text": "A PM hands you 'redesign the onboarding to convert better.' They have no data, no hypothesis. What do you do in week 1?",
            "difficulty": 3, "dimension": "decomposition",
            "depth_hooks": ["What's your first artifact?", "When do you start sketching vs. researching?"],
        },
    ],
    "data": [
        {
            "text": "Stakeholder asks 'is feature X causing churn?' You have access to all the data. What's your investigation plan, and what's the FIRST thing you'd check?",
            "difficulty": 4, "dimension": "decomposition",
            "depth_hooks": ["How do you avoid confirmation bias?", "What would make you abandon this hypothesis?"],
        },
        {
            "text": "A model you built is performing 5% worse this month. Walk me through your debugging steps in order. Don't skip the obvious ones.",
            "difficulty": 4, "dimension": "verification",
            "depth_hooks": ["What if the data pipeline itself is broken?", "When do you retrain vs. investigate?"],
        },
    ],
    "ml": [
        {
            "text": "Your model has 92% accuracy on the test set but production performance is 78%. Diagnose. Don't tell me 'distribution shift' — that's the symptom, not the diagnosis.",
            "difficulty": 5, "dimension": "verification",
            "depth_hooks": ["What's your cheapest experiment?", "What if it's NOT distribution shift?"],
        },
        {
            "text": "When do you reach for a small fine-tuned model vs. a big LLM with smart prompting? Be specific.",
            "difficulty": 4, "dimension": "ai_fluency",
            "depth_hooks": ["What's a case where you'd use BOTH?", "What's the hidden cost of fine-tuning?"],
        },
    ],
    "sales": [
        {
            "text": "Lost deal — they went with a clearly worse competitor. You have 15 minutes to figure out why. What questions do you ask?",
            "difficulty": 3, "dimension": "decomposition",
            "depth_hooks": ["What if the prospect won't tell you?", "What signal did you miss earlier in the deal?"],
        },
        {
            "text": "AI tools can now draft sales emails. Walk me through what you do that AI CAN'T do in a sales cycle.",
            "difficulty": 3, "dimension": "ai_fluency",
            "depth_hooks": ["Where IS AI a force-multiplier for you?", "What changes about hiring AEs in 2 years?"],
        },
    ],
    "marketing": [
        {
            "text": "You can either spend $50K on a single brand campaign or $50K split across 20 micro-experiments. What's the right call and what would change your answer?",
            "difficulty": 4, "dimension": "decomposition",
            "depth_hooks": ["What's the multiplier on learning vs. revenue?", "Have you ever been wrong about this?"],
        },
        {
            "text": "An AI agent can now write all your blog content. Pick: would you let it? What changes?",
            "difficulty": 3, "dimension": "ai_fluency",
            "depth_hooks": ["Where's the human still essential?", "How do readers find out and what do they do?"],
        },
    ],
    "ops": [
        {
            "text": "A process you own takes 4 hours of human time daily. Walk me through how you'd cut it to 30 minutes — and tell me what you'd refuse to automate even if you could.",
            "difficulty": 3, "dimension": "decomposition",
            "depth_hooks": ["Which step is the highest-leverage to automate?", "What breaks if you automate everything?"],
        },
    ],
    "cs": [
        {
            "text": "A customer is escalating loudly but their underlying ask is small. A quiet customer's renewal is at risk. You have time for one this morning. Which one and why?",
            "difficulty": 3, "dimension": "decomposition",
            "depth_hooks": ["What information would flip your choice?", "How do you avoid the squeaky-wheel trap long-term?"],
        },
    ],
}


# ════════════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════════════

DIMENSIONS = ["first_principles", "decomposition", "ai_fluency", "taste", "verification"]

_DIMENSION_TO_POOL: Dict[str, List[Dict[str, Any]]] = {
    "first_principles": FIRST_PRINCIPLES,
    "decomposition":    DECOMPOSITION,
    "ai_fluency":       AI_FLUENCY,
    "taste":            TASTE,
    "verification":     VERIFICATION,
}


def pool_for_dimension(dimension: str) -> List[Dict[str, Any]]:
    return _DIMENSION_TO_POOL.get(dimension, [])


def pool_for_role(archetype: str) -> List[Dict[str, Any]]:
    return ROLE_SPECIFIC.get(archetype, [])


def all_questions_for_archetype(archetype: str) -> List[Dict[str, Any]]:
    """Combine universal pools + role-specific. Each question is tagged by dimension."""
    combined: List[Dict[str, Any]] = []
    for dim, pool in _DIMENSION_TO_POOL.items():
        for q in pool:
            combined.append({**q, "dimension": dim, "source": "universal"})
    for q in pool_for_role(archetype):
        combined.append({**q, "source": "role_specific"})
    return combined
