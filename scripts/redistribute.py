#!/usr/bin/env python3
"""Applica la redistribuzione delle skill definita in config/redistribution.yaml.

Uso:
    python3 scripts/redistribute.py            # applica (idempotente)
    python3 scripts/redistribute.py --dry-run  # mostra solo le modifiche
    python3 scripts/redistribute.py --report   # rigenera REDISTRIBUTION.md

Il file di config e' la FONTE DI VERITA': agenti -> categorie/skill.
Lo store (questa repo) e' il master; i runtime fanno symlink allo store.
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


def load_config(path):
    try:
        import yaml
    except ImportError:
        sys.exit("Serve PyYAML: pip install pyyaml (oppure usa il venv del progetto).")
    with open(path) as fh:
        return yaml.safe_load(fh)


IGNORE = {".git", "_sources", "config", "scripts", "docs", "trash"}


def categories(store):
    return [c for c in sorted(os.listdir(store))
            if not c.startswith((".", "_")) and c not in IGNORE
            and os.path.isdir(os.path.join(store, c))]


def store_map(store):
    mapping = {}
    for cat in categories(store):
        for name in os.listdir(os.path.join(store, cat)):
            mapping[name] = cat
    return mapping


def expand(entries, cats, smap):
    """Espande la lista di un agente. `cat:<nome>` = categoria intera; altrimenti skill."""
    out = []
    for e in entries or []:
        if e.startswith("cat:"):
            c = e[4:]
            if c not in cats:
                sys.exit(f"Categoria sconosciuta nel config: '{c}'")
            out += sorted([n for n, cc in smap.items() if cc == c])
        elif e in smap:
            out.append(e)
        else:
            sys.exit(f"Skill sconosciuta nel config: '{e}'")
    return sorted(set(out))


def sync_flat(target_dir, names, smap, store, dry=False, label=""):
    """Symlink piatti <target_dir>/<skill> -> store/<cat>/<skill>."""
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
    print(f"  [{label}] +{added} -{removed}  -> {target_dir}")


def sync_hermes(target_dir, names, smap, store, dry=False):
    """Hermes usa categorie: <target_dir>/<store_cat>/<skill>."""
    names = set(names)
    removed = added = 0
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
        if any(os.path.lexists(os.path.join(target_dir, c, n)) for c in os.listdir(target_dir)):
            continue
        cat = smap[n]
        os.makedirs(os.path.join(target_dir, cat), exist_ok=True)
        if not dry:
            os.symlink(os.path.join(store, cat, n), os.path.join(target_dir, cat, n))
        added += 1
    print(f"  [hermes] +{added} -{removed}  -> {target_dir}")


def rewrite_openclaw(cfg_path, per_agent, all_store, dry=False):
    """Riscrive agents.entries.<a>.skills preservando le skill bundled/native."""
    with open(cfg_path) as fh:
        cfg = json.load(fh)
    entries = cfg["agents"]["entries"]
    for agent, names in per_agent.items():
        if agent not in entries:
            print(f"  [openclaw] WARN: agente '{agent}' non in openclaw.json")
            continue
        bundled = [x for x in entries[agent].get("skills", []) if x not in all_store]
        final = bundled + sorted(set(names))
        if entries[agent].get("skills") != final:
            if not dry:
                entries[agent]["skills"] = final
            print(f"  [openclaw] {agent}: {len(bundled)} bundled + {len(set(names))} store")
    if not dry:
        shutil.copy2(cfg_path, cfg_path + ".bak-redistribute")
        with open(cfg_path, "w") as fh:
            json.dump(cfg, fh, indent=2)


def build_report(cfg, smap, cats):
    home = os.path.expanduser("~")
    agent_lists = cfg["agents"]
    oc = {k.split(".", 1)[1]: expand(v, cats, smap) for k, v in agent_lists.items() if k.startswith("openclaw.")}
    hermes = expand(agent_lists.get("hermes", []), cats, smap)
    opencode = expand(agent_lists.get("opencode", []), cats, smap)
    maka = expand(agent_lists.get("maka", []), cats, smap)

    def by_cat(names):
        g = collections.defaultdict(list)
        for n in names:
            g[smap[n]].append(n)
        return g

    assigned = collections.defaultdict(set)
    for a, ns in oc.items():
        for n in ns:
            assigned[n].add(f"OC.{a}")
    for n in hermes:
        assigned[n].add("Hermes")
    for n in opencode:
        assigned[n].add("OpenCode")
    for n in maka:
        assigned[n].add("Maka")

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    L = ["# Skill Redistribution", "",
         f"_Generato da `scripts/redistribute.py --report` il {ts} — fonte: `config/redistribution.yaml`_", "",
         "## Store per categoria", "", "| Categoria | # | Skill |", "|---|---|---|"]
    for cat in cats:
        ns = sorted([n for n, c in smap.items() if c == cat])
        L.append(f"| `{cat}` | {len(ns)} | {', '.join(ns)} |")
    L += ["", f"**Totale store: {len(smap)} skill**", "",
          "## Agenti", "", "| Agente | # skill (store) |", "|---|---|"]
    for a in ["coordinator", "coder", "researcher", "analyst", "writer"]:
        L.append(f"| OpenClaw.{a} | {len(oc.get(a, []))} |")
    L += [f"| Hermes | {len(hermes)} |", f"| OpenCode | {len(opencode)} |", f"| Maka | {len(maka)} |", ""]

    L += ["## Dettaglio per agente", ""]
    for a in ["coordinator", "coder", "researcher", "analyst", "writer"]:
        L.append(f"### OpenClaw.{a}")
        for cat, ns in sorted(by_cat(oc.get(a, [])).items()):
            L.append(f"- **{cat}** ({len(ns)}): {', '.join(ns)}")
        L.append("")
    for label, names in [("Hermes", hermes), ("OpenCode", opencode), ("Maka", maka)]:
        L.append(f"### {label}")
        for cat, ns in sorted(by_cat(names).items()):
            L.append(f"- **{cat}** ({len(ns)}): {', '.join(ns)}")
        L.append("")

    shared = {n: sorted(v) for n, v in assigned.items() if len(v) > 1}
    L += ["## Skill condivise", ""]
    if shared:
        bypair = collections.defaultdict(list)
        for n, who in shared.items():
            bypair[" + ".join(who)].append(n)
        for pair, ns in bypair.items():
            L.append(f"- **{pair}** — {len(ns)}: {', '.join(sorted(ns))}")
    else:
        L.append("(nessuna)")
    L += ["", "## Skill NON assegnate a nessuno", ""]
    unassigned = [n for n in smap if n not in assigned]
    L.append("**Nessuna**" if not unassigned else "\n".join(f"- `{smap[n]}/{n}`" for n in unassigned))
    L += ["", "## Maka — profilo", "",
          f"- Composition: `maka.interactive` · workspace `~/.config/Maka/workspaces/default`",
          f"- Ruolo: specialista Android/mobile ({len(maka)} skill)"]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=CONFIG_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    store = os.path.expanduser(cfg.get("store", ROOT))
    smap = store_map(store)
    cats = categories(store)
    all_store = set(smap)
    tgt = cfg["targets"]

    print(f"store: {store}  ({len(smap)} skill, {len(cats)} categorie)  dry_run={args.dry_run}")

    if args.report:
        out = os.path.join(ROOT, "REDISTRIBUTION.md")
        with open(out, "w") as fh:
            fh.write(build_report(cfg, smap, cats))
        print(f"report -> {out}")
        return

    oc_lists = {k.split(".", 1)[1]: expand(v, cats, smap)
                for k, v in cfg["agents"].items() if k.startswith("openclaw.")}
    pool = sorted(set(sum(oc_lists.values(), [])))

    sync_flat(os.path.expanduser(tgt["openclaw"]["skills_dir"]), pool, smap, store, args.dry_run, "openclaw")
    sync_flat(os.path.expanduser(tgt["openclaw"]["library_dir"]), pool, smap, store, args.dry_run, "openclaw/lib")
    rewrite_openclaw(os.path.expanduser(tgt["openclaw"]["config"]), oc_lists, all_store, args.dry_run)
    sync_hermes(os.path.expanduser(tgt["hermes"]["skills_dir"]),
                expand(cfg["agents"]["hermes"], cats, smap), smap, store, args.dry_run)
    sync_flat(os.path.expanduser(tgt["opencode"]["skills_dir"]),
              expand(cfg["agents"]["opencode"], cats, smap), smap, store, args.dry_run, "opencode")
    sync_flat(os.path.expanduser(tgt["maka"]["skills_dir"]),
              expand(cfg["agents"]["maka"], cats, smap), smap, store, args.dry_run, "maka")
    print("OK")


if __name__ == "__main__":
    main()
