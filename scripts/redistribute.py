#!/usr/bin/env python3
"""Motore generico di redistribuzione skill.

Legge UNA fonte di verita' (`config/redistribution.yaml`) e la applica a N harness,
distribuendo le skill dello store (via symlink o riscrivendo la config dell'harness).

Backend (registry `BACKENDS`): ogni harness dichiara un `type`.
    flat         symlink piatti:  <skills_dir>/<skill>
    categorized  symlink per categoria:  <skills_dir>/<store_cat>/<skill>
    json_list    riscrive una lista in un file JSON (dichiarativo, nessun codice)
    openclaw     preset: pool flat (skills_dir + library_dir) + per-agente su JSON

Aggiungere un harness path-based (flat/categorized/json_list) = solo una voce di
config, nessun codice. Un nuovo backend serve solo per una NUOVA forma di layout.

Uso:
    python3 scripts/redistribute.py            # applica (idempotente)
    python3 scripts/redistribute.py --dry-run  # mostra solo le modifiche (non scrive)
    python3 scripts/redistribute.py --report   # rigenera REDISTRIBUTION.md
"""
import argparse
import collections
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DEFAULT = os.path.join(ROOT, "config", "redistribution.yaml")
IGNORE_DIRS = {".git", "_sources", "config", "scripts", "docs", "trash", "examples", "tests"}
BACKUP_SUFFIX = ".bak-redistribute"


# ---------------------------------------------------------------- config/store
def load_config(path):
    """Carica il config YAML (richiede PyYAML)."""
    try:
        import yaml
    except ImportError:
        sys.exit("Serve PyYAML: pip install pyyaml")
    with open(path) as fh:
        return yaml.safe_load(fh)


def categories(store):
    """Le categorie dello store = sottocartelle reali, esclusi i meta-dir."""
    return [c for c in sorted(os.listdir(store))
            if not c.startswith((".", "_")) and c not in IGNORE_DIRS
            and os.path.isdir(os.path.join(store, c))]


def store_map(store):
    """Mappa skill -> categoria per tutte le skill dello store."""
    out = {}
    for cat in categories(store):
        for name in os.listdir(os.path.join(store, cat)):
            out[name] = cat
    return out


def expand(entries, cats, smap):
    """`cat:<nome>` = categoria intera; altrimenti nome di skill puntuale."""
    out = []
    for e in entries or []:
        if e.startswith("cat:"):
            c = e[4:]
            if c not in cats:
                sys.exit(f"Categoria sconosciuta nel config: '{c}'")
            out += [n for n, cc in smap.items() if cc == c]
        elif e in smap:
            out.append(e)
        else:
            sys.exit(f"Skill sconosciuta nel config: '{e}'")
    return sorted(set(out))


# -------------------------------------------------------------- json primitive
def rewrite_json_list(path, pointer, names, preserve, dry=False):
    """Riscrive la lista puntata da `pointer` (dot-path) in `path` come
    `[voci preservate] + sorted(names non gia' presenti)`.

    `preserve(item) -> bool` decide quali voci esistenti tenere.
    Ritorna True se il file cambierebbe (o e' cambiato). Con `dry` non scrive.
    """
    with open(path) as fh:
        data = json.load(fh)
    keys = pointer.split(".")
    node = data
    for k in keys[:-1]:
        node = node[k]
    old = list(node.get(keys[-1], []))
    kept = [x for x in old if preserve(x)]
    new = kept + sorted(set(names) - set(kept))
    if new == old:
        return False
    if not dry:
        node[keys[-1]] = new
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)
    return True


def _preserve_fn(hcfg, all_store):
    """Risolve la regola `preserve` del config in una funzione."""
    mode = hcfg.get("preserve", "not_in_store")
    if callable(mode):
        return mode
    if mode == "none":
        return lambda _x: False
    if mode == "not_in_store":
        return lambda x: x not in all_store
    sys.exit(f"preserve sconosciuto: '{mode}'")


# ------------------------------------------------------------------- back-end
def apply_flat(target_dir, names, smap, store, dry=False):
    """Symlink piatti: <target_dir>/<skill> -> <store>/<cat>/<skill>."""
    exists = os.path.isdir(target_dir)
    if not dry:
        os.makedirs(target_dir, exist_ok=True)
    added = removed = 0
    if exists:
        for existing in list(os.listdir(target_dir)):
            fp = os.path.join(target_dir, existing)
            if os.path.islink(fp) and existing not in names:
                if not dry:
                    os.remove(fp)
                removed += 1
    for n in names:
        fp = os.path.join(target_dir, n)
        tgt = os.path.join(store, smap[n], n)
        if os.path.islink(fp):
            if os.readlink(fp) != tgt:
                if not dry:
                    os.remove(fp)
                    os.symlink(tgt, fp)
                added += 1
        elif os.path.exists(fp):
            continue  # directory nativa: non tocchiamo
        else:
            if not dry:
                os.symlink(tgt, fp)
            added += 1
    return added, removed


