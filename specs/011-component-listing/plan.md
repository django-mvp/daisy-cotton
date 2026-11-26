# Implementation Plan: List the Cotton components a project can use

**Branch**: `011-component-listing` | **Date**: 2026-11-26 | **Spec**: [spec.md](spec.md)

**Input**: `specs/011-component-listing/spec.md`, `research.md`, `decisions.md`, `planning-notes.md`

## Summary

A `cotton_components` management command, backed by a `ComponentCatalog` class that finds every component the project can render in loader order, and an annotation parser copied from django-cotton-gallery. The command prints a one-line-per-component list, or one component's full documentation with the number of page templates that use it, as text or JSON.

## Technical Context

- **Language**: Python 3.12+, Django 5.2+, django-cotton 2.6+.
- **Runtime dependencies**: unchanged (Django, django-cotton). django-cotton-gallery stays a development dependency and is used only in tests, to check the copied parser against the original.
- **Testing**: pytest with pytest-django, `tests/settings.py`. Tests that need several template folders use `override_settings` on `INSTALLED_APPS`, `TEMPLATES` and `COTTON_DIR`, with two small fixture apps under `tests/fixtures/` and project-level folders under `tmp_path`.
- **Performance**: the list reads each component file once. Uses are scanned only for `--show`.

## Constitution Check

| Article | How the plan meets it |
|---|---|
| VI Documentation | README gains a section on the command and the *Scope & philosophy* line. CHANGELOG `Added`. Every public class and function has a Google-style docstring. |
| VII Dependency discipline | No runtime dependency added. `deptry` passes. |
| VIII Internationalization | Command output is developer-facing terminal text, not user-facing copy, and Django's own management commands do not translate theirs. Not translated. |
| X Cohesion | Discovery, overrides and uses live in one `ComponentCatalog` class. Parsing lives in `AnnotationParser`. The command only parses arguments and formats output. |
| XI Agnostic of every adopter | Nothing names a project. The command lists whatever the project has. |
| Others | No models, no components, no colours or attributes touched. |

## Design

### `daisy_cotton/annotations.py`, the copied parser

A copy of django-cotton-gallery 1.0.1's `core/annotations.py` with the `Prop`, `Slot` and `ParsedComponent` dataclasses from `core/schemas.py` (only those three, plus `PropType`), in one module. The file opens with a comment naming the source package, version and file, and carries the gallery's MIT copyright and permission notice. Imports are adjusted to the one module. Nothing else changes, so a later re-copy is a plain diff. Behaviour is not re-tested line by line: one parametrised test runs this parser and the gallery's over every component file in `daisy_cotton/templates/cotton/` and requires equal `ParsedComponent` values (as dicts, via `dataclasses.asdict`), plus a test for each annotation shape the spec names that the package's own files do not exercise (required, deprecated, hidden, default).

### `daisy_cotton/catalog.py`

```python
@dataclass(frozen=True)
class Component:
    name: str            # "card.title"
    path: Path           # absolute file path of the copy that renders
    package: str         # app label, or "project"
    overrides: tuple[str, ...]  # packages of the other copies, in loader order
    source: str          # file text, "" when unreadable
    # tag -> f"<c-{name}>", summary -> first sentence or "—" (properties)

class ComponentCatalog:
    def __init__(self): ...             # reads COTTON_DIR, COTTON_SNAKE_CASED_NAMES once
    def folders(self) -> list[Path]     # template folders in loader order
    def components(self) -> list[Component]   # sorted by name
    def search(self, term="", text="", package="") -> list[Component]
    def get(self, name) -> Component    # raises ComponentNotFound(name, suggestions)
    def uses(self, component) -> list[Path]
```

