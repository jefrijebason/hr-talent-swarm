"""
Daily Digest System
Sends one organized summary email to each HR at 8 AM.
Replaces hundreds of per-event spam emails.
"""

from datetime import datetime, timedelta
from shared.cosmos_client import col, get_hr_user
from agents.communicator.agent import send_email
from shared.agent_feed import log_agent


def get_hr_candidates(hr_id: str) -> list:
    """Get all active candidates for a specific HR."""
    try:
        container = col("candidates")
        items = list(container.read_all_items())
        return [c for c in items if c.get("hr_id") == hr_id
                and c.get("status") not in ["hired", "rejected"]]
    except Exception as e:
        print(f"[DIGEST] Error fetching candidates: {e}")
        return []


def get_all_hr_users() -> list:
    """Get all HR users."""
    try:
        container = col("hr_users")
        return list(container.read_all_items())
    except Exception as e:
        print(f"[DIGEST] Error fetching HR users: {e}")
        return []


def get_pipeline_stats_for_hr(hr_id: str) -> dict:
    """Calculate real pipeline stats for one HR's jobs."""
    try:
        container  = col("candidates")
        all_items  = list(container.read_all_items())
        candidates = [c for c in all_items if c.get("hr_id") == hr_id]

        today = datetime.utcnow().date()

        # Today's new applications
        new_today = [
            c for c in candidates
            if c.get("applied_at", "")[:10] == str(today)
        ]

        stats = {
            "total":        len(candidates),
            "new_today":    len(new_today),
            "applied":      len([c for c in candidates if c.get("status") == "applied"]),
            "screening":    len([c for c in candidates if c.get("status") in
                                 ["screened", "ai_interview_sent"]]),
            "ai_interview": len([c for c in candidates if c.get("status") in
                                 ["ai_interview_complete", "ai_interview_in_progress"]]),
            "coding":       len([c for c in candidates if c.get("status") in
                                 ["coding_sent", "coding_complete"]]),
            "technical":    len([c for c in candidates if c.get("status") in
                                 ["waiting_technical_interview",
                                  "technical_interview_scheduled"]]),
            "hr_round":     len([c for c in candidates if c.get("status") in
                                 ["waiting_hr_interview", "hr_interview_scheduled"]]),
            "hired":        len([c for c in candidates if c.get("status") == "hired"]),
            "rejected":     len([c for c in candidates if c.get("status") == "rejected"]),
        }
        return stats
    except Exception as e:
        print(f"[DIGEST] Stats error: {e}")
        return {}


def get_attention_items(hr_id: str) -> list:
    """Find candidates that need HR attention."""
    try:
        container  = col("candidates")
        all_items  = list(container.read_all_items())
        candidates = [c for c in all_items if c.get("hr_id") == hr_id]

        now      = datetime.utcnow()
        items    = []

        for c in candidates:
            name   = c.get("name", "Unknown")
            status = c.get("status", "")
            cid    = c.get("id", "")[:8].upper()

            # Stuck in applied for 2+ hours (pipeline may have failed)
            if status == "applied" and c.get("applied_at"):
                try:
                    applied = datetime.fromisoformat(c["applied_at"])
                    if (now - applied).total_seconds() > 7200:
                        items.append({
                            "level":   "🔴",
                            "name":    name,
                            "id":      cid,
                            "message": "Stuck at application stage (2+ hours). "
                                       "Pipeline may have failed."
                        })
                except Exception:
                    pass

            # Stuck in any stage for 48+ hours
            if status in ["ai_interview_sent", "coding_sent"] \
                    and c.get("applied_at"):
                try:
                    applied = datetime.fromisoformat(c["applied_at"])
                    if (now - applied).total_seconds() > 172800:  # 48hrs
                        items.append({
                            "level":   "🟡",
                            "name":    name,
                            "id":      cid,
                            "message": f"No response for 48+ hours at {status} stage."
                        })
                except Exception:
                    pass

            # Evaluation ready (scorecard submitted)
            if status == "technical_complete_pending_hr":
                items.append({
                    "level":   "🟢",
                    "name":    name,
                    "id":      cid,
                    "message": "Technical evaluation complete. "
                               "Your decision is needed."
                })

            # Pipeline failed
            if status == "pipeline_failed":
                items.append({
                    "level":   "🔴",
                    "name":    name,
                    "id":      cid,
                    "message": f"Pipeline error: "
                               f"{c.get('failure_reason','Unknown error')}. "
                               f"Manual action needed."
                })

            # Resume unreadable
            if status == "resume_unreadable":
                items.append({
                    "level":   "🟡",
                    "name":    name,
                    "id":      cid,
                    "message": f"Resume could not be processed "
                               f"({c.get('resume_issue','unknown')}). "
                               f"Candidate notified."
                })

        return items[:10]  # Max 10 items
    except Exception as e:
        print(f"[DIGEST] Attention items error: {e}")
        return []


