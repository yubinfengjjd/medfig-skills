#!/usr/bin/env python3
"""Check explicit local planning registers; never execute their command text.

Exit 0: registered structure passes (not scientific validation).
Exit 1: directly registered relationship/rule fails.
Exit 2: input/JSON/schema/report operational failure.
Standard library only. Inputs are always read-only.
"""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import sys
import tempfile


SCHEMA_VERSION = "1.0"
INPUT_FILES = ("state.json", "constraints.json", "evidence.json", "data-register.json", "plan-contract.json")
PROTECTED_FILES = INPUT_FILES + ("session.md", "project-plan.md", "review.md", "search-log.md")
SECTIONS = ("scope", "question", "data", "methods", "analysis", "statistics", "trustworthiness", "positioning", "consistency", "engineering", "risks")
EVIDENCE_STATES = ("PROVIDED", "VERIFIED", "INFERRED", "PROVISIONAL", "UNKNOWN", "CONFLICTED")
IMPACTS = ("CRITICAL_SCIENTIFIC", "EXECUTION_PREREQUISITE", "NONCRITICAL_CHOICE")
CONFIRMATION_STATES = ("UNCONFIRMED", "CONFIRMED", "INVALIDATED", "SUPERSEDED")
EXECUTION_STATES = ("PLANNED", "NOT_STARTED", "EXECUTED_UNVERIFIED", "EXECUTED_VERIFIED")
RECORD_TYPES = ("METHOD", "CLAIM", "EXPERIMENT", "METRIC", "TASK", "CONFIG", "BUDGET")
ENTITY_TYPES = ("CONSTRAINT", "EVIDENCE", "DATASET") + RECORD_TYPES
GATE_IDS = ("G1", "G2", "G3")
ARTIFACT_DEFAULTS = {"session": "session.md", "main_plan": "project-plan.md", "review": "review.md"}


def string(nonempty=False):
    return {"type": "string", **({"min_length": 1} if nonempty else {})}


def enum(*values):
    return {"type": "string", "enum": list(values)}


def array(items):
    return {"type": "array", "items": items}


def obj(properties, optional=()):
    return {"type": "object", "properties": properties,
            "required": [name for name in properties if name not in optional], "additional_properties": True}


def nullable(schema):
    return {"any_of": [{"type": "null"}, schema]}


TEXT = string()
ID = string(True)
IDS = array(ID)
BOOL = {"type": "boolean"}
NUMBER = {"type": "number"}
INTEGER = {"type": "integer"}
SOURCE = obj({"kind": enum("USER", "PUBLIC", "LOCAL", "ASSISTANT"), "locator": TEXT, "summary": TEXT})
USER_SOURCE = obj({"kind": enum("USER", "PUBLIC", "LOCAL", "ASSISTANT"), "locator": TEXT,
                   "decision": enum("ANSWER", "CONFIRM", "DELEGATE", "AUTHORIZE_EXECUTION", "PAUSE"),
                   "scope": IDS, "response": TEXT})
CONFIRMATION = obj({"status": enum(*CONFIRMATION_STATES), "version": ID, "source": nullable(USER_SOURCE)})
UNKNOWN = obj({"id": ID, "status": enum("UNKNOWN", "CONFLICTED", "PROVISIONAL"), "impact": enum(*IMPACTS),
               "statement": TEXT, "affected_ids": IDS, "next_action": TEXT})
GATE_CHANGE = obj({"id": ID, "record_type": enum("GATE_CHANGE"), "from_version": ID, "to_version": ID,
                   "reason": TEXT, "source": SOURCE, "affected_gate_ids": array(enum(*GATE_IDS)),
                   "preserved_gate_ids": array(enum(*GATE_IDS)), "affected_constraint_ids": IDS, "preserved_constraint_ids": IDS})
INTERVAL = obj({"lower": nullable(NUMBER), "upper": nullable(NUMBER)})
QUANTITY_RULE = obj({"rule_type": enum("QUANTITY"), "record_type": enum(*ENTITY_TYPES), "target_ids": IDS,
                     "operator": enum("MIN", "MAX", "EQUAL"), "value": INTEGER})
NUMBER_RULE = obj({"rule_type": enum("NUMBER"), "actual": nullable(NUMBER), "operator": enum("MIN", "MAX", "EQUAL"), "value": NUMBER})
CONSTRAINT = obj({"id": ID, "statement": TEXT, "kind": enum("HARD", "TARGET", "PREFERENCE", "DEFAULT", "UNKNOWN"),
                  "category": TEXT, "evidence_status": enum(*EVIDENCE_STATES), "impact": enum(*IMPACTS), "source": SOURCE,
                  "user_confirmation": CONFIRMATION, "validation": nullable({"type": "object"}),
                  "affected_ids": IDS, "override_history": array({"type": "object"})})
EVIDENCE = obj({"id": ID, "title": TEXT, "evidence_status": enum(*EVIDENCE_STATES), "impact": enum(*IMPACTS), "source": SOURCE,
                "verification": nullable(obj({"scope": TEXT, "location": TEXT, "checked_at": TEXT})),
                "supported_claim_ids": IDS, "challenged_claim_ids": IDS})
DATASET = obj({"id": ID, "name": TEXT, "version": TEXT,
               "role": enum("DEVELOPMENT", "TRAIN", "TUNING", "CALIBRATION", "INTERNAL_TEST", "EXTERNAL_TEST", "ANALYSIS"),
               "uses": array(enum("TRAIN", "TUNE", "CALIBRATE", "THRESHOLD", "EVALUATE", "ANALYZE")),
               "available_inputs": IDS, "evidence_status": enum(*EVIDENCE_STATES), "impact": enum(*IMPACTS),
               "evidence_ids": IDS, "independence_unit": TEXT, "group_ids": nullable(IDS)}, optional=("group_ids",))
