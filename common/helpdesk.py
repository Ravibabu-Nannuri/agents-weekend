"""Fake IT helpdesk "backend" + the tools agents can call.

Everything is in-memory and made up (no real company data), so the repo is
safe to keep public. In a real system these would be calls to ServiceNow,
Jira, Okta, a status page, etc.

Teaching point: the docstring and type hints of each @tool become the schema
the LLM sees. Vague docstrings = wrong tool choices. Try it in block 02.
"""

from datetime import datetime

from langchain_core.tools import tool

# --------------------------------------------------------------------------
# Fake data
# --------------------------------------------------------------------------
USERS = {
    "alice": {"name": "Alice Chen", "email": "alice@example.com", "dept": "Finance", "laptop": "MacBook Pro 14"},
    "bob": {"name": "Bob Patel", "email": "bob@example.com", "dept": "Sales", "laptop": "ThinkPad X1"},
    "carol": {"name": "Carol Diaz", "email": "carol@example.com", "dept": "Engineering", "laptop": "MacBook Air 13"},
}

TICKETS = {
    "INC-1001": {"user": "alice", "title": "VPN disconnects every 10 minutes", "status": "In Progress", "priority": "P2"},
    "INC-1002": {"user": "bob", "title": "Outlook not syncing calendar", "status": "Open", "priority": "P3"},
    "INC-1003": {"user": "carol", "title": "Need access to staging database", "status": "Resolved", "priority": "P3"},
}

SYSTEM_STATUS = {
    "email": "operational",
    "vpn": "degraded - EU gateway intermittent, fix ETA 2 hours",
    "wifi": "operational",
    "sso": "operational",
    "printers": "outage - 3rd floor printer offline",
}

KB_ARTICLES = [
    {"id": "KB-01", "title": "Connect to the VPN", "keywords": ["vpn", "remote", "connect", "globalprotect"],
     "body": "Open GlobalProtect, choose the nearest gateway, sign in with SSO. If it drops, switch gateway and restart the client."},
    {"id": "KB-02", "title": "Reset your password", "keywords": ["password", "reset", "locked", "login"],
     "body": "Use the self-service portal at id.example.com. If locked out, the helpdesk can reset it after verifying identity."},
    {"id": "KB-03", "title": "Set up email on your phone", "keywords": ["email", "phone", "outlook", "mobile"],
     "body": "Install Outlook mobile, sign in with your work email, approve the MFA prompt."},
    {"id": "KB-04", "title": "Fix Wi-Fi in the office", "keywords": ["wifi", "wi-fi", "wireless", "network"],
     "body": "Forget the 'Corp' network, reconnect, accept the certificate. Still failing? Restart your laptop."},
    {"id": "KB-05", "title": "Request software", "keywords": ["software", "install", "license", "app"],
     "body": "Submit a request in the IT portal. Standard apps are approved automatically within 1 hour."},
]

_next_ticket = 1004


# --------------------------------------------------------------------------
# Tools
# --------------------------------------------------------------------------
@tool
def search_kb(query: str) -> str:
    """Search the IT knowledge base for how-to articles.
    Use for 'how do I...' questions about VPN, passwords, email, Wi-Fi or software."""
    q = query.lower()
    hits = [a for a in KB_ARTICLES if any(k in q for k in a["keywords"])]
    if not hits:
        return "No matching articles."
    return "\n\n".join(f"[{a['id']}] {a['title']}: {a['body']}" for a in hits[:2])


@tool
def check_system_status(system: str) -> str:
    """Check whether an IT system is up. Valid systems: email, vpn, wifi, sso, printers.
    Use when a user reports something is broken, before creating a ticket."""
    return SYSTEM_STATUS.get(system.lower().strip(), f"Unknown system '{system}'. Valid: {', '.join(SYSTEM_STATUS)}")


@tool
def get_ticket(ticket_id: str) -> str:
    """Look up an existing support ticket by its ID, e.g. INC-1001."""
    t = TICKETS.get(ticket_id.upper().strip())
    if not t:
        return f"Ticket {ticket_id} not found."
    return f"{ticket_id}: '{t['title']}' | status={t['status']} | priority={t['priority']} | user={t['user']}"


@tool
def create_ticket(username: str, title: str, priority: str = "P3") -> str:
    """Create a new support ticket for a user. priority is P1 (critical) to P4 (low).
    Only create a ticket if the problem is not explained by a known outage."""
    global _next_ticket
    if username.lower() not in USERS:
        return f"Unknown user '{username}'. Ask the user for their username."
    ticket_id = f"INC-{_next_ticket}"
    _next_ticket += 1
    TICKETS[ticket_id] = {"user": username.lower(), "title": title, "status": "Open", "priority": priority}
    return f"Created {ticket_id} for {username}: '{title}' ({priority})"


@tool
def lookup_user(username: str) -> str:
    """Get a user's profile (name, email, department, laptop) by username."""
    u = USERS.get(username.lower().strip())
    return str(u) if u else f"User '{username}' not found."


def do_password_reset(username: str) -> str:
    """The actual 'dangerous' action. Wrapped with human approval in block 05."""
    if username.lower() not in USERS:
        return f"Unknown user '{username}'."
    stamp = datetime.now().strftime("%H:%M")
    return f"Password for {username} reset at {stamp}. Temporary password sent to {USERS[username.lower()]['email']}."


KB_TOOLS = [search_kb, check_system_status]
TICKET_TOOLS = [get_ticket, create_ticket, lookup_user]
ALL_TOOLS = KB_TOOLS + TICKET_TOOLS

SYSTEM_PROMPT = (
    "You are a friendly IT helpdesk agent for Example Corp. "
    "Use the tools to look things up instead of guessing. "
    "If a system has a known outage, tell the user instead of creating a ticket. "
    "Keep answers short and practical."
)
