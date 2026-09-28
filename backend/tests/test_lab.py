"""The lab: analyzers, harness, experiments, reviews, Derby and persistence."""
from __future__ import annotations

import asyncio
import os
import shutil

import pytest
from fastapi.testclient import TestClient

from app.lab.analysis import analyze_repo
from app.lab.analysis.dataflow import analyze_source
from app.lab.chapters import BASE_DIR, CHAPTER_BY_ID
from app.lab.game import LabError, LabGame
from app.lab.grader import grade
from app.lab.harness.runner import run_workload
from app.lab.profile import ProfileStore
from app.lab.trainee import Trainee
from app.main import app
from app.services.trainer_service import TrainerEngine


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Static analysis, from scratch
# ---------------------------------------------------------------------------

class TestDataflow:
    def test_exception_path_leak(self):
        src = "def f(p):\n    h = open(p)\n    data = json.load(h)\n    h.close()\n    return data\n"
        (leak,) = analyze_source(src)
        assert leak.kind == "exception_path"
        assert leak.open_line == 2 and leak.raise_lines == [3] and leak.close_lines == [4]

    def test_with_and_finally_are_clean(self):
        assert analyze_source("def f(p):\n    with open(p) as h:\n        return h.read()\n") == []
        src = "def f(p):\n    h = open(p)\n    try:\n        return h.read()\n    finally:\n        h.close()\n"
        assert analyze_source(src) == []

    def test_normal_path_leak_and_escape(self):
        (leak,) = analyze_source("def f(p):\n    h = open(p)\n    return h.read()\n")
        assert leak.kind == "normal_path"
        assert analyze_source("def f(p):\n    h = open(p)\n    return h\n") == []
        assert analyze_source("def f(self, p):\n    c = sqlite3.connect(p)\n    self.c = c\n") == []

    def test_loop_with_continue_skipping_close(self):
        src = "def f(ps):\n    for p in ps:\n        h = open(p)\n        if not p:\n            continue\n        h.close()\n"
        assert [l.kind for l in analyze_source(src)] == ["normal_path"]


class TestWholeProgram:
    def test_specimen_findings(self):
        a = analyze_repo(BASE_DIR)
        (chain,) = [c for c in a.blocking if c.root.name == "handle_request"]
        assert [l.callee for l in chain.links] == ["profiles.enrich", "profiles.fetch_profile", "time.sleep"]
        loops = {os.path.basename(r.func.file) for r in a.loops}
        assert "orders.py" in loops
        assert a.arch.cycles == [["shop.billing", "shop.orders"]]
        assert a.arch.hidden_cycles == []

    def test_offloading_breaks_the_chain_but_async_keyword_does_not(self, tmp_path):
        ch = CHAPTER_BY_ID[2]
        t = Trainee(str(tmp_path / "t"))
        t.reset()
        t.apply(ch, "A")
        assert not [c for c in analyze_repo(t.root).blocking if "profiles" in c.root.qual]
        t.apply(ch, "B")
        assert [c for c in analyze_repo(t.root).blocking if "profiles" in c.root.qual]

    def test_lazy_import_hides_the_cycle(self, tmp_path):
        ch = CHAPTER_BY_ID[5]
        t = Trainee(str(tmp_path / "t"))
        t.reset()
        t.apply(ch, "B")
        a = analyze_repo(t.root)
        assert a.arch.cycles and a.arch.hidden_cycles
        t.apply(ch, "A")
        assert analyze_repo(t.root).arch.cycles == []
        assert os.path.exists(os.path.join(t.root, "shop", "pricing.py"))
        t.revert(ch)
        assert not os.path.exists(os.path.join(t.root, "shop", "pricing.py"))


# ---------------------------------------------------------------------------
# Measurement harness
# ---------------------------------------------------------------------------

class TestHarness:
    def test_leak_is_measured_and_gc_does_not_fix_it(self, tmp_path):
        ch = CHAPTER_BY_ID[1]
        t = Trainee(str(tmp_path / "t"))
        t.reset()
        base = run_workload("stamina", t.root, use_cache=False)
        assert base["metrics"]["leaked_fds"] == base["metrics"]["bad_requests"] == 20
        t.apply(ch, "C")
        assert run_workload("stamina", t.root, use_cache=False)["metrics"]["leaked_fds"] == 20
        t.apply(ch, "A")
        assert run_workload("stamina", t.root, use_cache=False)["metrics"]["leaked_fds"] == 0

    def test_n_plus_one_is_counted(self, tmp_path):
        ch = CHAPTER_BY_ID[3]
        t = Trainee(str(tmp_path / "t"))
        t.reset()
        assert run_workload("power", t.root, use_cache=False)["metrics"]["queries"] == 201
        t.apply(ch, "C")
        assert run_workload("power", t.root, use_cache=False)["metrics"]["queries"] == 21
        t.apply(ch, "A")
        m = run_workload("power", t.root, use_cache=False)["metrics"]
        assert m["queries"] == 1 and m["correct"]

    def test_broken_trainee_reports_error_instead_of_crashing(self, tmp_path):
        root = tmp_path / "t"
        shutil.copytree(BASE_DIR, root)
        (root / "orders.py").write_text("def render_orders(conn):\n    raise RuntimeError('boom')\n")
        out = run_workload("power", str(root), use_cache=False)
        assert "RuntimeError" in out["error"]


