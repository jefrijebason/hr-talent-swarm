"""
cleanup_cosmos.py — Delete old/test candidates and stale data from Cosmos.

Usage:
    python cleanup_cosmos.py --preview        # See what would be deleted (safe)
    python cleanup_cosmos.py --delete-test    # Delete test candidates only
    python cleanup_cosmos.py --delete-old 30  # Delete candidates older than 30 days
    python cleanup_cosmos.py --delete-audit   # Delete all audit logs (usually largest)
    python cleanup_cosmos.py --delete-all     # NUKE everything (dangerous)
"""
import sys
import argparse
from datetime import datetime, timedelta

from shared.cosmos_client import (
    get_all_candidates, get_all_jobs, get_all_assignments,
    get_all_interviewers, get_all_hr_users,
)

# Direct container access for batch deletes
from shared import cosmos_client as cx


def _get_container(name):
    """Get raw container handle from your cosmos_client module."""
    # Try common attribute names — adjust if your client uses different ones
    for attr in [f"{name}_container", f"_{name}_container", name, f"_{name}"]:
        if hasattr(cx, attr):
            return getattr(cx, attr)
    # Try via database
    if hasattr(cx, "database"):
        return cx.database.get_container_client(name)
    if hasattr(cx, "db"):
        return cx.db.get_container_client(name)
    raise RuntimeError(f"Could not find container '{name}' in cosmos_client module")


def delete_items(container_name, items, partition_key_field="id"):
    """Delete a list of items from a Cosmos container."""
    container = _get_container(container_name)
    deleted = 0
    for item in items:
        try:
            iid = item.get("id")
            pk = item.get(partition_key_field, iid)
            container.delete_item(item=iid, partition_key=pk)
            deleted += 1
            if deleted % 10 == 0:
                print(f"  ... deleted {deleted}/{len(items)}")
        except Exception as e:
            print(f"  ✗ Failed to delete {iid}: {e}")
    return deleted


def preview():
    """Show what's in your Cosmos DB without deleting anything."""
    candidates = get_all_candidates()
    jobs = get_all_jobs()
    print(f"\n═══ Cosmos DB Inventory ═══")
    print(f"  Candidates:    {len(candidates)}")
    print(f"  Jobs:          {len(jobs)}")
    try:
        print(f"  Assignments:   {len(get_all_assignments())}")
    except Exception:
        pass
    try:
        print(f"  Interviewers:  {len(get_all_interviewers())}")
    except Exception:
        pass
    try:
        print(f"  HR Users:      {len(get_all_hr_users())}")
    except Exception:
        pass

    print(f"\n── Sample candidates ──")
    for c in candidates[:5]:
        print(f"  {c.get('id','?')[:8]}... | {c.get('name','?'):<25} | {c.get('status','?'):<25} | job: {c.get('job_id','—')[:8] if c.get('job_id') else '—'}")
    if len(candidates) > 5:
        print(f"  ... and {len(candidates)-5} more")

    # Categorize candidates
    test_candidates = [c for c in candidates if _is_test_candidate(c)]
    print(f"\n── Categories ──")
    print(f"  Test/dummy candidates:  {len(test_candidates)}")
    print(f"  No job_id linked:       {sum(1 for c in candidates if not c.get('job_id'))}")
    print(f"  Rejected:               {sum(1 for c in candidates if c.get('status') == 'rejected')}")


def _is_test_candidate(c):
    """Heuristics — adjust to your needs."""
    name = (c.get("name") or "").lower()
    email = (c.get("email") or "").lower()
    return (
        "test" in name or "test" in email or
        "dummy" in name or "example.com" in email or
        name in ("", "candidate", "name")
    )


def delete_test_candidates():
    candidates = get_all_candidates()
    test = [c for c in candidates if _is_test_candidate(c)]
    print(f"Found {len(test)} test candidates to delete.")
    if not _confirm():
        return
    deleted = delete_items("candidates", test)
    print(f"\n✓ Deleted {deleted} test candidates")


def delete_old_candidates(days):
    candidates = get_all_candidates()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    old = [c for c in candidates if (c.get("created_at") or "9999") < cutoff]
    print(f"Found {len(old)} candidates older than {days} days.")
    if not _confirm():
        return
    deleted = delete_items("candidates", old)
    print(f"\n✓ Deleted {deleted} old candidates")


def delete_audit():
    """Audit logs are usually the biggest space + RU drain."""
    try:
        container = _get_container("audit")
        items = list(container.read_all_items())
        print(f"Found {len(items)} audit logs.")
        if not _confirm():
            return
        deleted = delete_items("audit", items)
        print(f"\n✓ Deleted {deleted} audit logs")
    except Exception as e:
        print(f"Could not access audit container: {e}")


def delete_all():
    """⚠ Nuclear option — wipes everything."""
    print("⚠⚠⚠  THIS WILL DELETE ALL DATA  ⚠⚠⚠")
    confirm = input('Type "DELETE EVERYTHING" to proceed: ').strip()
    if confirm != "DELETE EVERYTHING":
        print("Aborted.")
        return

    for cname in ["candidates", "jobs", "assignments", "interviewers",
                  "hr_users", "audit", "talent_pool", "agent_feed"]:
        try:
            container = _get_container(cname)
            items = list(container.read_all_items())
            if items:
                print(f"\nDeleting {len(items)} items from {cname}...")
                delete_items(cname, items)
        except Exception as e:
            print(f"  Skipped {cname}: {e}")
    print("\n✓ Done")


def _confirm():
    ans = input("Proceed? (yes/no): ").strip().lower()
    return ans == "yes"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview",       action="store_true", help="Show inventory, no deletion")
    parser.add_argument("--delete-test",   action="store_true", help="Delete test candidates")
    parser.add_argument("--delete-old",    type=int, help="Delete candidates older than N days")
    parser.add_argument("--delete-audit",  action="store_true", help="Delete all audit logs")
    parser.add_argument("--delete-all",    action="store_true", help="⚠ Delete everything")
    args = parser.parse_args()

    if args.preview:                preview()
    elif args.delete_test:          delete_test_candidates()
    elif args.delete_old:           delete_old_candidates(args.delete_old)
    elif args.delete_audit:         delete_audit()
    elif args.delete_all:           delete_all()
    else:
        parser.print_help()
        preview()