def get_todays_interviews(hr_id: str) -> list:
    """Get interviews scheduled for today."""
    try:
        container = col("assignments")
        items     = list(container.read_all_items())
        today_str = str(datetime.utcnow().date())

        interviews = []
        for a in items:
            slot = a.get("meeting_slot_human", "")
            if today_str in a.get("technical_interview_slot", "") \
                    or today_str in a.get("hr_interview_slot", ""):

                from shared.cosmos_client import get_candidate, get_interviewer
                candidate = get_candidate(a.get("candidate_id", ""))
                if candidate and candidate.get("hr_id") == hr_id:
                    iv_id = a.get("assigned_to", "")
                    iv    = get_interviewer(iv_id) if iv_id else None
                    interviews.append({
                        "candidate": candidate.get("name", "Unknown"),
                        "role":      candidate.get("applied_role", ""),
                        "slot":      slot or "Time TBC",
                        "interviewer": iv.get("name", "TBC") if iv else "TBC",
                        "type":      a.get("interview_type", "technical")
                    })

        return interviews[:5]  # Max 5
    except Exception as e:
        print(f"[DIGEST] Interviews error: {e}")
        return []


def get_pending_digest_events(hr_id: str) -> list:
    """Get queued non-urgent events since last digest."""
    try:
        container  = col("candidates")
        all_items  = list(container.read_all_items())
        candidates = [c for c in all_items if c.get("hr_id") == hr_id]

        events = []
        for c in candidates:
            for key, val in c.items():
                if key.startswith("digest_event_") \
                        and isinstance(val, dict) \
                        and not val.get("sent"):
                    events.append({
                        "candidate": c.get("name", "Unknown"),
                        "event":     val.get("event", "").replace("_", " ").title(),
                        "message":   val.get("message", ""),
                        "time":      val.get("timestamp", "")[:16].replace("T", " ")
                    })
                    # Mark as sent
                    try:
                        c[key]["sent"] = True
                        container.upsert_item(c)
                    except Exception:
                        pass

        return events[-20:]  # Last 20 events
    except Exception as e:
        print(f"[DIGEST] Events error: {e}")
        return []