# ---------------------------------------------------------------------------
# Grader
# ---------------------------------------------------------------------------

def test_grader_hears_spoken_explanations():
    rubric = CHAPTER_BY_ID[2].rubric
    g = grade("The event loop is one thread and time dot sleep blocks it, nothing awaits", rubric)
    assert set(g.hits) >= {"one_thread", "blocking", "yield"}
    assert g.missed == ["fix"] and g.follow_up
    g2 = grade("so use asyncio to_thread", rubric, set(g.hits))
    assert g2.score == 1.0


# ---------------------------------------------------------------------------
# A full career
# ---------------------------------------------------------------------------

@pytest.fixture
def lab(tmp_path) -> LabGame:
    return LabGame(str(tmp_path / "lab"))


@pytest.fixture
def engine(lab) -> TrainerEngine:
    return TrainerEngine(run(lab.start_career(fresh=True)))


def test_career_starts_with_measured_stats(lab, engine):
    st = engine.state
    assert st.mode == "lab" and st.turn == 1 and st.max_turns == 12
    assert all(v < 400 for v in st.attributes.model_dump().values())  # the specimen is sick
    view = lab.public_state()
    assert [c["status"] for c in view["chapters"]] == ["open"] * 5
    assert view["chapters"][0]["measure"]["value"] == 20


def test_full_experiment_loop(lab, engine, tmp_path):
    result, ui = run(lab.start_experiment(engine, 1))
    assert ui["panel"] == "experiment" and len(result["options"]) == 4
    assert engine.state.energy == 80
    view = lab.public_state()["experiment"]
    assert view["correct_index"] is None and view["baseline"] is None  # no spoilers before predicting

    with pytest.raises(LabError):
        lab.present_evidence(engine, 6)  # wrong step

    res, _ = lab.submit_prediction(engine, "B", "certain")
    assert res["correct"] and res["measured"].startswith("File descriptors")
    assert lab.profile.certain_right == 1

    res, ui = lab.present_evidence(engine, 8)  # the close() line: tempting, wrong
    assert not res["accepted"] and "close" in ui["script"][0].lower()
    res, _ = lab.present_evidence(engine, 6)
    assert res["accepted"] and res["quality"] == "best"

    res, _ = lab.submit_explanation(engine, "json load raises on bad input so it never reaches close")
    assert res["follow_up"] and lab.experiment.stage == "explain"
    res, _ = lab.submit_explanation(engine, "the stored traceback keeps the frame alive; use a with block")
    assert res["score"] == 1.0 and lab.experiment.stage == "fix"

    res, _ = run(lab.choose_fix(engine, "C"))
    assert res["verdict"] == "wrong" and "leaks" in res["static_analysis"]
    res, _ = run(lab.choose_fix(engine, "A"))
    assert res["verdict"] == "best" and res["after"].startswith("0")
    assert res["stat_after"] > res["stat_before"]

    res, ui = lab.keep_fix(engine)
    assert res["score"] > 60 and res["lore"]
    assert engine.state.turn == 2
    assert lab.profile.concept("resource_lifetimes").mastery == res["score"]
    assert lab.public_state()["chapters"][0]["status"] == "cleared"

    # it survives a restart
    again = LabGame(lab.data_dir)
    assert again.profile.chapters_cleared == [1]
    resumed = run(again.start_career())
    assert resumed.turn == 2 and resumed.attributes.stamina == engine.state.attributes.stamina


def test_review_comes_due_and_moves_leitner_box(lab, engine):
    with pytest.raises(LabError):
        lab.start_review(engine)  # nothing studied yet
    lab.profile.concept("n_plus_one").box = 1
    lab.profile.concept("n_plus_one").due_day = lab.profile.lab_day
    res, _ = lab.start_review(engine)
    assert res["concept"] == "n_plus_one"
    q = lab.review.question
    res, _ = lab.answer_review(engine, "ABCD"[q.correct])
    assert res["correct"]
    rec = lab.profile.concept("n_plus_one")
    assert rec.box == 2 and rec.due_day == lab.profile.lab_day + 2


def test_derby_and_legacy(lab, engine):
    lab.profile.chapters_cleared = [1, 2, 3]
    lab.profile.chapter_scores = {"1": 96, "2": 70, "3": 40}
    engine.state = lab._sync(engine)
    assert engine.state.race_unlocked
    qs = lab.derby_questions()
    assert len(qs) == 3 and len({q.concept for q in qs}) == 3
    out = lab.answer_checkpoint(qs[0].id, qs[0].correct)
    assert out["correct"]
    summary = lab.complete_career(engine, place=1, checkpoint_score=2)
    assert summary["sparks_earned"] == {"resource_lifetimes": 3, "event_loop_blocking": 1}
    assert lab.profile.career == 2 and lab.profile.hall[0].place == 1
    assert any(r.id == "ghost" and r.name.startswith("Ghost") for r in lab.rivals())
    assert {s["concept"] for s in lab.skills()} >= {"resource_lifetimes", "event_loop_blocking"}


