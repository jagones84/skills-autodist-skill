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
    python3 scripts/redistribute.py --dry-run  # mostra i conteggi delle modifiche (non scrive)
    python3 scripts/redistribute.py --diff     # mostra le modifiche voce per voce (non scrive)
    python3 scripts/redistribute.py --validate # valida il config, nessuna scrittura (exit 1 se errato)
    python3 scripts/redistribute.py --adopt <src> --cat <cat>  # mette una skill nello store (copy|link)
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
STRIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}


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


def resolve_entries(entries, cats, smap):
    """Come `expand` ma NON esce: ritorna (nomi, errori)."""
    out, errors = [], []
    for e in entries or []:
        if e.startswith("cat:"):
            c = e[4:]
            if c not in cats:
                errors.append(f"Categoria sconosciuta nel config: '{c}'")
            else:
                out += [n for n, cc in smap.items() if cc == c]
        elif e in smap:
            out.append(e)
        else:
            errors.append(f"Skill sconosciuta nel config: '{e}'")
    return sorted(set(out)), errors


def expand(entries, cats, smap):
    """`cat:<nome>` = categoria intera; altrimenti nome di skill puntuale."""
    names, errors = resolve_entries(entries, cats, smap)
    if errors:
        sys.exit(errors[0])
    return names


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
    parts = pointer.split(".")
    return parts[-2] if len(parts) >= 2 else parts[-1]


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


# ------------------------------------------------------------------- validate
def _harness_entries(htype, hcfg):
    """{etichetta -> voci}: '' = harness a lista singola (flat/categorized)."""
    if htype in ("flat", "categorized"):
        return {"": hcfg.get("skills", [])}
    if htype == "json_list":
        if not (hcfg.get("lists") or hcfg.get("pointer")):
            return {}
        return {_label(s["pointer"]): s.get("skills", []) for s in _specs(hcfg) if s.get("pointer")}
    if htype == "openclaw":
        return dict(hcfg.get("agents", {}))
    return {}


def validate_config(cfg, store, smap, cats):
    """Valida il config SENZA applicarlo: ritorna la lista errori ([] = valido)."""
    errs = []
    if not isinstance(cfg, dict):
        return ["config non valido (non e' una mappa YAML)"]
    if not cfg.get("store"):
        errs.append("manca 'store'")
    if not os.path.isdir(store):
        errs.append(f"store inesistente: {store}")
    harnesses = cfg.get("harnesses")
    if not isinstance(harnesses, dict) or not harnesses:
        errs.append("manca 'harnesses' (mappa non vuota)")
        return errs
    for hname, hcfg in harnesses.items():
        if not isinstance(hcfg, dict):
            errs.append(f"{hname}: harness non valido")
            continue
        htype = hcfg.get("type")
        if htype not in BACKENDS:
            errs.append(f"{hname}: type sconosciuto '{htype}'")
            continue
        if htype in ("flat", "categorized") and not hcfg.get("skills_dir"):
            errs.append(f"{hname}: manca 'skills_dir'")
        if htype == "json_list":
            if not hcfg.get("file"):
                errs.append(f"{hname}: manca 'file'")
            elif not os.path.isfile(os.path.expanduser(hcfg["file"])):
                errs.append(f"{hname}: file inesistente: {hcfg['file']}")
            if not hcfg.get("lists") and not hcfg.get("pointer"):
                errs.append(f"{hname}: serve 'pointer' o 'lists'")
            if hcfg.get("lists") or hcfg.get("pointer"):
                for spec in _specs(hcfg):
                    if not spec.get("pointer"):
                        errs.append(f"{hname}: un target senza 'pointer'")
        if htype == "openclaw":
            if not hcfg.get("config"):
                errs.append(f"{hname}: manca 'config'")
            elif not os.path.isfile(os.path.expanduser(hcfg["config"])):
                errs.append(f"{hname}: config inesistente: {hcfg['config']}")
        for label, entries in _harness_entries(htype, hcfg).items():
            for msg in resolve_entries(entries, cats, smap)[1]:
                errs.append(f"{hname}.{label}: {msg}" if label else f"{hname}: {msg}")
    return errs


