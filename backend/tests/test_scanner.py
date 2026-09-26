"""Unit tests for backend/app/services/scanner_service.py — Mission 02."""
from __future__ import annotations

import os
import textwrap

import pytest

from app.models.schemas import AttributeType
from app.services.scanner_service import DetectedSmell, RepoScanner


# ---------------------------------------------------------------------------
# Helper: build a scanner that operates on *content* in memory
# ---------------------------------------------------------------------------

def _scan(content: str, file_path: str = "test_file.py") -> list[DetectedSmell]:
    scanner = RepoScanner(target_path=".")
    return scanner.scan_file(file_path=file_path, content=textwrap.dedent(content))


def _rules(smells: list[DetectedSmell]) -> list[str]:
    return [s.rule_id for s in smells]


def _attrs(smells: list[DetectedSmell]) -> list[AttributeType]:
    return [s.attribute for s in smells]


# ===========================================================================
# Speed checks
# ===========================================================================

class TestSpeedChecks:

    def test_time_sleep_in_async_triggers_speed_smell(self):
        code = """\
            import time

            async def fetch():
                time.sleep(1)
        """
        smells = _scan(code)
        speed_smells = [s for s in smells if s.attribute == AttributeType.SPEED and s.rule_id == "SPEED-001"]
        assert len(speed_smells) == 1
        smell = speed_smells[0]
        assert smell.rule_id == "SPEED-001"
        assert smell.attribute == AttributeType.SPEED
        # Tachyon critique must be non-empty
        assert smell.tachyon_critique
        assert "sleep" in smell.description.lower() or "sleep" in smell.tachyon_critique.lower()

    def test_time_sleep_in_sync_func_does_not_trigger(self):
        code = """\
            import time

            def fetch():
                time.sleep(1)
        """
        smells = _scan(code)
        speed_blocking = [s for s in smells if s.rule_id == "SPEED-001"]
        assert len(speed_blocking) == 0

    def test_sync_requests_in_async_triggers_speed_smell(self):
        code = """\
            import requests

            async def get_data():
                resp = requests.get("http://example.com", timeout=5)
                return resp
        """
        smells = _scan(code)
        speed_smells = [s for s in smells if s.rule_id == "SPEED-001"]
        assert len(speed_smells) == 1
        assert "requests" in speed_smells[0].description.lower()

    def test_high_complexity_triggers_speed_smell(self):
        # Build a function with > 10 branches
        branches = "\n".join(
            f"    if x == {i}:\n        pass" for i in range(12)
        )
        code = f"def complex_func(x):\n{branches}\n"
        smells = _scan(code)
        speed002 = [s for s in smells if s.rule_id == "SPEED-002"]
        assert len(speed002) == 1
        assert "complexity" in speed002[0].description.lower()

    def test_low_complexity_does_not_trigger(self):
        code = """\
            def simple(x):
                if x > 0:
                    return x
                return -x
        """
        smells = _scan(code)
        assert "SPEED-002" not in _rules(smells)


# ===========================================================================
# Stamina checks
# ===========================================================================

class TestStaminaChecks:

    def test_open_without_with_triggers_stamina_smell(self):
        code = """\
            def read_file(path):
                f = open(path)
                data = f.read()
                return data
        """
        smells = _scan(code)
        stamina_smells = [s for s in smells if s.rule_id == "STAMINA-001"]
        assert len(stamina_smells) == 1
        smell = stamina_smells[0]
        assert smell.attribute == AttributeType.STAMINA
        assert smell.tachyon_critique
        assert "open" in smell.description.lower()

    def test_open_inside_with_does_not_trigger(self):
        code = """\
            def read_file(path):
                with open(path) as f:
                    return f.read()
        """
        smells = _scan(code)
        assert "STAMINA-001" not in _rules(smells)

    def test_db_cursor_without_with_triggers_stamina_smell(self):
        code = """\
            def query(conn):
                cur = conn.cursor()
                cur.execute("SELECT 1")
                return cur.fetchall()
        """
        smells = _scan(code)
        stamina_smells = [s for s in smells if s.rule_id == "STAMINA-002"]
        assert len(stamina_smells) >= 1
        assert all(s.attribute == AttributeType.STAMINA for s in stamina_smells)

    def test_db_cursor_inside_with_does_not_trigger(self):
        code = """\
            def query(conn):
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return cur.fetchall()
        """
        smells = _scan(code)
        assert "STAMINA-002" not in _rules(smells)


