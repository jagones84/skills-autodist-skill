"""Test del motore di redistribuzione (scripts/redistribute.py).

TDD: questi test definiscono l'interfaccia GENERICA del motore:
- registry dei backend (BACKENDS) + dispatch per nome (plan / apply_harness)
- backend dichiarativi: flat, categorized, json_list (+ preset openclaw)
- helper rewrite_json_list (riscrittura di una lista in un file JSON)
- report generato senza rami hardcoded per harness

Il modulo viene caricato dal path, senza installarlo.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("redistribute", ROOT / "scripts" / "redistribute.py")
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)


def make_store(tmp_path, layout=None):
    """Crea uno store sintetico: {"dev": ["a", "b"], "ops": ["c"]}."""
    layout = layout or {"dev": ["a", "b"], "ops": ["c"]}
    store = tmp_path / "store"
    for cat, skills in layout.items():
        for s in skills:
            d = store / cat / s
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("# " + s)
    return store


# ------------------------------------------------ store_map / categories / expand
def test_store_map_and_categories_ignore_meta_dirs(tmp_path):
    store = make_store(tmp_path)
    for meta in ("_sources", "config", "scripts", ".git", "trash", "docs"):
        (store / meta).mkdir()
    assert R.categories(str(store)) == ["dev", "ops"]
    assert R.store_map(str(store)) == {"a": "dev", "b": "dev", "c": "ops"}


def test_expand_category_prefix_and_single_name(tmp_path):
    smap = {"a": "dev", "b": "dev", "c": "ops"}
    cats = ["dev", "ops"]
    assert R.expand(["cat:ops", "a"], cats, smap) == ["a", "c"]
    assert R.expand([], cats, smap) == []


def test_expand_unknown_raises(tmp_path):
    with pytest.raises(SystemExit):
        R.expand(["ghost"], ["dev"], {"a": "dev"})


# --------------------------------------------------------------- backend: flat
def test_apply_flat_creates_symlinks_and_is_idempotent(tmp_path):
    store = make_store(tmp_path)
    smap = R.store_map(str(store))
    d = tmp_path / "flat"
    assert R.apply_flat(str(d), ["a", "b"], smap, str(store)) == (2, 0)
    assert (d / "a").is_symlink()
    assert os.readlink(d / "a") == str(store / "dev" / "a")
    assert R.apply_flat(str(d), ["a", "b"], smap, str(store)) == (0, 0)


def test_apply_flat_prunes_stale_and_keeps_native(tmp_path):
    store = make_store(tmp_path)
    smap = R.store_map(str(store))
    d = tmp_path / "flat"
    R.apply_flat(str(d), ["a", "b"], smap, str(store))
    (d / "native").mkdir()
    a, r = R.apply_flat(str(d), ["a"], smap, str(store))
    assert r == 1
    assert not (d / "b").exists()
    assert (d / "native").is_dir()


# --------------------------------------------------------- backend: categorized
def test_apply_categorized_places_and_repairs(tmp_path):
    store = make_store(tmp_path)
    smap = R.store_map(str(store))
    d = tmp_path / "cat"
    (d / "dev").mkdir(parents=True)
    os.symlink(str(tmp_path / "wrong"), d / "dev" / "a")
    added, removed = R.apply_categorized(str(d), ["a"], smap, str(store))
    assert added == 1
    assert os.readlink(d / "dev" / "a") == str(store / "dev" / "a")


# ---------------------------------------------------- helper: rewrite_json_list
def test_rewrite_json_list_preserves_and_is_idempotent(tmp_path):
    f = tmp_path / "cfg.json"
    f.write_text(json.dumps({"agents": {"entries": {"c": {"skills": ["bundled-1"]}}}}))
    changed = R.rewrite_json_list(
        str(f), "agents.entries.c.skills", ["a", "b"],
        preserve=lambda item: not item.startswith("st_"), dry=False)
    assert changed is True
    assert json.loads(f.read_text())["agents"]["entries"]["c"]["skills"] == ["bundled-1", "a", "b"]
    changed2 = R.rewrite_json_list(
        str(f), "agents.entries.c.skills", ["a", "b"],
        preserve=lambda item: not item.startswith("st_"), dry=False)
    assert changed2 is False


# ------------------------------------------------------------ backend: json_list
def test_json_list_backend_plan_and_apply(tmp_path):
    store = make_store(tmp_path)
    smap, cats = R.store_map(str(store)), R.categories(str(store))
    f = tmp_path / "cfg.json"
    f.write_text(json.dumps({"agents": {"entries": {"c": {"skills": []}, "r": {"skills": ["keep"]}}}}))
    hcfg = {
        "type": "json_list", "file": str(f), "preserve": "not_in_store",
        "lists": [
            {"pointer": "agents.entries.c.skills", "skills": ["cat:dev"]},
            {"pointer": "agents.entries.r.skills", "skills": ["c"]},
        ],
    }
    plan = R.plan("json_list", hcfg, cats, smap)
    assert plan == {"c": ["a", "b"], "r": ["c"]}
    R.apply_harness("json_list", hcfg, cats, smap, str(store), set(smap), False)
    data = json.loads(f.read_text())
    assert data["agents"]["entries"]["r"]["skills"] == ["keep", "c"]


# ----------------------------------------------------------- preset: openclaw
def test_openclaw_preset_pool_and_agents(tmp_path):
    store = make_store(tmp_path)
    smap, cats = R.store_map(str(store)), R.categories(str(store))
    cfg = tmp_path / "oc.json"
    cfg.write_text(json.dumps({"agents": {"entries": {"coder": {"skills": ["bundled"]}}}}))
    hcfg = {
        "type": "openclaw", "skills_dir": str(tmp_path / "pool"),
        "library_dir": str(tmp_path / "lib"), "config": str(cfg),
        "agents": {"coder": ["cat:dev"]},
    }
    R.apply_harness("openclaw", hcfg, cats, smap, str(store), set(smap), False)
    assert (tmp_path / "pool" / "a").is_symlink()
    assert (tmp_path / "lib" / "a").is_symlink()
    assert json.loads(cfg.read_text())["agents"]["entries"]["coder"]["skills"] == ["bundled", "a", "b"]


# ------------------------------------------------------------------- registry
def test_registry_has_all_backends_and_unknown_exits(tmp_path):
    for name in ("flat", "categorized", "json_list", "openclaw"):
        assert name in R.BACKENDS and R.BACKENDS[name] is not None
    store = make_store(tmp_path)
    smap, cats = R.store_map(str(store)), R.categories(str(store))
    with pytest.raises(SystemExit):
        R.apply_harness("ghost", {}, cats, smap, str(store), set(smap), True)


# --------------------------------------------------------------------- report
def test_build_report_generic_no_type_branch(tmp_path):
    store = make_store(tmp_path)
    smap, cats = R.store_map(str(store)), R.categories(str(store))
    cfg = {
        "version": 2, "store": str(store),
        "harnesses": {
            "oc": {"type": "openclaw", "skills_dir": str(tmp_path / "p"), "library_dir": "",
                   "config": str(tmp_path / "c.json"), "agents": {"coder": ["cat:dev"]}},
            "h": {"type": "flat", "skills_dir": str(tmp_path / "f"), "skills": ["a"]},
        },
    }
    (tmp_path / "c.json").write_text(json.dumps({"agents": {"entries": {"coder": {"skills": []}}}}))
    md = R.build_report(cfg, smap, cats)
    assert "oc.coder" in md
    assert "| h |" in md
    assert "NON assegnate" in md


# ------------------------------------------------------------------ end-to-end
def test_main_dry_run_writes_nothing(tmp_path, monkeypatch):
    store = make_store(tmp_path)
    cfgf = tmp_path / "cfg.yaml"
    cfgf.write_text(
        "version: 2\n"
        f"store: {store}\n"
        "harnesses:\n"
        "  h:\n"
        "    type: flat\n"
        f"    skills_dir: {tmp_path / 'flat'}\n"
        "    skills: [a, b]\n"
    )
    monkeypatch.setattr(sys, "argv", ["redistribute.py", "--config", str(cfgf), "--dry-run"])
    R.main()
    assert not (tmp_path / "flat").exists()


# --------------------------------------------------------- report deterministico
def test_build_report_has_no_volatile_timestamp(tmp_path, monkeypatch):
    store = make_store(tmp_path)
    smap, cats = R.store_map(str(store)), R.categories(str(store))
    cfg = {"version": 2, "store": str(store),
           "harnesses": {"h": {"type": "flat", "skills_dir": str(tmp_path / "f"), "skills": ["a"]}}}

    class _FakeDateTime:
        @staticmethod
        def now():
            import datetime as _d
            return _d.datetime(2001, 1, 1, 0, 0)

    class _FakeDatetimeModule:
        datetime = _FakeDateTime

    monkeypatch.setattr(R, "datetime", _FakeDatetimeModule, raising=False)
    md = R.build_report(cfg, smap, cats)
    assert "2001" not in md  # niente timestamp volatile: il report e' riproducibile


# ------------------------------------------------ openclaw: onora `preserve`
def test_openclaw_preset_honors_preserve_none(tmp_path):
    store = make_store(tmp_path)
    smap, cats = R.store_map(str(store)), R.categories(str(store))
    cfg = tmp_path / "oc.json"
    cfg.write_text(json.dumps({"agents": {"entries": {"coder": {"skills": ["bundled"]}}}}))
    hcfg = {"type": "openclaw", "skills_dir": str(tmp_path / "pool"), "library_dir": "",
            "config": str(cfg), "preserve": "none", "agents": {"coder": ["cat:dev"]}}
    R.apply_harness("openclaw", hcfg, cats, smap, str(store), set(smap), False)
    assert json.loads(cfg.read_text())["agents"]["entries"]["coder"]["skills"] == ["a", "b"]


