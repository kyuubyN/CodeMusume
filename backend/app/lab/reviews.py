"""Transfer questions for spaced review and Derby checkpoints.

Each question shows *new* code that hides a concept learned in a chapter, so
answering it means recognising the idea, not recalling the specimen.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewQuestion:
    id: str
    concept: str
    prompt: str
    code: str
    options: tuple[str, ...]
    correct: int
    explanation: str


REVIEW_BANK: list[ReviewQuestion] = [
    # --- resource lifetimes ---------------------------------------------------
    ReviewQuestion(
        "rl-1", "resource_lifetimes",
        "A worker processes uploads. What goes wrong when parse() raises?",
        "def handle(path):\n    conn = db.connect()\n    rows = parse(path)\n    conn.insert(rows)\n    conn.close()",
        ("Nothing, the connection closes when handle returns.",
         "The connection stays open: the exception skips conn.close().",
         "parse() closes the connection for us.",
         "The database rolls its eyes and closes it."),
        1,
        "The exception jumps over conn.close(). Use with db.connect() as conn: so the close runs on every path.",
    ),
    ReviewQuestion(
        "rl-2", "resource_lifetimes",
        "Which version is guaranteed to release the lock even if work() raises?",
        "lock.acquire()\nwork()\nlock.release()",
        ("Add lock.release() at the top of the function too.",
         "Call gc.collect() after work().",
         "with lock:\n    work()",
         "Ask the lock nicely."),
        2,
        "A context manager releases on every exit path. gc.collect() cannot release something still referenced.",
    ),
    # --- event loop blocking --------------------------------------------------
    ReviewQuestion(
        "el-1", "event_loop_blocking",
        "This FastAPI endpoint is async. What happens with 50 simultaneous calls?",
        "@app.get('/weather')\nasync def weather(city: str):\n    r = requests.get(API, params={'q': city})\n    return r.json()",
        ("They overlap nicely; the endpoint is async.",
         "They run one after another: requests.get blocks the event loop.",
         "FastAPI automatically moves requests.get to a thread.",
         "The weather changes."),
        1,
        "requests is synchronous. Inside an async def it blocks the loop. Use an async client (httpx.AsyncClient) or a plain def endpoint, which FastAPI runs in a thread pool.",
    ),
    ReviewQuestion(
        "el-2", "event_loop_blocking",
        "Which change actually lets other requests run during the hash?",
        "async def signup(pw):\n    digest = bcrypt.hashpw(pw, salt)  # ~300 ms of CPU\n    return await save(digest)",
        ("Mark bcrypt.hashpw with async.",
         "Wrap it: await asyncio.wait_for(..., timeout=1).",
         "digest = await asyncio.to_thread(bcrypt.hashpw, pw, salt)",
         "Hash the password more gently."),
        2,
        "Offloading to a thread frees the loop. A timeout cannot interrupt code that never yields.",
    ),
    # --- N+1 ------------------------------------------------------------------
    ReviewQuestion(
        "np-1", "n_plus_one",
        "A template shows 50 posts with their author. How many queries does this ORM code send?",
        "posts = Post.objects.all()[:50]\nfor p in posts:\n    print(p.title, p.author.name)",
        ("1", "2", "51", "Depends on the moon."),
        2,
        "One for the posts, then one per author access: 51. select_related('author') makes it one JOIN.",
    ),
    ReviewQuestion(
        "np-2", "n_plus_one",
        "Which fix removes the round trips instead of just shrinking them?",
        "for user_id in ids:\n    user = api.get(f'/users/{user_id}')",
        ("Add an index on users.id.",
         "Use a faster network card.",
         "One batched call: api.get('/users', params={'ids': ids})",
         "Pray."),
        2,
        "Batching turns N round trips into one. Indexes and hardware make each trip cheaper but keep all N.",
    ),
    # --- failure isolation ----------------------------------------------------
    ReviewQuestion(
        "fi-1", "failure_isolation",
        "What is wrong with this inventory check?",
        "def in_stock(sku):\n    try:\n        return http.get(f'{INV}/{sku}').json()['qty'] > 0\n    except Exception:\n        return True",
        ("Nothing, it degrades gracefully.",
         "No timeout, and on failure it silently claims the item is in stock.",
         "It should catch BaseException too.",
         "Inventory should be stored in a spreadsheet."),
        1,
        "It waits without a deadline and turns an outage into a lie. Add a timeout, retry what is transient, and surface the failure.",
    ),
    ReviewQuestion(
        "fi-2", "failure_isolation",
        "Adding only timeout=0.2 to a call inside a bare except. What happens during an outage?",
        "try:\n    price = fetch(sku, timeout=0.2)\nexcept:\n    price = None",
        ("Checkouts fail loudly and quickly.",
         "Checkouts get faster and more of them silently use a missing price.",
         "The timeout retries automatically.",
         "The outage is shortened."),
        1,
        "The timeout converts hangs into exceptions, and the bare except converts those into silent None. Faster, and more wrong.",
    ),
    # --- dependency direction ---------------------------------------------------
    ReviewQuestion(
        "dd-1", "dependency_direction",
        "users.py imports auth.py, and auth.py imports users.py for one helper. Best fix?",
        "# users.py\nfrom app import auth\n# auth.py\nfrom app import users  # for users.normalize_email",
        ("Move the import in auth.py inside a function.",
         "Move normalize_email into a small module both can import.",
         "Merge users and auth into one module.",
         "Rename users.py to people.py."),
        1,
        "Extract the shared piece into a module that depends on neither. A lazy import only hides the cycle.",
    ),
    ReviewQuestion(
        "dd-2", "dependency_direction",
        "Why is a module with high blast radius a risk?",
        "# utils.py is imported, directly or not, by 40 of 45 modules",
        ("It makes imports slower, nothing else.",
         "Any change to it may break, and needs retesting across, most of the codebase.",
         "It means the code is well reused, which is always good.",
         "It emits radiation."),
        1,
        "Blast radius measures who depends on you. Keep widely depended-on modules small and stable.",
    ),
]

BY_CONCEPT: dict[str, list[ReviewQuestion]] = {}
for _q in REVIEW_BANK:
    BY_CONCEPT.setdefault(_q.concept, []).append(_q)
BY_ID = {q.id: q for q in REVIEW_BANK}