# ===========================================================================
# Power checks
# ===========================================================================

class TestPowerChecks:

    def test_sequential_loop_triggers_power_smell(self):
        code = """\
            def process(items):
                for item in items:
                    process_item(item)
        """
        smells = _scan(code)
        power_smells = [s for s in smells if s.rule_id == "POWER-001"]
        assert len(power_smells) == 1
        smell = power_smells[0]
        assert smell.attribute == AttributeType.POWER
        assert smell.tachyon_critique

    def test_loop_with_mixed_body_does_not_trigger(self):
        # Body has an if-statement, not purely sequential calls
        code = """\
            def process(items):
                results = []
                for item in items:
                    if item:
                        results.append(item)
                return results
        """
        smells = _scan(code)
        assert "POWER-001" not in _rules(smells)


# ===========================================================================
# Guts checks
# ===========================================================================

class TestGutsChecks:

    def test_bare_except_pass_triggers_guts_smell(self):
        code = """\
            def risky():
                try:
                    do_something()
                except:
                    pass
        """
        smells = _scan(code)
        guts_smells = [s for s in smells if s.rule_id == "GUTS-001"]
        assert len(guts_smells) == 1
        smell = guts_smells[0]
        assert smell.attribute == AttributeType.GUTS
        assert smell.tachyon_critique
        assert "swallow" in smell.description.lower() or "exception" in smell.description.lower()

    def test_except_exception_pass_triggers_guts_smell(self):
        code = """\
            def risky():
                try:
                    do_something()
                except Exception:
                    pass
        """
        smells = _scan(code)
        guts_smells = [s for s in smells if s.rule_id == "GUTS-001"]
        assert len(guts_smells) == 1

    def test_specific_exception_with_handling_does_not_trigger(self):
        code = """\
            def risky():
                try:
                    do_something()
                except ValueError as e:
                    raise RuntimeError("bad value") from e
        """
        smells = _scan(code)
        assert "GUTS-001" not in _rules(smells)

    def test_http_call_without_timeout_triggers_guts_smell(self):
        code = """\
            import requests

            def fetch():
                return requests.get("http://example.com")
        """
        smells = _scan(code)
        guts_smells = [s for s in smells if s.rule_id == "GUTS-002"]
        assert len(guts_smells) == 1
        assert guts_smells[0].attribute == AttributeType.GUTS

    def test_http_call_with_timeout_does_not_trigger(self):
        code = """\
            import requests

            def fetch():
                return requests.get("http://example.com", timeout=10)
        """
        smells = _scan(code)
        assert "GUTS-002" not in _rules(smells)


# ===========================================================================
# Wisdom checks
# ===========================================================================

class TestWisdomChecks:

    def test_missing_return_annotation_triggers_wisdom_smell(self):
        code = """\
            def compute(x):
                return x * 2
        """
        smells = _scan(code)
        wisdom_smells = [s for s in smells if s.rule_id == "WISDOM-001"]
        assert len(wisdom_smells) == 1
        assert wisdom_smells[0].attribute == AttributeType.WISDOM

    def test_annotated_function_does_not_trigger(self):
        code = """\
            def compute(x: int) -> int:
                return x * 2
        """
        smells = _scan(code)
        assert "WISDOM-001" not in _rules(smells)

    def test_init_missing_annotation_does_not_trigger(self):
        code = """\
            class Foo:
                def __init__(self):
                    self.x = 1
        """
        smells = _scan(code)
        assert "WISDOM-001" not in _rules(smells)

    def test_long_function_triggers_wisdom_smell(self):
        # Generate a function with > 80 lines
        body = "\n".join(f"    x_{i} = {i}" for i in range(82))
        code = f"def long_func() -> None:\n{body}\n"
        smells = _scan(code)
        wisdom_smells = [s for s in smells if s.rule_id == "WISDOM-002"]
        assert len(wisdom_smells) == 1
        assert "lines" in wisdom_smells[0].description.lower()