def _build_digest_html(hr: dict, stats: dict, attention: list,
                        interviews: list, events: list) -> str:
    """Build the daily digest HTML email."""

    today = datetime.utcnow().strftime("%A %B %d, %Y")

    # Stats row
    def stat_cell(label, val, color="#6366f1"):
        return f"""
        <td style="text-align:center;padding:12px;
          border-right:1px solid #e2e8f0">
          <div style="font-size:24px;font-weight:800;color:{color}">
            {val}
          </div>
          <div style="font-size:11px;color:#94a3b8;margin-top:4px">
            {label}
          </div>
        </td>"""

    stats_html = f"""
    <table style="width:100%;border-collapse:collapse;
      border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;
      margin:16px 0">
      <tr>
        {stat_cell("New Today",  stats.get('new_today',0),  "#6366f1")}
        {stat_cell("Screening",  stats.get('screening',0),  "#0891b2")}
        {stat_cell("AI Interview",stats.get('ai_interview',0),"#7c3aed")}
        {stat_cell("Coding",     stats.get('coding',0),     "#22d3ee")}
        {stat_cell("Technical",  stats.get('technical',0),  "#d97706")}
        {stat_cell("HR Round",   stats.get('hr_round',0),   "#059669")}
        {stat_cell("Hired ✅",   stats.get('hired',0),      "#16a34a")}
      </tr>
    </table>"""

    # Attention items
    attention_html = ""
    if attention:
        rows = "".join(f"""
        <tr style="border-bottom:1px solid #f1f5f9">
          <td style="padding:10px 12px">{a['level']}</td>
          <td style="padding:10px 12px;font-weight:600">{a['name']}</td>
          <td style="padding:10px 12px;font-size:13px;color:#64748b">
            {a['message']}
          </td>
        </tr>""" for a in attention)

        attention_html = f"""
        <h3 style="color:#dc2626;margin:24px 0 12px">
          ⚠️ Needs Attention ({len(attention)})
        </h3>
        <table style="width:100%;border-collapse:collapse;
          border:1px solid #fecaca;border-radius:10px;overflow:hidden">
          {rows}
        </table>"""
    else:
        attention_html = """
        <div style="background:#f0fdf4;border:1px solid #86efac;
          border-radius:10px;padding:14px;margin:16px 0;
          color:#166534;font-weight:600">
          ✅ All clear — no items need your attention today.
        </div>"""

    # Today's interviews
    interviews_html = ""
    if interviews:
        rows = "".join(f"""
        <tr style="border-bottom:1px solid #f1f5f9">
          <td style="padding:10px 12px;font-weight:600">{i['candidate']}</td>
          <td style="padding:10px 12px;font-size:13px;color:#64748b">
            {i['type'].title()} Interview
          </td>
          <td style="padding:10px 12px;font-size:13px">{i['slot']}</td>
          <td style="padding:10px 12px;font-size:13px;color:#6366f1">
            {i['interviewer']}
          </td>
        </tr>""" for i in interviews)

        interviews_html = f"""
        <h3 style="color:#0f172a;margin:24px 0 12px">
          📅 Today's Interviews ({len(interviews)})
        </h3>
        <table style="width:100%;border-collapse:collapse;
          border:1px solid #e2e8f0;border-radius:10px;overflow:hidden">
          <tr style="background:#f8fafc">
            <th style="padding:10px 12px;text-align:left;
              font-size:12px;color:#64748b">Candidate</th>
            <th style="padding:10px 12px;text-align:left;
              font-size:12px;color:#64748b">Type</th>
            <th style="padding:10px 12px;text-align:left;
              font-size:12px;color:#64748b">Time</th>
            <th style="padding:10px 12px;text-align:left;
              font-size:12px;color:#64748b">Interviewer</th>
          </tr>
          {rows}
        </table>"""

    # Pipeline events
    events_html = ""
    if events:
        rows = "".join(f"""
        <tr style="border-bottom:1px solid #f1f5f9">
          <td style="padding:8px 12px;font-size:12px;color:#94a3b8">
            {e['time']}
          </td>
          <td style="padding:8px 12px;font-weight:600;
            font-size:13px">{e['candidate']}</td>
          <td style="padding:8px 12px;font-size:13px;color:#64748b">
            {e['message']}
          </td>
        </tr>""" for e in events)

        events_html = f"""
        <h3 style="color:#0f172a;margin:24px 0 12px">
          📋 Yesterday's Pipeline Activity ({len(events)} events)
        </h3>
        <table style="width:100%;border-collapse:collapse;
          border:1px solid #e2e8f0;border-radius:10px;overflow:hidden">
          {rows}
        </table>"""

    return f"""
<!DOCTYPE html>
<html>
<body style="font-family:Segoe UI,sans-serif;background:#f8fafc;
  margin:0;padding:24px">
<div style="max-width:700px;margin:0 auto;background:#fff;
  border-radius:16px;overflow:hidden;
  box-shadow:0 4px 20px rgba(0,0,0,0.08)">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#4f46e5,#7c3aed);
    padding:24px 32px">
    <div style="color:#c7d2fe;font-size:13px;margin-bottom:4px">
      {today}
    </div>
    <h1 style="color:#fff;margin:0;font-size:22px">
      🚀 Daily Pipeline Digest
    </h1>
    <p style="color:#c7d2fe;margin:4px 0 0;font-size:14px">
      Hi {hr.get('name','HR')}, here's your pipeline summary.
    </p>
  </div>

  <!-- Body -->
  <div style="padding:24px 32px">

    <!-- Stats -->
    <h3 style="color:#0f172a;margin:0 0 12px">
      📊 Pipeline Overview
    </h3>
    {stats_html}

    <!-- Attention -->
    {attention_html}

    <!-- Interviews -->
    {interviews_html}

    <!-- Events -->
    {events_html}

    <!-- Footer -->
    <div style="margin-top:28px;padding-top:16px;
      border-top:1px solid #e2e8f0;text-align:center">
      <a href="http://localhost:3000"
         style="display:inline-block;background:#4f46e5;color:#fff;
         padding:12px 28px;text-decoration:none;border-radius:8px;
         font-weight:bold">
        Open HR Dashboard →
      </a>
      <p style="color:#94a3b8;font-size:11px;margin:12px 0 0">
        This digest is sent once daily at 8 AM IST.<br>
        Urgent items are emailed immediately as they happen.
      </p>
    </div>
  </div>
</div>
</body>
</html>"""


def send_daily_digest(hr_id: str = None) -> dict:
    """
    Send daily digest to one HR (by id) or ALL HR users.
    Call this at 8 AM daily.
    """
    hr_users = [get_hr_user(hr_id)] if hr_id else get_all_hr_users()
    hr_users = [h for h in hr_users if h]  # remove None

    sent  = 0
    failed = 0

    for hr in hr_users:
        try:
            stats      = get_pipeline_stats_for_hr(hr["id"])
            attention  = get_attention_items(hr["id"])
            interviews = get_todays_interviews(hr["id"])
            events     = get_pending_digest_events(hr["id"])

            # Only skip if truly no candidates at all
            if stats.get("total", 0) == 0:
                print(f"[DIGEST] No candidates yet for {hr['name']} — sending welcome digest")

            html = _build_digest_html(hr, stats, attention,
                                       interviews, events)

            today = datetime.utcnow().strftime("%b %d")
            subject = (f"📊 Daily Pipeline Digest — {today} | "
                       f"{stats.get('total',0)} candidates | "
                       f"{len(attention)} need attention")

            result = send_email(
                to_address=hr["email"],
                subject=subject,
                body_html=html
            )

            if result:
                print(f"[DIGEST] ✅ Sent to {hr['name']} ({hr['email']})")
                log_agent("COMMUNICATOR", "daily_digest",
                          f"Digest sent to HR {hr['name']}")
                sent += 1
            else:
                print(f"[DIGEST] ❌ Failed for {hr['name']}")
                failed += 1

        except Exception as e:
            print(f"[DIGEST] Error for HR {hr.get('name','?')}: {e}")
            failed += 1

    return {"sent": sent, "failed": failed, "total": len(hr_users)}