BASE_RECORD = {"id": ID, "record_type": enum(*RECORD_TYPES)}
PLAN_RECORD_SCHEMAS = {
    "METHOD": obj({**BASE_RECORD, "name": TEXT, "purpose": TEXT, "dataset_ids": IDS, "required_inference_inputs": IDS, "evidence_ids": IDS}),
    "CLAIM": obj({**BASE_RECORD, "statement": TEXT, "evidence_status": enum(*EVIDENCE_STATES), "impact": enum(*IMPACTS),
                  "method_ids": IDS, "evidence_ids": IDS, "experiment_ids": IDS, "falsification": TEXT}),
    "EXPERIMENT": obj({**BASE_RECORD, "purpose": TEXT, "role": enum("BASELINE", "MAIN", "ABLATION", "SENSITIVITY", "EVALUATION", "SEARCH", "DIAGNOSTIC"),
                       "claim_ids": IDS, "method_ids": IDS, "dataset_ids": IDS, "metric_ids": IDS, "task_ids": IDS}),
    "METRIC": obj({**BASE_RECORD, "name": TEXT, "target": TEXT, "definition": TEXT, "unit": TEXT, "aggregation": TEXT, "uncertainty": TEXT, "primary": BOOL}),
    "TASK": obj({**BASE_RECORD, "kind": enum("PREPARATION", "TRAINING", "ANALYSIS", "EVALUATION", "PROFILING", "ARCHIVE"),
                 "scientific_purpose": TEXT, "claim_ids": IDS, "depends_on": IDS,
                 "inputs": array(obj({"ref_id": ID, "schema": TEXT})), "outputs": array(obj({"path": TEXT, "schema": TEXT})),
                 "scope": TEXT, "planned_files": array(TEXT), "config_ids": IDS,
                 "command": obj({"status": enum(*EXECUTION_STATES), "text": TEXT, "executable": BOOL}),
                 "acceptance": array(TEXT), "failure_handling": TEXT, "stop_conditions": array(TEXT),
                 "execution_status": enum(*EXECUTION_STATES), "authorization_status": enum("NOT_AUTHORIZED", "AUTHORIZED"),
                 "authorization_source": nullable(USER_SOURCE), "execution_evidence_ids": IDS}),
    "CONFIG": obj({**BASE_RECORD, "method_id": ID, "settings": {"type": "object"}}),
    "BUDGET": obj({**BASE_RECORD, "config_id": ID, "runs": INTEGER, "duration_hours": INTERVAL, "memory_gb": INTERVAL,
                   "measurement_status": enum("ESTIMATED", "REFERENCE_MEASURED", "LOCAL_MEASURED", "UNKNOWN"), "basis": TEXT,
                   "profile_task_id": nullable(ID), "impact": enum(*IMPACTS)}),
}
for record_kind, record_schema in PLAN_RECORD_SCHEMAS.items():
    record_schema["properties"]["record_type"] = enum(record_kind)
REGISTER_BASE = {"schema_version": enum(SCHEMA_VERSION), "version": ID}
FILE_SCHEMAS = {
    "state.json": obj({**REGISTER_BASE, "stage": enum("INTAKE", "INTERVIEW", "POSITIONING", "DESIGN", "REVIEW", "HANDOFF"),
                       "status": enum("ACTIVE", "PAUSED_BY_USER", "PROVISIONAL", "READY_FOR_HANDOFF"),
                       "gates": obj({gate: CONFIRMATION for gate in ("G1", "G2", "G3")}), "unknowns": array(UNKNOWN),
                       "pause_source": nullable(USER_SOURCE), "changes": array(GATE_CHANGE),
                       "artifacts": obj({role: ID for role in ARTIFACT_DEFAULTS}, optional=tuple(ARTIFACT_DEFAULTS))},
                      optional=("pause_source", "changes", "artifacts")),
    "constraints.json": obj({**REGISTER_BASE, "records": array(CONSTRAINT)}),
    "evidence.json": obj({**REGISTER_BASE, "records": array(EVIDENCE)}),
    "data-register.json": obj({**REGISTER_BASE, "records": array(DATASET)}),
    "plan-contract.json": obj({**REGISTER_BASE, "records": array(obj(BASE_RECORD)),
                               "sections": obj({name: obj({"summary": TEXT, "ref_ids": IDS}) for name in SECTIONS}, optional=SECTIONS)}),
}
LIMITATIONS = [
    "A PASS means explicit registered structure passes; it does not establish scientific validity or readiness of real execution resources.",
    "Submitted USER/CONFIRM provenance cannot be authenticated by this checker; inspect the actual user reply and its scope in the registered session artifact.",
    "GATE_CHANGE records only register continued applicability of original consent; their source, unchanged scope, and affected/preserved decisions require semantic review and cannot create new confirmation.",
    "No source authenticity, literature novelty, label quality, clinical value, statistical adequacy, or real resource feasibility is scientifically validated.",
    "Observed group IDs are compared only within their submitted namespace; missing identifiers and different identifier encodings do not prove independence.",
    "No natural-language inference, semantic word matching, network access, command execution, data analysis, or training is performed.",
]


def issue(code, path, message):
    return {"code": code, "path": path, "message": message}