def apply_categorized(target_dir, names, smap, store, dry=False):
    """Symlink per categoria: <target_dir>/<store_cat>/<skill>."""
    names = set(names)
    added = removed = 0
    if os.path.isdir(target_dir):
        for cat in list(os.listdir(target_dir)):
            cp = os.path.join(target_dir, cat)
            if not os.path.isdir(cp):
                continue
            for entry in list(os.listdir(cp)):
                fp = os.path.join(cp, entry)
                if os.path.islink(fp) and entry not in names:
                    if not dry:
                        os.remove(fp)
                    removed += 1
    for n in names:
        want = os.path.join(store, smap[n], n)
        found = None
        if os.path.isdir(target_dir):
            for c in os.listdir(target_dir):
                fp = os.path.join(target_dir, c, n)
                if os.path.lexists(fp):
                    found = fp
                    break
        if found is None:
            cat = smap[n]
            if not dry:
                os.makedirs(os.path.join(target_dir, cat), exist_ok=True)
                os.symlink(want, os.path.join(target_dir, cat, n))
            added += 1
        elif os.path.islink(found) and os.readlink(found) != want:
            if not dry:  # symlink al posto sbagliato o dangling: ripara
                os.remove(found)
                os.symlink(want, found)
            added += 1
    return added, removed


def _single_plan(hcfg, cats, smap):
    """Plan di flat/categorized: una sola lista, etichetta `*`."""
    return {"*": expand(hcfg.get("skills", []), cats, smap)}


def _flat_apply(hcfg, plan, smap, store, all_store, dry):
    a, r = apply_flat(os.path.expanduser(hcfg["skills_dir"]), plan["*"], smap, store, dry)
    return {"*": (a, r)}


def _categorized_apply(hcfg, plan, smap, store, all_store, dry):
    a, r = apply_categorized(os.path.expanduser(hcfg["skills_dir"]), plan["*"], smap, store, dry)
    return {"*": (a, r)}


def _specs(hcfg):
    """La forma dei target json_list: `lists:` (multi) oppure `pointer`+`skills`."""
    if hcfg.get("lists"):
        return hcfg["lists"]
    return [{"pointer": hcfg["pointer"], "skills": hcfg.get("skills", [])}]


def _label(pointer):
    """L'etichetta di un pointer: penultimo segmento (…entries.<a>.skills -> <a>)."""
    return pointer.split(".")[-2]


def _json_list_plan(hcfg, cats, smap):
    return {_label(s["pointer"]): expand(s.get("skills", []), cats, smap) for s in _specs(hcfg)}


def _json_list_apply(hcfg, plan, smap, store, all_store, dry):
    path = os.path.expanduser(hcfg["file"])
    preserve = _preserve_fn(hcfg, all_store)
    specs = _specs(hcfg)
    would = any(rewrite_json_list(path, s["pointer"], plan[_label(s["pointer"])],
                                  preserve, dry=True) for s in specs)
    if would and not dry and hcfg.get("backup", True):
        shutil.copy2(path, path + BACKUP_SUFFIX)
    res = {}
    for s in specs:
        label = _label(s["pointer"])
        names = plan[label]
        before = _count_added(path, s["pointer"], names, preserve)
        rewrite_json_list(path, s["pointer"], names, preserve, dry)
        after = _count_added(path, s["pointer"], names, preserve)
        res[label] = (after if dry else before, 0)
    return res


def _count_added(path, pointer, names, preserve):
    """Quante delle `names` sono (o sarebbero) presenti nella lista puntata."""
    with open(path) as fh:
        data = json.load(fh)
    node = data
    for k in pointer.split("."):
        node = node[k]
    return len(set(names) & set(node))


def _openclaw_plan(hcfg, cats, smap):
    """Preset OpenClaw: un plan per sub-agente da `agents:`."""
    return {a: expand(v, cats, smap) for a, v in hcfg.get("agents", {}).items()}


def _openclaw_apply(hcfg, plan, smap, store, all_store, dry):
    """Pool flat (skills_dir + library_dir) + riscrittura agents.entries.<a>.skills."""
    pool = sorted(set(sum(plan.values(), [])))
    res = {}
    for key in ("skills_dir", "library_dir"):
        if hcfg.get(key):
            res[key] = apply_flat(os.path.expanduser(hcfg[key]), pool, smap, store, dry)
    cfg_path = os.path.expanduser(hcfg["config"])
    preserve = _preserve_fn(hcfg, all_store)
    with open(cfg_path) as fh:
        entries = json.load(fh)["agents"]["entries"]
    targets = [a for a in plan if a in entries]
    for a in plan:
        if a not in entries:
            print(f"    WARN: agente '{a}' assente in {cfg_path}")
    would = any(rewrite_json_list(cfg_path, f"agents.entries.{a}.skills", plan[a], preserve, dry=True)
                for a in targets)
    if would and not dry:
        shutil.copy2(cfg_path, cfg_path + BACKUP_SUFFIX)
    for a in targets:
        ptr = f"agents.entries.{a}.skills"
        res[f"agent:{a}"] = (_count_added(cfg_path, ptr, plan[a], preserve), len(plan[a]))
        rewrite_json_list(cfg_path, ptr, plan[a], preserve, dry)
    return res


