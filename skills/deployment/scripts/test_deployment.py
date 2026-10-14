"""Behavioral conformance tests for the read-only deployment planner."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import deployment as d


NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


def fixture() -> dict:
    def check(kind="unit", phase="source", subject="source", **extra):
        return {"kind": kind, "phase": phase, "environment": "local", "method": "command",
                "subject": subject, "command": "test", **extra}

    return {
        "schema_version": 1, "project_id": "demo",
        "owners": {"deployment": "docs/deploy.md", "quality": "docs/quality.md",
                   "engineering": "docs/engineering.md"},
        "native": {"status": "native status owner", "release": "native release owner",
                   "rollback": "native rollback owner"},
        "commands": {"test": {"argv": ["python3", "-m", "unittest"], "cwd": ".",
                              "timeout_seconds": 90},
                     "verify": {"argv": ["python3", "native_verify.py"], "cwd": "."}},
        "checks": {
            "stack": check("stack readiness"),
            "source-e2e": check("E2E", depends_on=["stack"], binding_keys=["toolchain"]),
            "build": check("artifact production", "artifact", depends_on=["source-e2e"]),
            "stage": check("staged readiness", "artifact", "artifact", environment="staging",
                           depends_on=["build"]),
            "artifact-e2e": check("E2E", "artifact", "artifact", environment="staging",
                                  depends_on=["stage"], reuse_verifier="verify", max_age_seconds=600),
            "human": {"kind": "manual acceptance", "phase": "environment", "environment": "staging",
                      "subject": "artifact", "method": "manual", "acceptance_owner": "club owner",
                      "criterion": "docs/quality.md#acceptance", "depends_on": ["artifact-e2e"],
                      "reuse_verifier": "verify"},
            "live": check("live ACL", "postdeploy", "artifact", environment="production",
                          depends_on=["human"], reuse_verifier="verify"),
            "nightly": check("future scientific AI eval", "scheduled", binding_keys=["dataset"]),
        },
        "profiles": {"release": ["live"], "scheduled": ["nightly"], "weak": ["stack"]},
        "default_profile": "release",
    }


def bindings() -> dict:
    return {"source": "git:abc", "artifact": "sha256:image-a",
            "environments": {"local": "stack:v1", "staging": "stage:v1", "production": "prod:v1"},
            "inputs": {"toolchain": "python:3.10", "dataset": "sha256:data"}}


def planned(contract=None, **kwargs) -> dict:
    return d.plan(fixture() if contract is None else contract, context=bindings(), now=NOW, **kwargs)


def by_id(result: dict) -> dict:
    return {check["id"]: check for check in result["checks"]}


def receipt(contract: dict, key: str, *, when: datetime = NOW) -> dict:
    subject = by_id(planned(contract))[key]["expected_subject"]
    return {"schema_version": 1, "checks": {key: {"status": "passed", "subject": subject,
             "completed_at": when.isoformat(), "receipt_ref": "native/receipts/original.json"}}}


class PlanningTests(unittest.TestCase):
    def test_dependency_closure_and_source_and_staged_e2e(self):
        result = planned()
        self.assertEqual([c["id"] for c in result["checks"]],
                         ["stack", "source-e2e", "build", "stage", "artifact-e2e", "human", "live"])
        checks = by_id(result)
        self.assertEqual(checks["source-e2e"]["phase"], "source")
        self.assertEqual(checks["stage"]["phase"], "artifact")
        self.assertEqual(checks["artifact-e2e"]["expected_subject"]["artifact"], "sha256:image-a")
        self.assertNotIn("artifact", checks["build"]["expected_subject"])
        self.assertEqual(checks["human"]["action"], "manual_required")
        self.assertEqual(checks["human"]["acceptance_owner"], "club owner")
        self.assertNotIn("command", checks["human"])
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["release_verified"])

    def test_scheduled_arbitrary_kind_and_required_scheduled_not_discarded(self):
        c = fixture()
        self.assertEqual(planned(c, profile="scheduled")["checks"][0]["kind"], "future scientific AI eval")
        c["profiles"]["release"].append("nightly")
        self.assertEqual(planned(c)["checks"][-1]["id"], "nightly")

    def test_phase_order_when_independent_checks_are_selected(self):
        c = fixture()
        c["profiles"]["release"] = ["nightly", "stack", "artifact-e2e", "human"]
        phases = [d.PHASES.index(check["phase"]) for check in planned(c)["checks"]]
        self.assertEqual(phases, sorted(phases))

    def test_absent_context_and_partial_inputs_keep_all_checks_visible(self):
        result = d.plan(fixture(), now=NOW)
        self.assertEqual(len(result["checks"]), 7)
        self.assertTrue(all(c["action"] == "await_bindings" for c in result["checks"]))
        self.assertEqual(by_id(result)["source-e2e"]["missing_bindings"],
                         ["source", "environments.local", "inputs.toolchain"])
        self.assertIn("artifact", by_id(result)["artifact-e2e"]["missing_bindings"])
        context = bindings()
        del context["inputs"]["toolchain"]
        checks = by_id(d.plan(fixture(), context=context, now=NOW))
        self.assertEqual(checks["source-e2e"]["action"], "await_bindings")
        self.assertEqual(checks["source-e2e"]["missing_bindings"], ["inputs.toolchain"])

    def test_missing_environment_never_invented_from_phase(self):
        context = bindings()
        del context["environments"]["staging"]
        result = by_id(d.plan(fixture(), context=context, now=NOW))
        self.assertEqual(result["artifact-e2e"]["missing_bindings"], ["environments.staging"])

    def test_potential_reuse_requires_native_verifier_and_original_receipt(self):
        c = fixture()
        result = planned(c, evidence=receipt(c, "artifact-e2e"))
        check = by_id(result)["artifact-e2e"]
        self.assertEqual(check["action"], "verify_reuse")
        self.assertEqual(check["receipt_ref"], "native/receipts/original.json")
        self.assertEqual(check["verifier_command"]["id"], "verify")
        self.assertEqual(check["command"]["id"], "test")
        self.assertEqual(len(result["checks"]), 7)
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["release_verified"])

    def test_manual_reuse_retains_owner_and_criterion(self):
        c = fixture()
        check = by_id(planned(c, evidence=receipt(c, "human")))["human"]
        self.assertEqual(check["action"], "verify_reuse")
        self.assertEqual(check["acceptance_owner"], "club owner")
        self.assertEqual(check["criterion"], "docs/quality.md#acceptance")

    def test_failed_skipped_blocked_unknown_never_reused(self):
        c = fixture()
        for status in ("failed", "skipped", "blocked", "unknown"):
            with self.subTest(status=status):
                evidence = receipt(c, "artifact-e2e")
                evidence["checks"]["artifact-e2e"]["status"] = status
                self.assertEqual(by_id(planned(c, evidence=evidence))["artifact-e2e"]["action"], "run_required")

    def test_missing_evidence_fields_never_reused(self):
        c = fixture()
        for key in ("subject", "completed_at", "receipt_ref"):
            with self.subTest(key=key):
                evidence = receipt(c, "artifact-e2e")
                del evidence["checks"]["artifact-e2e"][key]
                self.assertEqual(by_id(planned(c, evidence=evidence))["artifact-e2e"]["action"], "run_required")

    def test_stale_future_boundary_and_timezone(self):
        c = fixture()
        for seconds, action in ((601, "run_required"), (600, "verify_reuse"),
                                (-1, "run_required"), (0, "verify_reuse")):
            with self.subTest(seconds=seconds):
                evidence = receipt(c, "artifact-e2e", when=NOW - timedelta(seconds=seconds))
                self.assertEqual(by_id(planned(c, evidence=evidence))["artifact-e2e"]["action"], action)
        evidence = receipt(c, "artifact-e2e")
        evidence["checks"]["artifact-e2e"]["completed_at"] = "2026-10-14T17:00:00+05:00"
        self.assertEqual(by_id(planned(c, evidence=evidence))["artifact-e2e"]["action"], "verify_reuse")
        evidence["checks"]["artifact-e2e"]["completed_at"] = "2026-10-14T12:00:00Z"
        self.assertEqual(by_id(planned(c, evidence=evidence))["artifact-e2e"]["action"], "verify_reuse")
        for invalid in ("2026-10-14T12:00:00", "tomorrow", "2026-99-99T00:00:00Z"):
            evidence["checks"]["artifact-e2e"]["completed_at"] = invalid
            with self.assertRaises(d.ValidationError):
                planned(c, evidence=evidence)

    def test_explicit_fresh_and_postdeploy_are_always_required(self):
        c = fixture()
        c["checks"]["artifact-e2e"]["fresh"] = True
        self.assertEqual(by_id(planned(c, evidence=receipt(c, "artifact-e2e")))["artifact-e2e"]["action"], "run_required")
        self.assertEqual(by_id(planned(c, evidence=receipt(c, "live")))["live"]["action"], "run_required")

    def test_no_verifier_means_no_reuse(self):
        c = fixture()
        self.assertEqual(by_id(planned(c, evidence=receipt(c, "stack")))["stack"]["action"], "run_required")

    def test_context_fingerprints_change_source_environment_artifact_inputs(self):
        c = fixture()
        evidence = receipt(c, "artifact-e2e")
        for field in ("source", "artifact", "environment"):
            context = bindings()
            if field == "environment":
                context["environments"]["staging"] = "stage:v2"
            else:
                context[field] += ":changed"
            with self.subTest(field=field):
                check = by_id(d.plan(c, context=context, evidence=evidence, now=NOW))["artifact-e2e"]
                self.assertEqual(check["action"], "run_required")
        c["checks"]["source-e2e"]["reuse_verifier"] = "verify"
        evidence = receipt(c, "source-e2e")
        context = bindings()
        context["inputs"]["toolchain"] = "python:3.11"
        self.assertEqual(by_id(d.plan(c, context=context, evidence=evidence, now=NOW))["source-e2e"]["action"], "run_required")

    def test_entire_mapping_recipe_and_manual_owner_are_fingerprinted(self):
        original = fixture()
        evidence = receipt(original, "artifact-e2e")
        mutations = [lambda c: c["commands"]["test"]["argv"].append("--changed"),
                     lambda c: c["native"].update(status="different native owner"),
                     lambda c: c["checks"]["nightly"].update(kind="unselected check changed"),
                     lambda c: c["checks"]["artifact-e2e"].update(binding_keys=["dataset"])]
        for mutate in mutations:
            c = copy.deepcopy(original)
            mutate(c)
            self.assertEqual(by_id(planned(c, evidence=evidence))["artifact-e2e"]["action"], "run_required")
        evidence = receipt(original, "human")
        original["checks"]["human"]["acceptance_owner"] = "another owner"
        self.assertEqual(by_id(planned(original, evidence=evidence))["human"]["action"], "manual_required")

    def test_tampered_subject_does_not_remove_required_work(self):
        c = fixture()
        for key in ("source", "environment", "contract_digest", "check_digest", "artifact"):
            evidence = receipt(c, "artifact-e2e")
            evidence["checks"]["artifact-e2e"]["subject"][key] = "0" * 64
            self.assertEqual(by_id(planned(c, evidence=evidence))["artifact-e2e"]["action"], "run_required")

    def test_planner_does_not_execute_any_project_commands(self):
        c = fixture()
        c["commands"]["test"]["argv"] = ["sh", "-c", "touch SHOULD-NOT-EXIST"]
        with patch("subprocess.run", side_effect=AssertionError("executed")), \
             patch("subprocess.Popen", side_effect=AssertionError("executed")):
            self.assertEqual(planned(c)["status"], "planned")


class RejectionTests(unittest.TestCase):
    def test_unknown_fields_at_every_mapping_level(self):
        for path in ((), ("owners",), ("native",), ("commands", "test"), ("checks", "nightly")):
            c = fixture()
            value = c
            for key in path:
                value = value[key]
            value["unknown"] = True
            with self.subTest(path=path), self.assertRaises(d.ValidationError):
                d.validate_contract(c)

    def test_integer_bool_distinction_and_types(self):
        mutations = [lambda c: c.update(schema_version=True),
                     lambda c: c["commands"]["test"].update(timeout_seconds=True),
                     lambda c: c["commands"]["test"].update(timeout_seconds=0),
                     lambda c: c["checks"]["nightly"].update(max_age_seconds=False),
                     lambda c: c["checks"]["nightly"].update(fresh=1),
                     lambda c: c["checks"]["nightly"].update(binding_keys="dataset"),
                     lambda c: c["commands"]["test"].update(argv=[]),
                     lambda c: c["commands"]["test"].update(argv=[12]),
                     lambda c: c["commands"]["test"].update(argv=[""]),
                     lambda c: c["checks"]["nightly"].update(command=""),
                     lambda c: c["checks"]["nightly"].update(kind=" "),
                     lambda c: c["checks"]["nightly"].update(environment="postgres://secret"),
                     lambda c: c["checks"]["human"].update(acceptance_owner=""),
                     lambda c: c["checks"]["human"].update(command="test"),
                     lambda c: c["checks"]["stack"].update(criterion="extra"),
                     lambda c: c["profiles"].update(weak=[]),
                     lambda c: c["profiles"].update(weak=["stack", "stack"])]
        for mutate in mutations:
            c = fixture()
            mutate(c)
            with self.subTest(contract=c), self.assertRaises(d.ValidationError):
                d.validate_contract(c)

    def test_dependency_missing_duplicate_cycle_and_backward_in_unselected_lane(self):
        for dependencies in (["missing"], ["stack", "stack"], ["nightly"]):
            c = fixture()
            c["checks"]["stack"]["depends_on"] = dependencies
            with self.assertRaises(d.ValidationError):
                planned(c, profile="weak")
        c = fixture()
        c["checks"]["stack"]["depends_on"] = ["source-e2e"]
        with self.assertRaises(d.ValidationError):
            planned(c, profile="weak")
        c = fixture()
        c["checks"]["nightly"]["command"] = "unknown"
        with self.assertRaises(d.ValidationError):
            planned(c, profile="weak")

    def test_invalid_profiles_ids_and_references(self):
        mutations = [lambda c: c.update(default_profile="missing"),
                     lambda c: c["profiles"].update(weak=["missing"]),
                     lambda c: c["checks"]["nightly"].update(reuse_verifier="missing"),
                     lambda c: c.update(project_id="A"),
                     lambda c: c.update(project_id="a" * 65)]
        for mutate in mutations:
            c = fixture()
            mutate(c)
            with self.assertRaises(d.ValidationError):
                planned(c)
        with self.assertRaises(d.ValidationError):
            planned(profile="missing")

    def test_invalid_context_and_evidence_fail_closed_even_for_unselected_checks(self):
        for context in ({"unknown": "value"}, {"source": ""}, {"environments": []},
                        {"inputs": {"TOKEN/unsafe": "value"}}):
            with self.assertRaises(d.ValidationError):
                d.plan(fixture(), context=context)
        for evidence in ({"schema_version": True, "checks": {}},
                         {"schema_version": 1, "checks": {"missing": {"status": "passed"}}},
                         {"schema_version": 1, "checks": {"nightly": {"status": "PASS"}}},
                         {"schema_version": 1, "checks": {"nightly": {"status": "passed", "trusted": True}}},
                         {"schema_version": 1, "checks": {"nightly": {"status": "passed", "receipt_ref": ""}}}):
            with self.assertRaises(d.ValidationError):
                planned(evidence=evidence)

    def test_unsafe_relative_paths_and_symlink_components(self):
        for path in ("../owner", "/etc/passwd", "a/../b", "a\\b", "x\nfile", "C:/owner",
                     "control\u0085file", "surrogate\ud800file"):
            c = fixture()
            c["owners"]["quality"] = path
            with self.assertRaises(d.ValidationError):
                d.validate_contract(c)
            c = fixture()
            c["commands"]["test"]["cwd"] = path
            with self.assertRaises(d.ValidationError):
                d.validate_contract(c)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "docs").mkdir()
            for name in ("deploy", "quality", "engineering"):
                (root / "docs" / f"{name}.md").write_text("owner", encoding="utf-8")
            self.assertEqual(d.validate_contract(fixture(), root)["filesystem_scope"], "project_root")
            (root / "docs" / "quality.md").unlink()
            with self.assertRaises(d.ValidationError):
                d.validate_contract(fixture(), root)
            (root / "docs" / "quality.md").symlink_to(root / "docs" / "deploy.md")
            with self.assertRaises(d.ValidationError):
                d.validate_contract(fixture(), root)
            (root / "link").symlink_to(root / "docs", target_is_directory=True)
            c = fixture()
            c["commands"]["test"]["cwd"] = "link"
            with self.assertRaises(d.ValidationError):
                d.validate_contract(c, root)
            c["owners"]["quality"] = "link/deploy.md"
            c["commands"]["test"]["cwd"] = "."
            with self.assertRaises(d.ValidationError):
                d.validate_contract(c, root)
            with self.assertRaises(d.ValidationError):
                d.validate_contract(fixture(), root / "link")


class JsonAndCliTests(unittest.TestCase):
    def test_shared_command_amplification_is_bounded_in_api_and_cli(self):
        c = fixture()
        c["commands"]["test"]["argv"] = ["x" * 200000]
        check = c["checks"]["stack"]
        c["checks"] = {f"check-{index}": dict(check) for index in range(100)}
        c["profiles"] = {"release": list(c["checks"])}
        serialized = json.dumps(c).encode("utf-8")
        self.assertLess(len(serialized), d.MAX_BYTES)
        self.assertEqual(d.validate_contract(c)["status"], "contract_valid")
        with self.assertRaisesRegex(d.ValidationError, "expanded plan exceeds 4 MiB"):
            d.plan(c, context=bindings(), now=NOW)
        script = Path(d.__file__).resolve()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mapping.json"
            path.write_bytes(serialized)
            result = subprocess.run([sys.executable, "-B", str(script), "plan", "--contract", str(path)],
                                    capture_output=True, text=True, check=False, timeout=10)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads(result.stdout),
                             {"status": "invalid", "error": "expanded plan exceeds 4 MiB"})
            self.assertLess(len(result.stdout), 1024)
            self.assertEqual(result.stderr, "")

    def test_output_budget_counts_exact_encoder_spacing_and_unicode(self):
        c = fixture()
        context = bindings()
        context["environments"]["local"] = "стек:готов"
        result = d.plan(c, context=context, now=NOW)
        size = len(d.OUTPUT_ENCODER.encode(result).encode("utf-8"))
        with patch.object(d, "MAX_PLAN_BYTES", size):
            self.assertEqual(d.plan(c, context=context, now=NOW), result)
        with patch.object(d, "MAX_PLAN_BYTES", size - 1):
            with self.assertRaises(d.ValidationError):
                d.plan(c, context=context, now=NOW)

    def test_strict_bounded_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            for raw in (b'{"a":1,"a":2}', b'{"x":{"a":1,"a":2}}', b'{"x":NaN}',
                        b'{"x":Infinity}', b'{"x":1e9999}', b'[]', b'{', b'\xff', b' ' * (d.MAX_BYTES + 1),
                        b'{"x":' + b'[' * 70 + b'0' + b']' * 70 + b'}'):
                path.write_bytes(raw)
                with self.subTest(size=len(raw)), self.assertRaises(d.ValidationError):
                    d.load_json(path)

    def test_cli_stdout_exit_status_and_no_project_mutations(self):
        script = Path(d.__file__).resolve()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "mapping.json"
            c = fixture()
            c["commands"]["test"]["argv"] = [sys.executable, "-c", "open('UNSAFE', 'w').write('executed')"]
            path.write_text(json.dumps(c), encoding="utf-8")
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            for operation in ("validate", "plan"):
                result = subprocess.run([sys.executable, "-B", str(script), operation, "--contract", str(path)],
                                        cwd=root, capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                output = json.loads(result.stdout)
                self.assertEqual(output["status"], "contract_valid" if operation == "validate" else "planned")
                if operation == "plan":
                    self.assertFalse(output["release_authorized"])
                    self.assertTrue(all(c["action"] == "await_bindings" for c in output["checks"]))
            after = {p.name: p.read_bytes() for p in root.iterdir()}
            self.assertEqual(before, after)
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            result = subprocess.run([sys.executable, "-B", str(script), "validate", "--contract", str(path)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid")
            result = subprocess.run([sys.executable, "-B", str(script), "plan", "--contract", str(root / "absent")],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
