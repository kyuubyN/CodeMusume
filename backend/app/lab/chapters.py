"""Campaign content: five chapters, one concept each, all measured for real.

A chapter owns a few files of the trainee, a workload that measures them, and
everything Agnes needs to run the experiment: the hypothesis question (whose
options are built around the *baseline measurement*), how to find the culprit
line from the static analyzers, a rubric for the spoken explanation, the fix
options (real patches, some of them plausible and wrong), and the scripted
lines of the visual-novel layer.
"""
from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from typing import Callable

from app.lab.analysis import RepoAnalysis
from app.models.schemas import AttributeType

SPECIMEN_DIR = os.path.join(os.path.dirname(__file__), "specimen")
BASE_DIR = os.path.join(SPECIMEN_DIR, "base")
FIXES_DIR = os.path.join(SPECIMEN_DIR, "fixes")


@dataclass
class KeyIdea:
    id: str
    label: str            # what the idea is, shown after grading
    patterns: list[str]   # regexes, any match counts (lower-cased transcript)
    ask: str              # Socratic follow-up when it is missing


@dataclass
class FixOption:
    key: str
    label: str
    detail: str
    verdict: str          # "best" | "good" | "partial" | "wrong"
    lesson: str           # Agnes, after the re-measurement


@dataclass
class Evidence:
    file: str
    best: set[int]
    ok: set[int]
    wrong_hints: dict[int, str] = field(default_factory=dict)


@dataclass
class Chapter:
    id: int
    slug: str
    title: str
    concept: str
    concept_title: str
    attribute: AttributeType
    workload: str
    files: list[str]                     # trainee paths this chapter owns
    focus_file: str
    question: str
    build_options: Callable[[dict], tuple[list[str], int]]
    evidence_prompt: str
    find_evidence: Callable[[RepoAnalysis, str], Evidence]
    explain_prompt: str
    rubric: list[KeyIdea]
    hints: dict[str, list[str]]
    fixes: list[FixOption]
    intro: list[str]
    reveal_right: str
    reveal_wrong: str
    reveal_certain_wrong: str
    evidence_right: str
    evidence_wrong: str
    fix_prompt: str
    outro: list[str]
    lore_title: str
    lore: str
    takeaway: str


def _abs(root: str, rel: str) -> str:
    return os.path.join(root, rel)


# ---------------------------------------------------------------------------
# Option builders: the answer is whatever the harness measured on this machine
# ---------------------------------------------------------------------------

def _opts_leaks(base: dict) -> tuple[list[str], int]:
    m = base.get("metrics", {})
    leaked, n, bad = m.get("leaked_fds", 0), m.get("requests", 400), m.get("bad_requests", 20)
    options = [
        "Zero. Python closes a file when the function returns.",
        f"About {bad}, one for every malformed report.",
        f"All {n}. Every request leaks its file.",
        "Negative. The lab absorbs stray descriptors as nutrients.",
    ]
    idx = 0 if leaked <= 2 else 1 if leaked <= n // 4 else 2
    return options, idx


def _opts_frozen(base: dict) -> tuple[list[str], int]:
    total = base.get("metrics", {}).get("total_ms", 0)
    options = [
        "About 40 ms. They all wait in parallel; that is what async is for.",
        "About 200 ms. A few requests at a time.",
        "About 1.6 seconds. One after another, as if async did not exist.",
        "Never. The event loop has gone on a lunch break.",
    ]
    idx = 0 if total < 100 else 1 if total < 600 else 2
    return options, idx


def _opts_stampede(base: dict) -> tuple[list[str], int]:
    q = base.get("metrics", {}).get("queries", 0)
    options = [
        "One query. The database is smart.",
        "21 queries: the orders, then one per customer.",
        "201 queries: the orders, then one per order.",
        "Zero. The database reads my mind.",
    ]
    idx = 0 if q <= 2 else 1 if q <= 40 else 2
    return options, idx