def check_schema(value, schema, path, errors):
    """Small documented schema dialect, intentionally independent of dependencies."""
    if "any_of" in schema:
        if value is None and any(part.get("type") == "null" for part in schema["any_of"]):
            return
        return check_schema(value, next(part for part in schema["any_of"] if part.get("type") != "null"), path, errors)
    kind = schema["type"]
    valid = {"null": value is None, "string": isinstance(value, str), "boolean": type(value) is bool,
             "integer": type(value) is int, "number": type(value) in (int, float),
             "array": isinstance(value, list), "object": isinstance(value, dict)}[kind]
    if not valid:
        errors.append(issue("SCHEMA_TYPE", path, "Expected " + kind + "; received " + type(value).__name__ + "."))
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(issue("SCHEMA_ENUM", path, "Value is outside the documented enum."))
    if kind == "string" and "min_length" in schema and not value.strip():
        errors.append(issue("SCHEMA_VALUE", path, "Identifier must be a nonempty string."))
    if kind == "number" and isinstance(value, float) and not math.isfinite(value):
        errors.append(issue("SCHEMA_VALUE", path, "Number must be finite."))
    if kind == "object":
        for key in schema.get("required", []):
            if key not in value:
                errors.append(issue("SCHEMA_REQUIRED", path + "." + key, "Required field is missing."))
        for key, child in schema.get("properties", {}).items():
            if key in value:
                check_schema(value[key], child, path + "." + key, errors)
    if kind == "array":
        for index, child in enumerate(value):
            check_schema(child, schema["items"], path + "[" + str(index) + "]", errors)


def reject_constant(value):
    raise ValueError("Non-finite JSON number is not allowed: " + value)


def finite_float(value):
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("JSON number exceeds finite range.")
    return parsed


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key: " + key)
        result[key] = value
    return result


def read_inputs(project, report):
    files = {}
    for name in INPUT_FILES:
        try:
            files[name] = json.loads((project / name).read_text(encoding="utf-8-sig"),
                                     parse_constant=reject_constant, parse_float=finite_float, object_pairs_hook=reject_duplicate_keys)
        except (OSError, UnicodeError) as error:
            report["errors"].append(issue("INPUT_READ_FAILED", name, type(error).__name__ + ": input cannot be read."))
        except (ValueError, RecursionError) as error:
            detail = "JSON is invalid or exceeds supported nesting."
            if isinstance(error, json.JSONDecodeError):
                detail = "Invalid JSON at line " + str(error.lineno) + ", column " + str(error.colno) + "."
            report["errors"].append(issue("INVALID_JSON", name, detail))
    report["checks_run"].append("input_json")
    for name, value in files.items():
        check_schema(value, FILE_SCHEMAS[name], name, report["errors"])
    if isinstance(files.get("state.json"), dict):
        report["input_version"] = files["state.json"].get("version")
    # Conditional record/rule variants are explicit, not inferred from their prose.
    plan = files.get("plan-contract.json")
    if isinstance(plan, dict) and isinstance(plan.get("records"), list):
        for index, value in enumerate(plan["records"]):
            if isinstance(value, dict) and isinstance(value.get("record_type"), str) and value["record_type"] in PLAN_RECORD_SCHEMAS:
                check_schema(value, PLAN_RECORD_SCHEMAS[value["record_type"]], "plan-contract.json.records[" + str(index) + "]", report["errors"])
    constraints = files.get("constraints.json")
    if isinstance(constraints, dict) and isinstance(constraints.get("records"), list):
        for index, value in enumerate(constraints["records"]):
            if not isinstance(value, dict) or value.get("validation") is None:
                continue
            path = "constraints.json.records[" + str(index) + "].validation"
            rule = value.get("validation")
            if isinstance(rule, dict):
                if rule.get("rule_type") in ("QUANTITY", "NUMBER"):
                    check_schema(rule, QUANTITY_RULE if rule["rule_type"] == "QUANTITY" else NUMBER_RULE, path, report["errors"])
                else:
                    report["errors"].append(issue("SCHEMA_ENUM", path + ".rule_type", "Expected QUANTITY or NUMBER."))
    report["checks_run"].append("schema")
    return files


def resolve_artifact_path(project, name):
    """Resolve only a syntactically local Markdown registration, never its text."""
    if not isinstance(name, str) or not name.strip():
        return None
    relative = PureWindowsPath(name)
    if (relative.drive or relative.root or ".." in relative.parts or relative.suffix.lower() != ".md"
            or any(":" in component for component in relative.parts)):
        return None
    try:
        resolved = (project / Path(*relative.parts)).resolve()
        return resolved if resolved.is_relative_to(project) else None
    except (OSError, RuntimeError, ValueError):
        return None


def registered_artifact_paths(project, state):
    """Protect each valid registration even when unrelated input/schema is bad."""
    if not isinstance(state, dict) or not isinstance(state.get("artifacts"), dict):
        return []
    paths = []
    for role in ARTIFACT_DEFAULTS:
        if role in state["artifacts"]:
            path = resolve_artifact_path(project, state["artifacts"][role])
            if path is not None:
                paths.append(path)
    return paths


