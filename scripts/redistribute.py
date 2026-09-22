#!/usr/bin/env python3
"""Applica la redistribuzione delle skill definita in config/redistribution.yaml.

Uso:
    python3 scripts/redistribute.py            # applica (idempotente)
    python3 scripts/redistribute.py --dry-run  # mostra solo le modifiche
    python3 scripts/redistribute.py --report   # rigenera REDISTRIBUTION.md

Modello generico: ogni harness nel config ha un `type` (back-end) + i suoi path.
Aggiungere un harness path-based = solo una voce nel config (nessun codice nuovo).
Serve codice nuovo solo se l'harness richiede la riscrittura di un proprio file di
config (come il `type: openclaw`, che aggiorna agents.entries.<a>.skills).
"""
import argparse
import collections
import datetime
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DEFAULT = os.path.join(ROOT, "config", "redistribution.yaml")
IGNORE_DIRS = {".git", "_sources", "config", "scripts", "docs", "trash"}


# ---------------------------------------------------------------- config/store
def load_config(path):
    try:
        import yaml
    except ImportError:
        sys.exit("Serve PyYAML: pip install pyyaml")
    with open(path) as fh:
        return yaml.safe_load(fh)


def categories(store):
    return [c for c in sorted(os.listdir(store))
            if not c.startswith((".", "_")) and c not in IGNORE_DIRS
            and os.path.isdir(os.path.join(store, c))]


def store_map(store):
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


# ------------------------------------------------------------------- back-end
def apply_flat(target_dir, names, smap, store, dry=False):
    """Symlink piatti: <target_dir>/<skill> -> <store>/<cat>/<skill>."""
    os.makedirs(target_dir, exist_ok=True)
    added = removed = 0
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
            continue  # directory nativa: non tocco
        else:
            if not dry:
                os.symlink(tgt, fp)
            added += 1
    return added, removed


def apply_categorized(target_dir, names, smap, store, dry=False):
    """Symlink per categoria: <target_dir>/<store_cat>/<skill> (layout Hermes)."""
    names = set(names)
    added = removed = fixed = 0
    for cat in list(os.listdir(target_dir)):
        cp = os.path.join(target_dir, cat)
        if not os.path.isdir(cp):
            continue
        for entry in list(os.listdir(cp)):
            fp = os.path.join(cp, entry)
            if os.path.islink(fp) and os.path.basename(fp) not in names:
                if not dry:
                    os.remove(fp)
                removed += 1
    for n in names:
        want = os.path.join(store, smap[n], n)
        found = None
        for c in os.listdir(target_dir):
            fp = os.path.join(target_dir, c, n)
            if os.path.lexists(fp):
                found = fp
                break
        if found is None:
            cat = smap[n]
            os.makedirs(os.path.join(target_dir, cat), exist_ok=True)
            if not dry:
                os.symlink(want, os.path.join(target_dir, cat, n))
            added += 1
        elif os.path.islink(found) and os.readlink(found) != want:
            if not dry:  # symlink punta al posto sbagliato o dangling: ripara
                os.remove(found)
                os.symlink(want, found)
            fixed += 1
    return added + fixed, removed


def apply_openclaw(hcfg, cats, smap, store, all_store, dry=False):
    """Pool condiviso (flat) + riscrittura agents.entries.<a>.skills."""
    per_agent = {a: expand(v, cats, smap) for a, v in hcfg.get("agents", {}).items()}
    pool = sorted(set(sum(per_agent.values(), [])))
    res = {}
    for key in ("skills_dir", "library_dir"):
        if hcfg.get(key):
            res[key] = apply_flat(os.path.expanduser(hcfg[key]), pool, smap, store, dry)
    cfg_path = os.path.expanduser(hcfg["config"])
    with open(cfg_path) as fh:
        cfg = json.load(fh)
    entries = cfg["agents"]["entries"]
    for agent, names in per_agent.items():
        if agent not in entries:
            print(f"    WARN: agente '{agent}' assente in {cfg_path}")
            continue
        bundled = [x for x in entries[agent].get("skills", []) if x not in all_store]
        final = bundled + sorted(set(names))
        if entries[agent].get("skills") != final:
            if not dry:
                entries[agent]["skills"] = final
            res[f"agent:{agent}"] = (len(bundled), len(set(names)))
    if not dry and any(k.startswith("agent:") for k in res):
        shutil.copy2(cfg_path, cfg_path + ".bak-redistribute")
        with open(cfg_path, "w") as fh:
            json.dump(cfg, fh, indent=2)
    return res


BACKENDS = {"flat": None, "categorized": None, "openclaw": None}


# ---------------------------------------------------------------------- report
def build_report(cfg, smap, cats):
    harnesses = cfg["harnesses"]
    assigned = collections.defaultdict(set)
    per_harness = {}
    for hname, hcfg in harnesses.items():
        if hcfg["type"] == "openclaw":
            agents = {a: expand(v, cats, smap) for a, v in hcfg.get("agents", {}).items()}
            per_harness[hname] = agents
            for a, names in agents.items():
                for n in names:
                    assigned[n].add(f"{hname}.{a}")
        else:
            names = expand(hcfg.get("skills", []), cats, smap)
            per_harness[hname] = {"*": names}
            for n in names:
                assigned[n].add(hname)

    def by_cat(names):
        g = collections.defaultdict(list)
        for n in names:
            g[smap[n]].append(n)
        return g

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    L = ["# Skill Redistribution", "",
         f"_Generato da `scripts/redistribute.py --report` il {ts} — fonte: `config/redistribution.yaml`_", "",
         "## Store per categoria", "", "| Categoria | # | Skill |", "|---|---|---|"]
    for cat in cats:
        ns = sorted([n for n, c in smap.items() if c == cat])
        L.append(f"| `{cat}` | {len(ns)} | {', '.join(ns)} |")
    L += ["", f"**Totale store: {len(smap)} skill**", "", "## Agenti", "", "| Agente | # |", "|---|---|"]
    for hname, agents in per_harness.items():
        for a, names in agents.items():
            label = f"{hname}.{a}" if a != "*" else hname
            L.append(f"| {label} | {len(names)} |")
    L += ["", "## Dettaglio", ""]
    for hname, agents in per_harness.items():
        for a, names in agents.items():
            L.append(f"### {hname}.{a}" if a != "*" else f"### {hname}")
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
        htype = hcfg["type"]
        if htype == "flat":
            a, r = apply_flat(os.path.expanduser(hcfg["skills_dir"]),
                              expand(hcfg["skills"], cats, smap), smap, store, args.dry_run)
            print(f"  [{hname}:flat] +{a} -{r}")
        elif htype == "categorized":
            a, r = apply_categorized(os.path.expanduser(hcfg["skills_dir"]),
                                     expand(hcfg["skills"], cats, smap), smap, store, args.dry_run)
            print(f"  [{hname}:categorized] +{a} -{r}")
        elif htype == "openclaw":
            res = apply_openclaw(hcfg, cats, smap, store, all_store, args.dry_run)
            for k, v in res.items():
                print(f"  [{hname}:{k}] {v}")
        else:
            sys.exit(f"type sconosciuto: '{htype}' (harness {hname})")
    print("OK")


if __name__ == "__main__":
    main()