# ---------------------------------------------------------------------------
# Through the API, like the voice agent does it
# ---------------------------------------------------------------------------

def test_voice_tools_drive_the_experiment(isolated_lab):
    with TestClient(app) as client:
        snap = client.post("/api/lab/career", json={"fresh": True}).json()
        assert snap["state"]["mode"] == "lab"

        def tool(name, **args):
            return client.post("/api/voice/tool", json={"name": name, "arguments": args}).json()

        assert "error" in tool("train", attribute="speed")["result"]  # free-lab only
        out = tool("start_experiment", chapter=3)
        assert out["lab"]["experiment"]["stage"] == "predict"
        assert tool("submit_prediction", option="C", confidence="likely")["result"]["correct"]
        lines = out["lab"]["experiment"]["code"]
        culprit = next(i for i, l in enumerate(lines, 1) if "get_customer(conn, customer_id)" in l and "def" not in l)
        assert tool("present_evidence", line=culprit)["result"]["accepted"]
        res = tool("submit_explanation", explanation="one query per order in the loop, each a round trip; use a join")
        assert res["result"]["score"] == 1.0
        res = tool("choose_fix", option="B")
        assert res["result"]["verdict"] == "wrong"
        res = tool("choose_fix", option="A")
        assert res["result"]["after"] == "1 queries"
        res = tool("keep_fix")
        assert res["result"]["chapter"] == 3
        assert res["lab"]["chapters"][2]["status"] == "cleared"
        assert client.post("/api/lab/close").json()["lab"]["experiment"] is None
        session = client.get("/api/voice/session").json()
        assert "experiment" in session["system_prompt"].lower()
        assert any(t["name"] == "submit_prediction" for t in session["tools"])


def test_profile_store_survives_garbage(tmp_path):
    path = tmp_path / "p.json"
    path.write_text("{not json")
    assert ProfileStore(str(path)).load().career == 1


# ---------------------------------------------------------------------------
# Free lab: whole-program checks on real-world layouts
# ---------------------------------------------------------------------------

def _write(root, files: dict[str, str]):
    for rel, src in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src)


def test_no_false_blocking_from_names_that_look_external(tmp_path):
    _write(tmp_path, {
        "requests.py": "async def handler():\n    raise RuntimeError('x')\n",
        "svc.py": "async def run(requests):\n    for k in requests.items():\n        pass\n",
    })
    a = analyze_repo(str(tmp_path))
    assert a.blocking == [] and a.loops == []


def test_real_import_is_blocking_and_package_root_resolves(tmp_path):
    pkg = tmp_path / "shop"
    _write(pkg, {
        "__init__.py": "from shop import api\n",
        "net.py": "import requests\n\ndef get(u):\n    return requests.get(u, timeout=1)\n",
        "api.py": "from shop.net import get\n\nasync def view():\n    return get('x')\n",
    })
    a = analyze_repo(str(pkg))  # the root itself is the package
    (chain,) = a.blocking
    assert chain.root.qual == "shop.api.view" and chain.primitive == "requests.get"
    assert a.arch.cycles == []  # __init__ re-exporting a submodule is a facade, not a cycle


def test_type_checking_imports_are_not_cycles_and_retry_loops_are_not_n_plus_one(tmp_path):
    _write(tmp_path, {
        "a.py": "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import b\n",
        "b.py": "import a\nimport urllib.request\n\ndef fetch(u):\n    for attempt in range(3):\n        urllib.request.urlopen(u, timeout=1)\n",
    })
    a = analyze_repo(str(tmp_path))
    assert a.arch.cycles == [] and a.loops == []


def test_standards_report_links_failures_to_chapters():
    from app.lab.standards import build_report

    rep = build_report(BASE_DIR)
    status = {c["id"]: c for c in rep["checks"]}
    assert status["acyclic"]["status"] == "fail" and status["acyclic"]["chapter"] == 5
    assert status["resources"]["status"] == "fail" and status["resources"]["evidence"][0]["file"] == "reports.py"
    assert status["event_loop"]["status"] == "fail"
    assert rep["total"] == 10 and rep["grade"] in "SABCDEF"
    assert all(120 <= v <= 1120 for v in rep["scores"].values())


def test_architecture_report_tool(isolated_lab):
    with TestClient(app) as client:
        client.post("/api/scan", json={"target_path": BASE_DIR})
        out = client.post("/api/voice/tool", json={"name": "architecture_report", "arguments": {}}).json()
        assert out["ui"]["panel"] == "standards"
        assert any(p["learn_in_chapter"] == 5 for p in out["result"]["problems"])
        assert client.get("/api/repo/report").json()["checks"]