class Rules:
    def __init__(self, files, project, report):
        self.files, self.project, self.report = files, project, report
        self.state = files["state.json"]
        self.ready = self.state["status"] == "READY_FOR_HANDOFF"
        self.entries, self.index = [], {}
        self.change_by_to, self.change_chain_valid = {}, True
        self.artifact_paths = {}
        groups = (("CONSTRAINT", "constraints.json"), ("EVIDENCE", "evidence.json"), ("DATASET", "data-register.json"))
        for kind, filename in groups:
            for number, record in enumerate(files[filename]["records"]):
                self.entries.append((kind, record, filename + ".records[" + str(number) + "]"))
        for number, record in enumerate(files["plan-contract.json"]["records"]):
            self.entries.append((record["record_type"], record, "plan-contract.json.records[" + str(number) + "]"))
        for number, record in enumerate(self.state["unknowns"]):
            self.entries.append(("UNKNOWN", record, "state.json.unknowns[" + str(number) + "]"))
        for number, record in enumerate(self.state.get("changes", [])):
            self.entries.append(("CHANGE", record, "state.json.changes[" + str(number) + "]"))

    def add(self, code, path, message, bucket="errors"):
        self.report[bucket].append(issue(code, path, message))

    def records(self, kind):
        return [(record, path) for candidate, record, path in self.entries if candidate == kind]

    def ref(self, identifiers, expected, path):
        if len(identifiers) != len(set(identifiers)):
            self.add("REFERENCE_DUPLICATE", path, "Repeated references cannot count as distinct records.")
        for identifier in identifiers:
            target = self.index.get(identifier)
            if target is None:
                self.add("FOREIGN_KEY_MISSING", path, "Referenced ID does not exist: " + identifier)
            elif expected and target[0] not in expected:
                self.add("FOREIGN_KEY_TYPE", path, "Referenced ID has the wrong register type: " + identifier)

    def source_valid(self, source, scope, decision):
        return bool(source and source["kind"] == "USER" and source["decision"] == decision and scope in source["scope"]
                    and source["locator"].strip() and source["response"].strip())

    def confirmation(self, confirmation, path, scope):
        if confirmation["status"] == "CONFIRMED":
            if confirmation["version"] != self.state["version"] and not self.carried(scope, confirmation["version"]):
                self.add("CONFIRMATION_VERSION_STALE", path, "Old confirmation has no valid explicit per-decision carry chain to the current version.")
            if not self.source_valid(confirmation["source"], scope, "CONFIRM"):
                self.add("CONFIRMATION_SOURCE_INVALID", path, "CONFIRMED requires explicit scoped USER/CONFIRM provenance; ANSWER, silence, and delegation are insufficient.")

    def carried(self, scope, original_version):
        if not self.change_chain_valid:
            return False
        version, seen = self.state["version"], set()
        while version != original_version:
            if version in seen or version not in self.change_by_to:
                return False
            seen.add(version)
            change = self.change_by_to[version]
            field = "preserved_gate_ids" if scope in GATE_IDS else "preserved_constraint_ids"
            if scope not in change[field]:
                return False
            version = change["from_version"]
        return True

    def gate_changes(self):
        changes = self.records("CHANGE")
        before = len(self.report["errors"])
        for change, path in changes:
            if not change["reason"].strip() or not all(change["source"][field].strip() for field in ("locator", "summary")):
                self.add("CHANGE_SOURCE_INCOMPLETE", path, "A carry/change record needs a reason and actual source locator/summary; it is not a new confirmation.")
            affected, preserved = set(change["affected_gate_ids"]), set(change["preserved_gate_ids"])
            if affected & preserved:
                self.add("CHANGE_GATE_CONFLICT", path, "A gate cannot be both affected and preserved by the same change.")
            if affected | preserved != set(GATE_IDS):
                self.add("CHANGE_GATE_SCOPE_INCOMPLETE", path, "Every change explicitly classifies G1-G3 as affected or preserved.")
            for field in ("affected_gate_ids", "preserved_gate_ids"):
                if len(change[field]) != len(set(change[field])):
                    self.add("REFERENCE_DUPLICATE", path + "." + field, "Gate scopes cannot contain duplicate IDs.")
            for field in ("affected_constraint_ids", "preserved_constraint_ids"):
                self.ref(change[field], {"CONSTRAINT"}, path + "." + field)
            if set(change["affected_constraint_ids"]) & set(change["preserved_constraint_ids"]):
                self.add("CHANGE_CONSTRAINT_CONFLICT", path, "A constraint cannot be both affected and preserved by the same change.")
            if change["from_version"] == change["to_version"] or change["to_version"] in self.change_by_to:
                self.add("CHANGE_VERSION_CHAIN_INVALID", path, "Version changes need distinct from/to versions and one unambiguous predecessor per destination.")
            self.change_by_to[change["to_version"]] = change
            if preserved or change["preserved_constraint_ids"]:
                self.add("GATE_CARRY_REVIEW", path, "Inspect whether these exact decisions are unchanged and whether change source/scope are justified; original USER/CONFIRM provenance is retained, not renewed.", "needs_review")
        version, seen, used = self.state["version"], set(), 0
        while version in self.change_by_to:
            if version in seen:
                self.add("CHANGE_VERSION_CHAIN_INVALID", "state.json.changes", "Version change chain contains a cycle.")
                break
            seen.add(version)
            used += 1
            version = self.change_by_to[version]["from_version"]
        if used != len(changes):
            self.add("CHANGE_VERSION_CHAIN_INVALID", "state.json.changes", "Changes must form one complete chain ending at state.version; disconnected or ambiguous history cannot carry decisions.")
        self.change_chain_valid = len(self.report["errors"]) == before
        self.report["checks_run"].append("explicit_gate_and_constraint_version_changes")

    def resolve_artifacts(self):
        names = {**ARTIFACT_DEFAULTS, **self.state.get("artifacts", {})}
        for role in ARTIFACT_DEFAULTS:
            resolved = resolve_artifact_path(self.project, names[role])
            if resolved is None:
                self.add("ARTIFACT_PATH_INVALID", "state.json.artifacts." + role,
                         "Artifact must be a project-relative .md path without traversal, absolute/drive paths, or symlink/junction escape.")
            else:
                self.artifact_paths[role] = resolved
        self.report["checks_run"].append("registered_artifact_path_scope")

    def run(self):
        for kind, record, path in self.entries:
            identifier = record["id"]
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,63}", identifier):
                self.add("ID_INVALID", path + ".id", "Stable ID must start with a letter and contain at most 64 identifier characters.")
            if identifier in self.index:
                self.add("ID_DUPLICATE", path + ".id", "ID is duplicated across registers: " + identifier)
            else:
                self.index[identifier] = (kind, record, path)
        for filename, content in self.files.items():
            if content["version"] != self.state["version"]:
                self.add("VERSION_MISMATCH", filename + ".version", "Input register does not match state.version.")
        self.gate_changes()
        self.resolve_artifacts()
        for gate, confirmation in self.state["gates"].items():
            if gate in ("G1", "G2", "G3"):
                self.confirmation(confirmation, "state.json.gates." + gate, gate)
        if self.state["status"] == "PAUSED_BY_USER" and not self.source_valid(self.state.get("pause_source"), "STATE", "PAUSE"):
            self.add("PAUSE_SOURCE_INVALID", "state.json.pause_source", "PAUSED_BY_USER requires a recorded user pause request scoped to STATE.")
        links = {"affected_ids": None, "evidence_ids": {"EVIDENCE"}, "supported_claim_ids": {"CLAIM"}, "challenged_claim_ids": {"CLAIM"},
                 "dataset_ids": {"DATASET"}, "method_ids": {"METHOD"}, "experiment_ids": {"EXPERIMENT"},
                 "claim_ids": {"CLAIM"}, "metric_ids": {"METRIC"}, "task_ids": {"TASK"}, "depends_on": {"TASK"},
                 "config_ids": {"CONFIG"}, "execution_evidence_ids": {"EVIDENCE"}}
        for kind, record, path in self.entries:
            permitted_fields = (PLAN_RECORD_SCHEMAS[kind]["properties"] if kind in PLAN_RECORD_SCHEMAS else
                                {"CONSTRAINT": CONSTRAINT, "EVIDENCE": EVIDENCE, "DATASET": DATASET, "UNKNOWN": UNKNOWN, "CHANGE": GATE_CHANGE}[kind]["properties"])
            for field, expected in links.items():
                if field in permitted_fields and field in record:
                    self.ref(record[field], expected, path + "." + field)
            if kind == "CONFIG":
                self.ref([record["method_id"]], {"METHOD"}, path + ".method_id")
            if kind == "BUDGET":
                self.ref([record["config_id"]], {"CONFIG"}, path + ".config_id")
                if record["profile_task_id"] is not None:
                    self.ref([record["profile_task_id"]], {"TASK"}, path + ".profile_task_id")
            status = record["status"] if kind == "UNKNOWN" else record.get("evidence_status") if "evidence_status" in permitted_fields else None
            if status in ("UNKNOWN", "CONFLICTED", "PROVISIONAL"):
                self.add("REGISTERED_UNKNOWN", path, "Registered uncertainty remains; its evidence and impact need review.", "needs_review")
                if self.ready and record.get("impact") == "CRITICAL_SCIENTIFIC":
                    self.add("READY_CRITICAL_UNKNOWN", path, "Explicit critical-scientific UNKNOWN, CONFLICTED, or PROVISIONAL feasibility is incompatible with READY_FOR_HANDOFF.")
            if kind == "EVIDENCE" and record["evidence_status"] == "VERIFIED":
                verification = record["verification"]
                if not verification or not all(verification[field].strip() for field in ("scope", "location", "checked_at")):
                    self.add("VERIFICATION_SCOPE_MISSING", path, "VERIFIED needs an explicit checked scope, source location, and date.")
            if kind == "CONSTRAINT":
                self.confirmation(record["user_confirmation"], path + ".user_confirmation", record["id"])
        for name, section in self.files["plan-contract.json"]["sections"].items():
            if name in SECTIONS:
                self.ref(section["ref_ids"], None, "plan-contract.json.sections." + name + ".ref_ids")
        self.report["checks_run"] += ["stable_ids", "versions", "foreign_keys", "confirmation_sources", "registered_unknowns"]
        self.dependencies()
        self.data_and_methods()
        self.tasks_and_budget()
        self.constraints()
        self.readiness()

    def dependencies(self):
        graph = {record["id"]: record["depends_on"] for record, _ in self.records("TASK")}
        # Kahn traversal avoids recursion limits on large valid task graphs.
        indegree = {identifier: len(set(dep for dep in dependencies if dep in graph)) for identifier, dependencies in graph.items()}
        followers = {identifier: [] for identifier in graph}
        for identifier, dependencies in graph.items():
            for dependency in set(dependencies):
                if dependency in followers:
                    followers[dependency].append(identifier)
        queue = [identifier for identifier, count in indegree.items() if count == 0]
        count = 0
        while queue:
            identifier = queue.pop()
            count += 1
            for follower in followers[identifier]:
                indegree[follower] -= 1
                if indegree[follower] == 0:
                    queue.append(follower)
        if count != len(graph):
            self.add("TASK_DEPENDENCY_CYCLE", "plan-contract.json.records", "Registered task dependencies contain a cycle.")
        self.report["checks_run"].append("task_dependencies")

    def data_and_methods(self):
        datasets = self.records("DATASET")
        for record, path in datasets:
            if record["role"] == "EXTERNAL_TEST" and set(record["uses"]) & {"TRAIN", "TUNE", "CALIBRATE", "THRESHOLD"}:
                self.add("EXTERNAL_TEST_LEAKAGE", path + ".uses", "A declared final external test cannot train, tune, calibrate, or select thresholds.")
            if not record.get("group_ids"):
                self.add("INDEPENDENCE_UNVERIFIED", path + ".group_ids", "Observed group identifiers are absent; independence is not demonstrated.", "needs_review")
            elif len(record["group_ids"]) != len(set(record["group_ids"])):
                self.add("GROUP_IDS_DUPLICATE", path + ".group_ids", "Repeated within-cohort groups require aggregation/split review.", "needs_review")
        for number, (left, left_path) in enumerate(datasets):
            for right, right_path in datasets[number + 1:]:
                if left.get("group_ids") and right.get("group_ids") and set(left["group_ids"]) & set(right["group_ids"]):
                    if left["role"] != right["role"] or left["role"] in ("INTERNAL_TEST", "EXTERNAL_TEST"):
                        self.add("DATA_GROUP_OVERLAP", right_path + ".group_ids", "Observed group identifiers overlap across declared separate data roles/cohorts: " + left["id"] + " and " + right["id"] + ".")
                    else:
                        self.add("SOURCE_OVERLAP_REVIEW", right_path, "Same-role datasets share observed groups; independent-source counting needs review.", "needs_review")
        for method, path in self.records("METHOD"):
            for identifier in method["dataset_ids"]:
                target = self.index.get(identifier)
                if target and target[0] == "DATASET" and not set(method["required_inference_inputs"]).issubset(target[1]["available_inputs"]):
                    self.add("INFERENCE_INPUT_UNAVAILABLE", path + ".required_inference_inputs", "Required use-time inputs are not a subset of available inputs for dataset " + identifier + ".")
        self.report["checks_run"] += ["declared_data_roles", "observed_group_overlap", "inference_input_availability"]

    def tasks_and_budget(self):
        required_configs = set()
        unconfigured_tasks = []
        for task, path in self.records("TASK"):
            for item in task["inputs"]:
                self.ref([item["ref_id"]], None, path + ".inputs")
                target = self.index.get(item["ref_id"])
                if task["kind"] == "TRAINING" and target and target[0] == "DATASET" and target[1]["role"] == "EXTERNAL_TEST":
                    self.add("EXTERNAL_TEST_LEAKAGE", path + ".inputs", "A training task explicitly consumes a declared final external test dataset.")
            complete = (task["scientific_purpose"].strip() and task["claim_ids"] and task["inputs"] and task["outputs"]
                        and task["scope"].strip() and task["acceptance"] and task["failure_handling"].strip() and task["stop_conditions"])
            complete = complete and all(item["schema"].strip() for item in task["inputs"])
            complete = complete and all(item["path"].strip() and item["schema"].strip() for item in task["outputs"])
            complete = complete and all(text.strip() for text in task["acceptance"] + task["stop_conditions"])
            if not complete:
                self.add("TASK_CONTRACT_INCOMPLETE", path, "Task needs a scientific purpose/claim, input/output schemas, scope, acceptance, failure handling, and stop conditions.")
            if task["kind"] in ("TRAINING", "ANALYSIS"):
                if not task["config_ids"]:
                    self.add("TASK_CONFIG_REQUIRED", path + ".config_ids", "Every training/analysis task needs explicit configuration IDs for budget coverage.")
            if task["kind"] in ("TRAINING", "ANALYSIS", "EVALUATION", "PROFILING"):
                required_configs.update(task["config_ids"])
                if not task["config_ids"]:
                    unconfigured_tasks.append(task["id"])
                    if task["kind"] in ("EVALUATION", "PROFILING"):
                        self.add("TASK_BUDGET_CONFIG_UNSPECIFIED", path + ".config_ids", "Evaluation/profiling configuration is not yet registered; cost completeness needs review.", "needs_review")
            command = task["command"]
            if command["status"] != task["execution_status"]:
                self.add("EXECUTION_STATUS_CONFLICT", path + ".command.status", "Command and task execution statuses disagree.")
            if command["status"] == "PLANNED" and command["executable"]:
                self.add("PLANNED_COMMAND_EXECUTABLE", path + ".command", "A future PLANNED command must not claim an executable implementation.")
            if not command["text"].strip():
                self.add("COMMAND_CONTRACT_EMPTY", path + ".command.text", "A registered task needs a nonempty future/existing command contract.")
            authorized = task["authorization_status"] == "AUTHORIZED" and self.source_valid(task["authorization_source"], task["id"], "AUTHORIZE_EXECUTION")
            if task["authorization_status"] == "AUTHORIZED" and not authorized:
                self.add("EXECUTION_AUTH_SOURCE_INVALID", path + ".authorization_source", "Execution authorization needs separate scoped user provenance.")
            if task["execution_status"] in ("EXECUTED_UNVERIFIED", "EXECUTED_VERIFIED"):
                if not authorized:
                    self.add("EXECUTION_NOT_AUTHORIZED", path, "Scientific gate confirmation does not authorize execution.")
                if not command["executable"] or not task["execution_evidence_ids"]:
                    self.add("EXECUTION_EVIDENCE_MISSING", path, "Executed tasks need an implemented command and separately registered execution evidence.")
                if task["execution_status"] == "EXECUTED_VERIFIED":
                    for identifier in task["execution_evidence_ids"]:
                        evidence = self.index.get(identifier)
                        if evidence and evidence[0] == "EVIDENCE" and evidence[1]["evidence_status"] != "VERIFIED":
                            self.add("EXECUTION_VERIFICATION_CONFLICT", path, "EXECUTED_VERIFIED cites evidence that is not VERIFIED.")
        covered = set()
        total_lower = total_upper = 0
        known_total = True
        for budget, path in self.records("BUDGET"):
            if budget["config_id"] in covered:
                self.add("BUDGET_CONFIG_DUPLICATE", path, "Use one aggregate budget row per configuration to avoid double counting.")
                known_total = False
            covered.add(budget["config_id"])
            if budget["runs"] < 1:
                self.add("BUDGET_RUNS_INVALID", path + ".runs", "Maximum planned run count must be a positive integer.")
                known_total = False
            has_unknown = False
            for field in ("duration_hours", "memory_gb"):
                interval = budget[field]
                if interval["lower"] is None or interval["upper"] is None:
                    has_unknown = True
                elif interval["lower"] < 0 or interval["upper"] < interval["lower"]:
                    self.add("BUDGET_INTERVAL_INVALID", path + "." + field, "Budget bounds must be nonnegative and ordered lower <= upper.")
                    known_total = False
            if budget["measurement_status"] == "UNKNOWN" or has_unknown or not budget["basis"].strip():
                self.add("BUDGET_UNKNOWN", path, "Resource forecast is unresolved; retain its rationale and future profiling task.", "needs_review")
                if budget["measurement_status"] != "UNKNOWN" or not has_unknown:
                    self.add("BUDGET_STATUS_CONFLICT", path, "UNKNOWN forecast needs null bounds; missing bounds need UNKNOWN status.")
                if not budget["basis"].strip():
                    self.add("BUDGET_RATIONALE_MISSING", path + ".basis", "Unknown forecasts still need an honest reason for missing evidence.")
                profile = self.index.get(budget["profile_task_id"])
                if not profile or profile[0] != "TASK" or profile[1]["kind"] != "PROFILING":
                    self.add("BUDGET_PROFILE_REQUIRED", path + ".profile_task_id", "Unknown forecasts need an explicit future PROFILING task.")
                if self.ready and budget["impact"] == "CRITICAL_SCIENTIFIC":
                    self.add("READY_CRITICAL_UNKNOWN", path, "Explicit critical-scientific budget unknown blocks handoff.")
            duration = budget["duration_hours"]
            if duration["lower"] is None or duration["upper"] is None:
                known_total = False
            else:
                total_lower += budget["runs"] * duration["lower"]
                total_upper += budget["runs"] * duration["upper"]
        missing_configs = required_configs - covered
        for identifier in sorted(missing_configs):
            self.add("BUDGET_MISSING_CONFIG", "plan-contract.json.records", "Budget ledger omits an explicit training/analysis/evaluation/profiling configuration " + identifier + ".")
        complete = not missing_configs and not unconfigured_tasks
        self.report["budget_config_coverage"] = {"required_ids": sorted(required_configs), "covered_ids": sorted(covered),
                                                 "missing_ids": sorted(missing_configs), "unconfigured_task_ids": sorted(unconfigured_tasks), "complete": complete}
        self.report["budget_total_hours"] = {"lower": total_lower, "upper": total_upper} if known_total and complete else None
        self.report["checks_run"] += ["task_scientific_contract", "planned_and_executed_status", "budget_config_coverage", "budget_intervals"]

    def constraints(self):
        for constraint, path in self.records("CONSTRAINT"):
            rule = constraint["validation"]
            if rule is None:
                self.add("CONSTRAINT_MANUAL_REVIEW", path + ".validation", "No explicit machine rule is registered for this constraint.", "needs_review")
                continue
            if rule["rule_type"] == "QUANTITY":
                self.ref(rule["target_ids"], {rule["record_type"]}, path + ".validation.target_ids")
                actual = len(set(identifier for identifier in rule["target_ids"] if identifier in self.index and self.index[identifier][0] == rule["record_type"]))
                if rule["value"] < 0:
                    self.add("QUANTITY_RULE_INVALID", path, "Quantity threshold cannot be negative.")
            else:
                actual = rule["actual"]
                if actual is None:
                    self.add("NUMBER_UNKNOWN", path + ".validation.actual", "Registered numeric rule lacks an actual value; it has not passed.", "needs_review")
                    if self.ready and constraint["kind"] == "HARD":
                        self.add("READY_HARD_RULE_UNRESOLVED", path, "An unresolved explicitly registered HARD numeric rule blocks READY.")
                    continue
            passed = actual >= rule["value"] if rule["operator"] == "MIN" else actual <= rule["value"] if rule["operator"] == "MAX" else actual == rule["value"]
            if not passed:
                hard = constraint["kind"] == "HARD"
                code = rule["rule_type"] + ("_HARD_UNMET" if hard else "_TARGET_UNMET")
                self.add(code, path + ".validation", "Explicit registered threshold is not satisfied; revise the plan or seek a recorded change.", "errors" if hard else "warnings")
        self.report["checks_run"].append("registered_quantity_and_numeric_rules")

    def readiness(self):
        if not self.ready:
            self.add("SCIENTIFIC_READY_NOT_ASSERTED", "state.json.status", "Structural pass does not advance ACTIVE/PROVISIONAL/PAUSED state or confirm any gate.", "needs_review")
        else:
            if self.state["stage"] != "HANDOFF":
                self.add("READY_STAGE_INVALID", "state.json.stage", "READY_FOR_HANDOFF requires the HANDOFF stage.")
            for gate in ("G1", "G2", "G3"):
                if self.state["gates"][gate]["status"] != "CONFIRMED":
                    self.add("READY_GATE_UNCONFIRMED", "state.json.gates." + gate, "Every science gate must have applicable genuine registered CONFIRMED provenance, current or explicitly carried.")
            for role, path in self.artifact_paths.items():
                try:
                    artifact_nonempty = path.is_file() and bool(path.read_text(encoding="utf-8-sig").strip())
                except (OSError, UnicodeError):
                    artifact_nonempty = False
                if not artifact_nonempty:
                    code = "READY_SESSION_MISSING" if role == "session" else "READY_ARTIFACT_MISSING"
                    self.add(code, "state.json.artifacts." + role, "READY requires a readable, nonempty final artifact for " + role + ".")
            required = ("CONSTRAINT", "EVIDENCE", "DATASET", "METHOD", "CLAIM", "EXPERIMENT", "METRIC", "TASK")
            for kind in required:
                if not self.records(kind):
                    self.add("READY_REGISTER_EMPTY", "registers." + kind, "READY requires substantive records for " + kind + ".")
            sections = self.files["plan-contract.json"]["sections"]
            for name in SECTIONS:
                section = sections.get(name)
                if not section or not section["summary"].strip() or not section["ref_ids"]:
                    self.add("READY_SECTION_INCOMPLETE", "plan-contract.json.sections." + name, "Required section needs nonempty scientific summary and registered references.")
            fields_by_kind = {"CONSTRAINT": ("statement", "category"), "EVIDENCE": ("title",), "DATASET": ("name", "version", "available_inputs", "evidence_ids", "independence_unit"),
                              "METHOD": ("name", "purpose", "dataset_ids", "required_inference_inputs"), "CLAIM": ("statement", "method_ids", "experiment_ids", "falsification"),
                              "EXPERIMENT": ("purpose", "claim_ids", "method_ids", "dataset_ids", "metric_ids", "task_ids"),
                              "METRIC": ("name", "target", "definition", "unit", "aggregation", "uncertainty"), "CONFIG": ("settings",)}
            for kind, fields in fields_by_kind.items():
                for record, path in self.records(kind):
                    if any(not record[field] or (isinstance(record[field], str) and not record[field].strip()) for field in fields):
                        self.add("READY_RECORD_INCOMPLETE", path, "READY requires substantive core fields, not empty record shells.")
            if self.records("METRIC") and not any(record["primary"] for record, _ in self.records("METRIC")):
                self.add("READY_PRIMARY_METRIC_MISSING", "plan-contract.json.records", "Declare at least one primary evaluation metric/estimand.")
        self.report["checks_run"].append("registered_handoff_readiness")