BACKENDS = {
    "flat": (_single_plan, _flat_apply),
    "categorized": (_single_plan, _categorized_apply),
    "json_list": (_json_list_plan, _json_list_apply),
    "openclaw": (_openclaw_plan, _openclaw_apply),
}


def plan(htype, hcfg, cats, smap):
    """Il plan di un harness: {etichetta -> [skill]}. Generico su tutti i backend."""
    if htype not in BACKENDS:
        sys.exit(f"type sconosciuto: '{htype}'")
    return BACKENDS[htype][0](hcfg, cats, smap)


def apply_harness(htype, hcfg, cats, smap, store, all_store, dry=False):
    """Applica un harness. Ritorna {etichetta -> (added, removed)}."""
    if htype not in BACKENDS:
        sys.exit(f"type sconosciuto: '{htype}'")
    p = BACKENDS[htype][0](hcfg, cats, smap)
    return BACKENDS[htype][1](hcfg, p, smap, store, all_store, dry)


# ---------------------------------------------------------------------- report
def build_report(cfg, smap, cats):
    """Genera REDISTRIBUTION.md dai soli `plan()` (nessun ramo per-harness)."""
    harnesses = cfg["harnesses"]
    assigned = collections.defaultdict(set)
    per_harness = {}
    for hname, hcfg in harnesses.items():
        p = plan(hcfg["type"], hcfg, cats, smap)
        per_harness[hname] = p
        for label, names in p.items():
            full = f"{hname}.{label}" if label != "*" else hname
            for n in names:
                assigned[n].add(full)

    def by_cat(names):
        g = collections.defaultdict(list)
        for n in names:
            g[smap[n]].append(n)
        return g

    L = ["# Skill Redistribution", "",
         "_Generato da `scripts/redistribute.py --report` — fonte: `config/redistribution.yaml`_", "",
         "## Store per categoria", "", "| Categoria | # | Skill |", "|---|---|---|"]
    for cat in cats:
        ns = sorted([n for n, c in smap.items() if c == cat])
        L.append(f"| `{cat}` | {len(ns)} | {', '.join(ns)} |")
    L += ["", f"**Totale store: {len(smap)} skill**", "", "## Agenti", "", "| Agente | # |", "|---|---|"]
    for hname, agents in per_harness.items():
        for label, names in agents.items():
            full = f"{hname}.{label}" if label != "*" else hname
            L.append(f"| {full} | {len(names)} |")
    L += ["", "## Dettaglio", ""]
    for hname, agents in per_harness.items():
        for label, names in agents.items():
            L.append(f"### {hname}.{label}" if label != "*" else f"### {hname}")
            for cat, ns in sorted(by_cat(names).items()):
                L.append(f"- **{cat}** ({len(ns)}): {', '.join(ns)}")
            L.append("")
    L += ["## Skill condivise", ""]
    shared = {n: sorted(v) for n, v in assigned.items() if len(v) > 1}
    if shared:
        gp = collections.defaultdict(list)
        for n, who in shared.items():
            gp[" + ".join(who)].append(n)
        for pair, ns in gp.items():
            L.append(f"- **{pair}** — {len(ns)}: {', '.join(sorted(ns))}")
    else:
        L.append("(nessuna)")
    L += ["", "## Skill NON assegnate", ""]
    un = [n for n in smap if n not in assigned]
    L.append("**Nessuna**" if not un else "\n".join(f"- `{smap[n]}/{n}`" for n in un))
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=CONFIG_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    store = os.path.expanduser(cfg["store"])
    smap = store_map(store)
    cats = categories(store)
    all_store = set(smap)
    print(f"store: {store}  ({len(smap)} skill, {len(cats)} categorie)  dry_run={args.dry_run}")

    if args.report:
        out = os.path.join(ROOT, "REDISTRIBUTION.md")
        with open(out, "w") as fh:
            fh.write(build_report(cfg, smap, cats))
        print(f"report -> {out}")
        return

    for hname, hcfg in cfg["harnesses"].items():
        res = apply_harness(hcfg["type"], hcfg, cats, smap, store, all_store, args.dry_run)
        for label, val in res.items():
            print(f"  [{hname}:{label}] {val}")
    print("OK")


if __name__ == "__main__":
    main()
