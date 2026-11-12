"""Small, local conversation cues; no model calls, stored profiles or extra listeners."""
import re

def day_requested(text):
    """A time word alone is not a request for operational telemetry."""
    direct = r"\b(daybook|checklist|dashboard|what.s (left|running)|anything (fail|break|broke|wrong)|how.s the (cluster|system))\b"
    work = r"\b(jobs?|queue|queued|machines|runs?|build|render|backup|scan|service|refresh|failed|failures)\b"
    recap = r"\b(what (got|did we|have we)|get done|got done|accomplish\w*)\b"
    timing = r"\b(today|this morning|tonight|status|finish\w*|done|did|check|running)\b"
    return bool(re.search(direct, text, re.I) or (re.search(work, text, re.I) and re.search(timing, text, re.I))
                or (re.search(recap, text, re.I) and re.search(timing, text, re.I)))

def guidance(text):
    """Turn-specific cue added to the system prompt."""
    base = ("Treat this as a continuing conversation: respond to the user's actual point, keep the subject and constraints "
            "from the recent turns, and accept corrections immediately. Never reset with a generic greeting. "
            "Do not end every answer with a question; ask at most one when it would move things forward. "
            "When speech is unclear, ask about the one uncertain detail instead of inventing it. "
            "Use the supplied conversation as evidence of what was said; never invent earlier events. ")
    if re.search(r"\b(play|imagine|pretend|story|surprise me|weird|silly|riff)\b", text, re.I):
        return base + "The user is inviting play. Join in with a specific, vivid contribution, not a menu of activities. Keep fiction inside the imagined scene."
    if re.search(r"\b(decide|choose|torn|trade.?off|should i|help me think|think (it|this) through)\b", text, re.I):
        return base + "Help them reach a decision. Name the real tradeoff, give a provisional take with its reason, and ask only for a missing constraint. Do not manufacture certainty."
    if re.search(r"\b(explore|idea|what if|wonder|curious|brainstorm)\b", text, re.I):
        return base + "Explore alongside them. Develop one concrete implication or surprising connection, distinguish speculation from fact, and leave space for the next thought."
    return base + "Have a specific response to what was said, rather than generic encouragement or an offer to help."