- **`folders()`**: for every engine in `django.template.engines.all()` whose backend is `DjangoTemplates`, walk `engine.engine.template_loaders` depth-first, descending into a loader's `loaders` attribute (the cached loader), and extend with each loader's `get_dirs()` when it has one. Each entry becomes a resolved `Path`, duplicates dropped, first position kept. Loaders with no `get_dirs()` (locmem) contribute nothing.
- **`components()`**: for each folder, walk `<folder>/<COTTON_DIR>` with `rglob("*.html")`, skipping any file with a part below `COTTON_DIR` starting with `_`, any name holding `-` when snake-cased names are on, and any stem holding `.`, since no tag resolves to those files. Each file gives a candidate `(name, kind)`: `kind` is `file` for `<x>.html` and `index` for `<x>/index.html` (a top-level `index.html` is a file named `index`). Descriptions are parsed once here, at list time, and kept on the `Component` (`documentation` is a property, not a catalog method). Then, per name: the winner is the first folder with a `file` candidate, else the first with an `index` candidate (research, "Which copy wins"). Every other candidate's package goes into `overrides`, in folder order, duplicates dropped, and excluding the winner's own package. A sibling `file` and `index` in the same folder give one component, the `file`, with nothing recorded as overridden.
- **Package**: a dict built once from `apps.get_app_configs()`, `Path(cfg.path, "templates").resolve() -> cfg.label`. A folder not in it is `project`.
- **Name matching**: `_normalise(s)` lower-cases, and replaces `-` with `_` when snake-cased names are on. `search(term)` keeps components where `_normalise(term) in _normalise(name)`. `text` is a case-insensitive substring of the full `@description`. `package` is an exact label match. All given filters apply.
- **`get(name)`**: exact match on the normalised name. Otherwise `ComponentNotFound` carrying `difflib.get_close_matches(normalised term, normalised names, n=5, cutoff=0.6)` mapped back to real names.
- **`uses(component)`**: every file under every folder from `folders()`, except files under any folder's `<COTTON_DIR>` subtree, read as UTF-8 (skip `UnicodeDecodeError` and `OSError`). A file counts once if any reference in it, normalised, equals the component's normalised name. References: `<c-([\w.-]+)` excluding `vars` and `component`, and `{%\s*cotton\s+([\w.-]+)`. Returns sorted paths.
- **Summary**: `re.match(r"(.+?[.!?])(?=\s+[A-Z])", description, re.S)`, else the whole description, whitespace collapsed. Empty → `—`.
- An unreadable component file gives `source=""`, so its summary is `—`.

### `daisy_cotton/management/commands/cotton_components.py`

```
cotton_components [term] [--text WORDS] [--package LABEL] [--show NAME] [--json]
```

- **List**: one line per component, columns padded to the longest tag and package: `<c-card.title>  daisy_cotton  Heading for a card.`, and ` (overrides mvp)` appended when there are overrides. Then `N components`. No match: `No component matches.`, exit 0.
- **`--show`** (ignores `term`, `--text` and `--package`):

  ```
  <c-card>
  File: …/daisy_cotton/templates/cotton/card/index.html
  Package: daisy_cotton   (overrides: …)        # overrides only when present
  Used by 4 templates (dynamic <c-component is="…"> references are not counted)

  <full description, or —>

  Props:
    title  text  — Heading text, …
    size   select [xs, sm, md, lg, xl]  default "md"  required  — Card size.
  Slots:
    (default)  — …   e.g. <c-accordion …>
    title      — …
  Passes extra attributes to its element.     # or: Does not pass extra attributes.
  ```

  No props → `Props: none`. No slots → `Slots: none`. Flags `required`, `deprecated: <message>` and `hidden` appear after the type when set.
- **Not found**: `CommandError("No component named 'card.titel'. Closest: card.title, …")`, or `"No component named 'x'."` when there are no suggestions.
- **`--json`**: the list is an array of `{name, tag, package, path, summary, overrides}`, the documentation one object with those plus `description`, `props` (each `dataclasses.asdict(prop)`), `slots`, `accepts_attrs`, `uses` (count) and `use_paths`. Paths are strings. `summary`/`description` are `null` when there is no description.

### Documentation

- README: a *Listing the components a project can use* section with both shapes and the options. *Scope & philosophy* gains: "One exception: the `cotton_components` management command, which lists every Cotton component a project can render, from any package."
- CONTEXT.md: under **Component**, one line that the `cotton_components` command lists any Cotton component the project can render, not only this package's.
- CHANGELOG `Added`.

## Project Structure

```
daisy_cotton/
  annotations.py                         # copied parser (MIT notice)
  catalog.py                             # Component, ComponentCatalog, ComponentNotFound
  management/__init__.py
  management/commands/__init__.py
  management/commands/cotton_components.py
tests/
  fixtures/catalog_first/                # app: apps.py, templates/cotton/…
  fixtures/catalog_second/
  test_annotations.py
  test_catalog.py
  test_management/test_commands/test_cotton_components.py
```

## Story order

US-1 first: it builds `annotations.py` (needed for descriptions), `catalog.py` without `uses()` and `documentation()`, and the list shape of the command. US-2 adds `get()`, `uses()`, `documentation()` and `--show`.

## Complexity Tracking

None.