# ===========================================================================
# Score calculation on a dummy repository fixture
# ===========================================================================

class TestScoreCalculation:

    def _write_files(self, tmp_path, files: dict[str, str]) -> None:
        for name, content in files.items():
            p = tmp_path / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(textwrap.dedent(content), encoding="utf-8")

    def test_clean_repo_starts_at_baseline_or_above(self, tmp_path):
        """A repo with no smells should produce scores >= 400 (baseline E)."""
        self._write_files(tmp_path, {
            "main.py": """\
                def greet(name: str) -> str:
                    return f"Hello, {name}"
            """,
        })
        scanner = RepoScanner(target_path=str(tmp_path))
        scores, smells = scanner.scan_repository()
        assert scores.speed >= 400
        assert scores.stamina >= 400
        assert scores.power >= 400
        assert scores.guts >= 400

    def test_multiple_smells_reduce_scores(self, tmp_path):
        """A repo with smells should have lower scores than the baseline."""
        self._write_files(tmp_path, {
            "bad.py": """\
                import time

                async def bad_async():
                    time.sleep(2)

                def read_raw(path):
                    f = open(path)
                    return f.read()

                def risky():
                    try:
                        pass
                    except:
                        pass
            """,
        })
        scanner = RepoScanner(target_path=str(tmp_path))
        scores, smells = scanner.scan_repository()

        assert scores.speed < 400, "Speed should be penalised by blocking call"
        assert scores.stamina < 400, "Stamina should be penalised by unclosed open()"
        assert scores.guts < 400, "Guts should be penalised by swallowed exception"

    def test_test_file_presence_grants_bonus(self, tmp_path):
        """A repo containing a test file should give a Guts/Wisdom bonus."""
        self._write_files(tmp_path, {
            "app.py": "def greet(name: str) -> str:\n    return name\n",
            "test_app.py": "def test_greet():\n    assert True\n",
        })
        scanner_with_tests = RepoScanner(target_path=str(tmp_path))
        scores_with, _ = scanner_with_tests.scan_repository()

        # Without test file
        tmp_no_test = tmp_path / "no_test"
        tmp_no_test.mkdir()
        (tmp_no_test / "app.py").write_text(
            "def greet(name: str) -> str:\n    return name\n", encoding="utf-8"
        )
        scanner_no_tests = RepoScanner(target_path=str(tmp_no_test))
        scores_without, _ = scanner_no_tests.scan_repository()

        assert scores_with.guts > scores_without.guts, "Test file should boost Guts"
        assert scores_with.wisdom > scores_without.wisdom, "Test file should boost Wisdom"

    def test_scores_are_clamped_between_100_and_1200(self, tmp_path):
        """Scores must never leave [100, 1200] regardless of smell density."""
        # 50 files each with a swallowed exception
        files = {}
        for i in range(50):
            files[f"module_{i}.py"] = """\
                def risky():
                    try:
                        pass
                    except:
                        pass
            """
        self._write_files(tmp_path, files)
        scanner = RepoScanner(target_path=str(tmp_path))
        scores, _ = scanner.scan_repository()

        for attr in ("speed", "stamina", "power", "guts", "wisdom"):
            value = getattr(scores, attr)
            assert 100 <= value <= 1200, f"{attr} out of range: {value}"

    def test_returns_correct_types(self, tmp_path):
        """scan_repository must return (AttributeScores, list[DetectedSmell])."""
        from app.models.schemas import AttributeScores as AS
        (tmp_path / "empty.py").write_text("", encoding="utf-8")
        scanner = RepoScanner(target_path=str(tmp_path))
        result = scanner.scan_repository()
        assert isinstance(result, tuple) and len(result) == 2
        scores, smells = result
        assert isinstance(scores, AS)
        assert isinstance(smells, list)

    def test_syntax_error_in_file_does_not_crash(self, tmp_path):
        """Files with SyntaxErrors must be silently skipped."""
        (tmp_path / "broken.py").write_text("def (:\n    pass\n", encoding="utf-8")
        scanner = RepoScanner(target_path=str(tmp_path))
        scores, smells = scanner.scan_repository()  # must not raise
        assert isinstance(smells, list)