# ----------------------------------------------------------------------- diff
def _link_names(d):
    """Nomi dei symlink in una cartella (vuoto se non esiste)."""
    if not os.path.isdir(d):
        return set()
    return {n for n in os.listdir(d) if os.path.islink(os.path.join(d, n))}


def _categorized_link_names(d):
    """Nomi dei symlink nei sottolivelli di categoria."""
    if not os.path.isdir(d):
        return set()
    out = set()
    for c in os.listdir(d):
        cp = os.path.join(d, c)
        if os.path.isdir(cp):
            out |= {n for n in os.listdir(cp) if os.path.islink(os.path.join(cp, n))}
    return out


def _json_names(path, pointer):
    """La lista puntata da `pointer` in un file JSON (vuoto se file/pointer assenti)."""
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return set()
    with open(path) as fh:
        node = json.load(fh)
    for k in pointer.split("."):
        node = node[k]
    return set(node)


def _changes(have, want, all_store, preserve_mode):
    """(aggiunte, rimosse) fra lo stato presente `have` e il voluto `want`."""
    have, want = set(have), set(want)
    added = sorted(want - have)
    if preserve_mode == "not_in_store":
        removed = sorted(x for x in have - want if x in all_store)
    else:
        removed = sorted(have - want)
    return added, removed


def _emit(lines, hname, label, have, want, all_store, preserve_mode):
    added, removed = _changes(have, want, all_store, preserve_mode)
    head = f"[{hname}]" if label == "*" else f"[{hname}:{label}]"
    if not added and not removed:
        lines.append(head + " (nessuna modifica)")
        return
    lines.append(head)
    lines += [f"  + {n}" for n in added]
    lines += [f"  - {n}" for n in removed]


def diff_config(cfg, store, smap, cats, all_store):
    """Le modifiche che `apply` farebbe, voce per voce. NON scrive nulla."""
    lines = []
    for hname, hcfg in cfg["harnesses"].items():
        htype = hcfg["type"]
        p = plan(htype, hcfg, cats, smap)
        pmode = hcfg.get("preserve", "not_in_store")
        if htype == "flat":
            _emit(lines, hname, "*", _link_names(os.path.expanduser(hcfg["skills_dir"])),
                  p["*"], all_store, "none")
        elif htype == "categorized":
            _emit(lines, hname, "*", _categorized_link_names(os.path.expanduser(hcfg["skills_dir"])),
                  p["*"], all_store, "none")
        elif htype == "json_list":
            for spec in _specs(hcfg):
                label = _label(spec["pointer"])
                _emit(lines, hname, label, _json_names(hcfg["file"], spec["pointer"]),
                      p[label], all_store, pmode)
        elif htype == "openclaw":
            pool = sorted(set(sum(p.values(), [])))
            for key in ("skills_dir", "library_dir"):
                if hcfg.get(key):
                    _emit(lines, hname, key, _link_names(os.path.expanduser(hcfg[key])),
                          pool, all_store, "none")
            for a in p:
                _emit(lines, hname, f"agent:{a}",
                      _json_names(hcfg["config"], f"agents.entries.{a}.skills"),
                      p[a], all_store, pmode)
    return lines


# ---------------------------------------------------------------------- adopt
def _skill_name(src):
    """Il `name:` del frontmatter di SKILL.md (sola lettura), o None."""
    try:
        with open(os.path.join(src, "SKILL.md"), encoding="utf-8") as fh:
            txt = fh.read(2000)
    except OSError:
        return None
    if txt.startswith("---") and txt.count("---") >= 2:
        block = txt.split("---", 2)[1]
        for line in block.splitlines():
            s = line.strip()
            if s.startswith("name:"):
                return s.split(":", 1)[1].strip().strip('"').strip("'") or None
    return None


def resolve_name(src, name=None):
    """Nome della skill: `name` esplicito > `name:` di SKILL.md > nome cartella."""
    return name or _skill_name(src) or os.path.basename(os.path.abspath(src).rstrip("/"))