def _opts_silent(base: dict) -> tuple[list[str], int]:
    m = base.get("metrics", {})
    options = [
        "Some customers wait over a second, and a few are charged a wrong total without any error.",
        "A few checkouts fail loudly with an error the customer can see.",
        "Nothing visible. The client copes with it.",
        "The pricing service shows up in person to apologize.",
    ]
    if m.get("silent_wrong", 0) > 0:
        idx = 0
    elif m.get("raised", 0) > 0:
        idx = 1
    else:
        idx = 2
    return options, idx


def _opts_tangle(base: dict) -> tuple[list[str], int]:
    n = base.get("metrics", {}).get("modules_loaded", 0)
    options = [
        "One: billing itself.",
        "Two or three: billing and its helpers.",
        "Five: nearly the whole shop, mailer included.",
        "All of them, plus my lunch order.",
    ]
    idx = 0 if n <= 1 else 1 if n <= 3 else 2
    return options, idx


# ---------------------------------------------------------------------------
# Evidence: accepted lines come from the analyzers, not from the script
# ---------------------------------------------------------------------------

def _ev_leaks(a: RepoAnalysis, root: str) -> Evidence:
    path = _abs(root, "reports.py")
    best: set[int] = set()
    ok: set[int] = set()
    wrong: dict[int, str] = {}
    for leak in a.leaks:
        if os.path.abspath(leak.file) == os.path.abspath(path):
            best.add(leak.open_line)
            ok.update(leak.raise_lines)
            for c in leak.close_lines:
                wrong[c] = "The close is right there. But does it run on every path?"
    return Evidence("reports.py", best, ok, wrong)


def _ev_frozen(a: RepoAnalysis, root: str) -> Evidence:
    best: set[int] = set()
    ok: set[int] = set()
    for chain in a.blocking:
        for link in chain.links:
            if os.path.basename(link.file) != "profiles.py":
                continue
            if link is chain.links[-1]:
                best.add(link.line)
            else:
                ok.add(link.line)
    return Evidence("profiles.py", best, ok - best, {})


def _ev_stampede(a: RepoAnalysis, root: str) -> Evidence:
    best: set[int] = set()
    ok: set[int] = set()
    for loop in a.loops:
        if os.path.basename(loop.func.file) != "orders.py":
            continue
        best.add(loop.call.line)
        ok.add(loop.loop_line)
        ok.update(link.line for link in loop.links[1:])
    return Evidence("orders.py", best, ok - best, {})