def output_protected(project, output, extra_paths=()):
    target = output.resolve()
    for source in [project / name for name in PROTECTED_FILES] + list(extra_paths):
        if os.path.normcase(str(source.resolve())) == os.path.normcase(str(target)):
            return True
        try:
            if output.exists() and source.exists() and os.path.samefile(output, source):
                return True
        except OSError:
            pass
    return False


def atomic_report(output, report, force):
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=".validate-plan-", suffix=".tmp", dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(report, handle, ensure_ascii=False, allow_nan=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if force:
            os.replace(temporary, output)
        else:
            # Atomic no-clobber publish; a competing report writer cannot be overwritten.
            os.link(temporary, output)
        if temporary.exists():
            temporary.unlink()
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_directory", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true", help="Explicitly replace an existing report, never an input.")
    arguments = parser.parse_args(argv)
    try:
        project = arguments.project_directory.resolve()
        output = arguments.output.absolute()
        protected = output_protected(project, output)
    except (OSError, RuntimeError) as error:
        print("PATH_RESOLUTION_FAILED: " + type(error).__name__ + "; no report or input was replaced.", file=sys.stderr)
        return 2
    if protected:
        print("OUTPUT_INPUT_COLLISION: report destination aliases a protected project input.", file=sys.stderr)
        return 2
    if output.exists() and not arguments.force:
        print("OUTPUT_EXISTS: choose a new report path or explicitly use --force.", file=sys.stderr)
        return 2
    report = {"schema_version": SCHEMA_VERSION, "checked_at": datetime.now(timezone.utc).isoformat(), "input_version": None,
              "structural_status": "OPERATIONAL_ERROR", "errors": [], "warnings": [], "needs_review": [],
              "checks_run": [], "checks_skipped": ["source_authentication", "scientific_validity", "natural_language_consistency", "real_resource_feasibility", "command_executability"],
              "limitations": LIMITATIONS.copy()}
    report["needs_review"].append(issue("SCIENTIFIC_REVIEW_REQUIRED", "project", "Inspect the actual sources, user confirmations, scientific design, and the final main document; structural checks alone do not establish them."))
    try:
        files = read_inputs(project, report)
        if output_protected(project, output, registered_artifact_paths(project, files.get("state.json"))):
            print("OUTPUT_INPUT_COLLISION: report destination aliases a registered project artifact, even if another input/schema failed.", file=sys.stderr)
            return 2
        if report["errors"]:
            code = 2
            report["checks_skipped"].append("registered_relationship_rules_due_to_invalid_input")
        else:
            rules = Rules(files, project, report)
            rules.run()
            if output_protected(project, output, rules.artifact_paths.values()):
                print("OUTPUT_INPUT_COLLISION: report destination aliases a registered project artifact.", file=sys.stderr)
                return 2
            code = 1 if report["errors"] else 0
            report["structural_status"] = "FAIL" if code else "PASS"
    except (RecursionError, OverflowError, ValueError, OSError) as error:
        report["errors"].append(issue("INPUT_PROCESSING_FAILED", "project", type(error).__name__ + ": malformed or unsupported input."))
        code = 2
        report["structural_status"] = "OPERATIONAL_ERROR"
    try:
        atomic_report(output, report, arguments.force)
    except (OSError, ValueError, OverflowError) as error:
        print("OUTPUT_WRITE_FAILED: " + type(error).__name__ + "; existing reports and inputs are preserved.", file=sys.stderr)
        return 2
    # ASCII summary is safe on legacy Windows console code pages; JSON is UTF-8.
    print(report["structural_status"] + ": explicit registered structure only; report=" + str(output).encode("ascii", "backslashreplace").decode("ascii"))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