def _strip_ignore(strip):
    """Ignore per copytree: salta le cartelle non-skill (VCS/dipendenze) se `strip`."""
    def ignore(_dirpath, names):
        return {n for n in names if n in STRIP_DIRS} if strip else set()
    return ignore


def adopt_skill(store, src, cat, name=None, mode="copy", strip=True, force=False, dry=False):
    """Colloca una skill nello store (copy di default, oppure link). NON modifica la sorgente.

    Ritorna (destinazione, nome). Solleva ValueError se la sorgente non e' una skill
    (manca `SKILL.md`), se il mode e' ignoto, o se la destinazione esiste (serve `force`).
    """
    src = os.path.abspath(os.path.expanduser(src))
    if not os.path.isdir(src):
        raise ValueError(f"sorgente inesistente: {src}")
    if not os.path.isfile(os.path.join(src, "SKILL.md")):
        raise ValueError(f"non e' una skill (manca SKILL.md): {src}")
    if mode not in ("copy", "link"):
        raise ValueError(f"mode sconosciuto: '{mode}' (copy|link)")
    name = resolve_name(src, name)
    catdir = os.path.join(store, cat)
    dest = os.path.join(catdir, name)
    if os.path.lexists(dest) and not force:
        raise ValueError(f"destinazione gia' esistente: {dest} (usa --force per sostituire)")
    if not dry:
        os.makedirs(catdir, exist_ok=True)
        if os.path.islink(dest):
            os.remove(dest)
        elif os.path.isdir(dest):
            shutil.rmtree(dest)
        if mode == "copy":
            shutil.copytree(src, dest, ignore=_strip_ignore(strip))
        else:
            os.symlink(os.path.relpath(src, catdir), dest)
    return dest, name


def wire_snippet(cat, name):
    """Le righe da mostrare all'utente per collegare la skill appena adottata."""
    return [
        f"config: '{name}' e' ora nello store (categoria '{cat}').",
        f"  - ZERO edit se un harness seleziona `cat:{cat}` (la prende da solo).",
        f"  - altrimenti aggiungi `{name}` alla lista `skills:` dell'harness voluto.",
    ]


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
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--diff", action="store_true")
    ap.add_argument("--adopt", metavar="SRC", help="colloca una skill nello store")
    ap.add_argument("--cat", help="categoria di destinazione per --adopt")
    ap.add_argument("--as", dest="as_name", help="nome di destinazione per --adopt")
    ap.add_argument("--mode", default="copy", help="copy (default) | link")
    ap.add_argument("--no-strip", action="store_true", help="con --adopt copia anche .git/dipendenze")
    ap.add_argument("--force", action="store_true", help="con --adopt sostituisce la destinazione esistente")
    args = ap.parse_args()

    cfg = load_config(args.config)
    store = os.path.expanduser(cfg.get("store", "")) if isinstance(cfg, dict) else ""

    if args.adopt:
        if not args.cat:
            print("ERRORE: --adopt richiede --cat <categoria>")
            sys.exit(1)
        if not store:
            print("ERRORE: manca 'store' nel config")
            sys.exit(1)
        try:
            dest, name = adopt_skill(store, args.adopt, args.cat, args.as_name,
                                     mode=args.mode, strip=not args.no_strip,
                                     force=args.force, dry=args.dry_run)
        except ValueError as exc:
            print("ERRORE:", exc)
            sys.exit(1)
        print(("[dry-run] " if args.dry_run else "") + f"adottata in: {dest}")
        for line in wire_snippet(args.cat, name):
            print(line)
        return

    smap = store_map(store) if os.path.isdir(store) else {}
    cats = categories(store) if os.path.isdir(store) else {}
    all_store = set(smap)
    print(f"store: {store}  ({len(smap)} skill, {len(cats)} categorie)  dry_run={args.dry_run}")

    if args.validate:
        errs = validate_config(cfg, store, smap, cats)
        if errs:
            for e in errs:
                print(f"ERRORE: {e}")
            sys.exit(1)
        print("config valido")
        return

    if args.diff:
        for line in diff_config(cfg, store, smap, cats, all_store):
            print(line)
        return

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