def _ev_silent(a: RepoAnalysis, root: str) -> Evidence:
    path = _abs(root, "upstream.py")
    best: set[int] = set()
    ok: set[int] = set()
    try:
        with open(path) as fh:
            tree = ast.parse(fh.read())
    except (OSError, SyntaxError):
        return Evidence("upstream.py", best, ok)
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            broad = node.type is None or (isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"))
            swallows = not any(isinstance(n, ast.Raise) for n in ast.walk(node))
            if broad and swallows:
                best.add(node.lineno)
                for stmt in node.body:
                    if isinstance(stmt, ast.Return):
                        best.add(stmt.lineno)
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "urlopen":
            if not any(k.arg == "timeout" for k in node.keywords):
                ok.add(node.lineno)
    return Evidence("upstream.py", best, ok - best, {})


def _ev_tangle(a: RepoAnalysis, root: str) -> Evidence:
    best: set[int] = set()
    ok: set[int] = set()
    for e in a.arch.cycle_edges:
        if e.src == "shop.billing":
            best.add(e.line)
        elif e.src == "shop.orders":
            ok.add(e.line)
    return Evidence("shop/billing.py", best, ok, {})


# ---------------------------------------------------------------------------
# The chapters
# ---------------------------------------------------------------------------

CHAPTERS: list[Chapter] = [
    Chapter(
        id=1,
        slug="leaks",
        title="The Leaking Lab",
        concept="resource_lifetimes",
        concept_title="Resource lifetimes",
        attribute=AttributeType.STAMINA,
        workload="stamina",
        files=["reports.py"],
        focus_file="reports.py",
        question=(
            "The dashboard loads 400 reports. One in twenty is a truncated upload, and the error "
            "tracker keeps every failed request for its error page. When it is over, how many file "
            "descriptors are still open?"
        ),
        build_options=_opts_leaks,
        evidence_prompt="Present the line where the leak begins.",
        find_evidence=_ev_leaks,
        explain_prompt="Explain it to me. Why do those files stay open, and only those?",
        rubric=[
            KeyIdea("exception", "A malformed report makes json.load raise",
                    [r"exception", r"rais", r"\berror", r"malformed", r"truncat", r"bad (json|input|report|file)", r"invalid", r"throw"],
                    "What does json.load do with a truncated report?"),
            KeyIdea("skip", "The exception jumps over f.close()",
                    [r"skip", r"never (reach|run|get|call)", r"not (reached|run|called|executed)", r"bypass", r"jump",
                     r"before (the )?clos", r"doesn'?t (reach|run|get to|call)", r"close (is )?never", r"never clos"],
                    "When json.load raises, does the next line still run?"),
            KeyIdea("retained", "The stored traceback keeps the frame, and the file, alive",
                    [r"traceback", r"frame", r"stor(e|ed|ing)", r"\bkept\b", r"\bkeep", r"referenc", r"hold", r"alive",
                     r"tracker", r"failures", r"exc_info", r"garbage"],
                    "Python usually cleans up a dropped file. What is still pointing at this one?"),
            KeyIdea("fix", "A with block (or try/finally) closes it on every path",
                    [r"\bwith\b", r"context manager", r"finally"],
                    "Which construct guarantees the close on every path out?"),
        ],
        hints={
            "predict": ["Look at what happens between open and close when the JSON is bad."],
            "evidence": ["It is not the close. Find where the handle is born without a guardian.",
                         "Line six creates the handle. Nothing protects it from the exception on line seven."],
            "explain": ["Think about exceptions, the skipped close, and what the error tracker is holding on to."],
        },
        fixes=[
            FixOption("A", "Open it in a with block", "with open(path) as f: return json.load(f)", "best",
                      "The context manager closes the file on every path out, including the exceptional one. Zero leaks."),
            FixOption("B", "try / finally: f.close()", "Keep open(), close it in a finally block", "good",
                      "Correct and leak-free. It is what with does for you, only longer and easier to get wrong."),
            FixOption("C", "Call gc.collect() after each load", "Force the garbage collector to sweep leftovers", "wrong",
                      "The collector cannot free a file the error tracker still references, so the leak stays, and every request is now about a hundred times slower. Treating the symptom costs you and cures nothing."),
        ],
        intro=[
            "Kukuku… welcome to the first experiment, Morumotto-kun.",
            "This dashboard has run for weeks without complaint. Then one night it died with 'too many open files'.",
            "Before I show you anything: make a prediction.",
        ],
        reveal_right="Correct. You smelled it before I showed you.",
        reveal_wrong="Wrong. Look at the chart: the line climbs every time a bad report arrives.",
        reveal_certain_wrong="You were certain, and certainly wrong! Magnificent. That surprise is exactly how memory is made.",
        evidence_right="Objection sustained! That is where the handle is born with no guardian.",
        evidence_wrong="Hmm, no. That line is innocent. Look again.",
        fix_prompt="Now choose the treatment. I will apply it and measure again.",
        outro=["Resource lifetimes: whoever opens a thing must guarantee it closes, on every path out."],
        lore_title="Journal 01: Why a lab",
        lore=("I did not build this lab to teach. I built it because every system I admired died of something "
              "small that nobody measured. A leak here, a stall there. I want to see the failure before it happens."),
        takeaway="Tie every resource to a scope: with blocks close on every path, including exceptions.",
    ),
    Chapter(
        id=2,
        slug="frozen",
        title="The Frozen Loop",
        concept="event_loop_blocking",
        concept_title="Blocking the event loop",
        attribute=AttributeType.SPEED,
        workload="speed",
        files=["profiles.py"],
        focus_file="profiles.py",
        question=(
            "Forty requests hit the async API at the same moment. Each one waits about 40 milliseconds "
            "for the profile service. When does the last request get its answer?"
        ),
        build_options=_opts_frozen,
        evidence_prompt="Present the line that freezes the event loop.",
        find_evidence=_ev_frozen,
        explain_prompt="Explain it. The handler is async, so why does everyone wait in line?",
        rubric=[
            KeyIdea("one_thread", "One event loop runs every request on a single thread",
                    [r"event loop", r"single[- ]?thread", r"one thread", r"one loop", r"single loop", r"same thread"],
                    "How many threads does the event loop use to run all forty requests?"),
            KeyIdea("blocking", "time.sleep is a blocking call that holds that thread",
                    [r"block", r"freez", r"stall", r"synchronous", r"\bsync\b", r"sleep", r"hold(s)? the"],
                    "What does time.sleep do to the thread that calls it?"),
            KeyIdea("yield", "Only await hands control back to the loop; async alone does not",
                    [r"await", r"yield", r"cooperat", r"control back", r"give(s)? (back )?control", r"let (the )?(loop|others)",
                     r"hand(s)? (back|over)", r"switch"],
                    "Where in this chain could the loop switch to another request?"),
            KeyIdea("fix", "Use an async client, or offload the blocking call to a thread",
                    [r"to_thread", r"to thread", r"thread ?pool", r"executor", r"async (http )?client", r"asyncio\.?sleep",
                     r"non[- ]?blocking", r"offload", r"(in|on) a (separate |worker )?thread", r"aiohttp", r"httpx"],
                    "How could the sleep happen without holding the loop?"),
        ],
        hints={
            "predict": ["An async handler is only as concurrent as the code it calls."],
            "evidence": ["Follow the calls: handle_request calls enrich, enrich calls fetch_profile…",
                         "The culprit never says async. It is the line that sleeps."],
            "explain": ["Single thread, blocking sleep, and where an await would have let the loop move on."],
        },
        fixes=[
            FixOption("A", "await asyncio.to_thread(enrich, user_id)", "Run the blocking chain in a worker thread", "good",
                      "Much better: the loop is free. But the thread pool has only a handful of workers, so requests still queue in batches."),
            FixOption("B", "Make enrich async def", "async def enrich(...), and await it", "wrong",
                      "Nothing changed. The async keyword does not make time.sleep cooperative. The sleep still holds the only thread."),
            FixOption("C", "Wrap it in asyncio.wait_for(timeout=0.1)", "Give each request a deadline", "wrong",
                      "The timeout never fires. A timer needs the loop to run, and the loop is stuck inside time.sleep."),
            FixOption("D", "Async client all the way down", "fetch_profile awaits a non-blocking call", "best",
                      "All forty in about forty milliseconds. When every wait is an await, the loop overlaps them all."),
        ],
        intro=[
            "Experiment two. The API went async last sprint and everyone celebrated.",
            "Then the first traffic spike arrived and latency went through the roof.",
            "Predict first. What does forty at once look like?",
        ],
        reveal_right="Correct. Async is a promise that only await can keep.",
        reveal_wrong="Look at the lag line. The heartbeat could not run for a second and a half.",
        reveal_certain_wrong="Certain and wrong! The async keyword fooled you. Remember this feeling.",
        evidence_right="Objection sustained! A synchronous sleep, three calls deep, holding the only thread.",
        evidence_wrong="That line is only a messenger. Follow the call further down.",
        fix_prompt="Choose the treatment. Some of these only look like cures.",
        outro=["An event loop is a single thread taking turns. Anything that blocks steals every turn."],
        lore_title="Journal 02: Speed",
        lore=("They call me obsessed with speed. Wrong. I am obsessed with the limit: the point where a system "
              "stops scaling. You only find it by pushing until something freezes."),
        takeaway="Never block the loop: use async clients, or push blocking work to threads.",
    ),
    Chapter(
        id=3,
        slug="stampede",
        title="The Stampede",
        concept="n_plus_one",
        concept_title="Round trips in loops (N+1)",
        attribute=AttributeType.POWER,
        workload="power",
        files=["orders.py"],
        focus_file="orders.py",
        question=(
            "The order history page shows 200 orders from 20 customers. The database is a network hop "
            "away. How many queries does one page render send?"
        ),
        build_options=_opts_stampede,
        evidence_prompt="Present the line that sends the stampede.",
        find_evidence=_ev_stampede,
        explain_prompt="Explain it. Every query is fast. So why is the page slow?",
        rubric=[
            KeyIdea("per_row", "One query per order, inside the loop",
                    [r"per (row|order|item|iteration|customer)", r"each (order|row|item|iteration)", r"inside (the )?loop",
                     r"in (a|the) loop", r"n ?\+ ?1", r"n plus one", r"200", r"two hundred", r"every order", r"for each"],
                    "How many times does get_customer run for one page?"),
            KeyIdea("roundtrip", "Each query pays a network round trip; latency adds up",
                    [r"round[- ]?trip", r"network", r"latenc", r"\brtt\b", r"hop", r"adds? up", r"trip", r"overhead"],
                    "If each query is fast, where does the time go?"),
            KeyIdea("batch", "Fetch everything in one query: a JOIN or WHERE id IN (...)",
                    [r"\bjoin\b", r"\bin ?\(", r"where .* in", r"batch", r"single query", r"one query", r"bulk", r"prefetch",
                     r"eager", r"all at once", r"together"],
                    "How could one query bring the customers along with the orders?"),
        ],
        hints={
            "predict": ["Count how often the loop body runs, and what it calls."],
            "evidence": ["The query is hidden in a helper. Who calls it, and from where?"],
            "explain": ["Per-iteration query, round-trip cost, and batching."],
        },
        fixes=[
            FixOption("A", "One JOIN query", "SELECT orders JOIN customers in a single round trip", "best",
                      "One round trip for the whole page. The database is good at joins; the network is bad at chatter."),
            FixOption("B", "Add an index on customers.id", "Make each lookup faster", "wrong",
                      "One more query, not fewer. The id is already the primary key. Indexes speed up each query; they do not remove round trips."),
            FixOption("C", "lru_cache on get_customer", "Remember customers we already fetched", "partial",
                      "Twenty-one queries: one per distinct customer. Better, but the cache holds a reference to the connection and serves stale names forever. The query shape is still wrong."),
        ],
        intro=[
            "Experiment three. The order page loads in one second on a good day.",
            "The database team swears every query takes under a millisecond. Both statements are true.",
            "Predict how many times we knock on the database's door.",
        ],
        reveal_right="Exactly. You counted the knocks.",
        reveal_wrong="See the staircase? Every step is one more trip to the database.",
        reveal_certain_wrong="So certain! And the database got two hundred and one visits. Delicious.",
        evidence_right="Objection sustained! A query hidden inside a helper, called once per order.",
        evidence_wrong="Not that one. Find the call that runs once per order.",
        fix_prompt="Pick the treatment. One of them only makes each knock quieter.",
        outro=["Chatty beats slow: count round trips, not milliseconds per query."],
        lore_title="Journal 03: Power",
        lore=("Power is not doing more work. It is doing the same work in fewer trips. "
              "The fastest request is the one you never send."),
        takeaway="Queries inside loops multiply round trips; fetch in batches or with joins.",
    ),
    Chapter(
        id=4,
        slug="silent",
        title="Silent Failure",
        concept="failure_isolation",
        concept_title="Timeouts and honest failures",
        attribute=AttributeType.GUTS,
        workload="guts",
        files=["upstream.py"],
        focus_file="upstream.py",
        question=(
            "The pricing service is having a bad day: one call in ten hangs, one in ten returns an error. "
            "Forty customers check out. What happens?"
        ),
        build_options=_opts_silent,
        evidence_prompt="Present the line that hides the failure.",
        find_evidence=_ev_silent,
        explain_prompt="Explain it. How does a checkout end up charging the wrong amount without any error?",
        rubric=[
            KeyIdea("hang", "No timeout: a hung upstream makes the customer wait",
                    [r"timeout", r"time out", r"hang", r"wait(s|ing)? forever", r"stuck", r"deadline", r"wait(s|ing)?"],
                    "What stops a request that never answers?"),
            KeyIdea("swallow", "The bare except turns errors into None, and None into a price of zero",
                    [r"swallow", r"silent", r"hid(e|es|den|ing)", r"bare except", r"except", r"\bnone\b", r"\bzero\b", r"wrong total",
                     r"corrupt", r"mask", r"ignor"],
                    "What does fetch_price return when the service fails, and what does cart_total do with it?"),
            KeyIdea("resilience", "Time out, retry with backoff, and fail loudly when it still fails",
                    [r"retr(y|ies)", r"backoff", r"back off", r"fail fast", r"circuit breaker", r"\braise", r"propagat",
                     r"explicit", r"surface", r"loud"],
                    "If the price really is unavailable, what should the checkout do instead of guessing?"),
        ],
        hints={
            "predict": ["Two problems: waiting too long, and lying when it fails."],
            "evidence": ["Which line turns an explosion into a quiet None?"],
            "explain": ["No timeout, a swallowed exception, and what an honest failure looks like."],
        },
        fixes=[
            FixOption("A", "Timeout, retry with backoff, raise", "timeout=0.25, two retries, raise PricingUnavailable", "best",
                      "Every checkout correct, p99 down from over a second. Fast retries absorb the flakiness, and if pricing is truly down you get an honest error, never a wrong charge."),
            FixOption("B", "Log the error and return 0", "except Exception: log it, return 0", "wrong",
                      "Now you have logs of your wrong totals. The customer is still charged the wrong amount, and still waits for the hung calls."),
            FixOption("C", "Add timeout=0.25", "Just stop waiting on hung calls", "wrong",
                      "Faster, and worse: the timeouts are swallowed too, so more customers get a wrong total. A timeout without an honest failure path just fails faster, in silence."),
        ],
        intro=[
            "Experiment four. Finance found checkouts that charged less than the cart.",
            "No errors in the logs. No alerts. The most dangerous kind of failure.",
            "Predict what forty customers experience while pricing misbehaves.",
        ],
        reveal_right="Yes. Slow, and quietly wrong. The worst combination.",
        reveal_wrong="Look at the flags: those checkouts succeeded with the wrong total, and nobody was told.",
        reveal_certain_wrong="Certain and wrong. Silent failures fool everyone. That is the whole point of them.",
        evidence_right="Objection sustained! The bare except, where errors go to disappear.",
        evidence_wrong="That line is suspicious, but it is not where the truth is buried.",
        fix_prompt="Choose the treatment. Beware: one of these makes the numbers look better and the truth worse.",
        outro=["Bound every wait, retry what is transient, and fail loudly on what is not."],
        lore_title="Journal 04: Guts",
        lore=("Courage in a system is saying 'I failed' out loud. A service that hides its failures "
              "is not brave. It is a liar with good uptime."),
        takeaway="Put deadlines on every remote call and never turn an error into a plausible value.",
    ),
    Chapter(
        id=5,
        slug="tangle",
        title="The Tangle",
        concept="dependency_direction",
        concept_title="Dependency direction",
        attribute=AttributeType.WISDOM,
        workload="wisdom",
        files=["shop"],
        focus_file="shop/billing.py",
        question=(
            "You want a unit test for billing.charge(). Nothing else. "
            "How many shop modules does Python load to run it?"
        ),
        build_options=_opts_tangle,
        evidence_prompt="Present the import that closes the cycle.",
        find_evidence=_ev_tangle,
        explain_prompt="Explain it. Why does testing billing drag in the mailer?",
        rubric=[
            KeyIdea("cycle", "billing and orders import each other: a cycle",
                    [r"cycl", r"circular", r"each other", r"both import", r"mutual", r"one another", r"back and forth"],
                    "Who does billing import, and who imports billing?"),
            KeyIdea("drag", "Imports are transitive: orders pulls in notifications, which pulls in the mailer",
                    [r"drag", r"pull", r"load", r"transitiv", r"mailer", r"notification", r"whole shop", r"everything",
                     r"side effect", r"chain", r"cascade", r"ripple"],
                    "When billing imports orders, what does orders import in turn?"),
            KeyIdea("direction", "Point dependencies at a small stable module: extract the pricing logic",
                    [r"direction", r"abstraction", r"extract", r"shared module", r"\bpure\b", r"invert", r"interface",
                     r"stable", r"lower[- ]level", r"pricing", r"separate module", r"move .*(out|into)"],
                    "What does billing actually need from orders? Could that live somewhere smaller?"),
        ],
        hints={
            "predict": ["Follow the imports from billing, then the imports of those."],
            "evidence": ["Billing is the low-level module. Which of its imports points up?"],
            "explain": ["A cycle, transitive loading, and which way dependencies should point."],
        },
        fixes=[
            FixOption("A", "Extract pricing.py", "Move order_total into a pure module both can use", "best",
                      "Cycle gone, and billing now loads three small modules instead of five. Dependencies point toward the stable, pure code."),
            FixOption("B", "Import orders inside charge()", "A lazy import to break the cycle", "wrong",
                      "The import got faster and the test did not: calling charge still drags in the mailer. The graph still has the cycle; you only hid it inside a function."),
            FixOption("C", "Merge billing into orders", "One module, no cycle", "partial",
                      "No cycle, but testing charge still loads the mailer, and orders is now a bigger module that everyone must touch. You removed the symptom by growing the tangle."),
        ],
        intro=[
            "Final experiment. The shop's tests take forever and fail when the mail server is down.",
            "Nobody touched the mailer. They were testing billing.",
            "Predict how much of the shop one small test drags in.",
        ],
        reveal_right="Correct. You read the graph in your head.",
        reveal_wrong="See the graph: one cycle, and the whole neighborhood comes along for the ride.",
        reveal_certain_wrong="Certain and wrong! The cycle hid the mailer from you. Remember its face.",
        evidence_right="Objection sustained! The low-level module importing the high-level one.",
        evidence_wrong="That import is fine. Find the one pointing the wrong way.",
        fix_prompt="Choose the treatment. The graph will not lie to either of us.",
        outro=["Depend toward stability: the code that changes least should know the least."],
        lore_title="Journal 05: Wisdom",
        lore=("Wisdom is knowing what not to know. My best modules are ignorant on purpose: "
              "they know nothing of the modules that depend on them. That ignorance is what lets them last."),
        takeaway="Keep dependencies acyclic and pointing toward small, stable modules.",
    ),
]

CHAPTER_BY_ID = {c.id: c for c in CHAPTERS}
CHAPTER_BY_ATTR = {c.attribute: c for c in CHAPTERS}
CHAPTER_BY_CONCEPT = {c.concept: c for c in CHAPTERS}


def fix_dir(chapter: Chapter, key: str) -> str:
    return os.path.join(FIXES_DIR, chapter.slug, key)
