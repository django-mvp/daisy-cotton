# Research: List the Cotton components a project can use

## Assumptions checked

Checked 2026-11-26 in this repository's demo project (django-cotton as locked in `uv.lock`, django-cotton-gallery 1.0.0).

- **Components named after a folder resolve through `index.html`.** `<c-card>` renders `daisy_cotton/templates/cotton/card/index.html`. django-cotton falls back to `<name>/index.html` when `<name>.html` does not exist (`django_cotton/templatetags/_component.py`).
- **Hyphens and underscores name the same component by default.** `<c-hover-gallery>` and `<c-hover_gallery>` both render `hover_gallery.html`. django-cotton replaces hyphens with underscores unless `COTTON_SNAKE_CASED_NAMES` is `False`, and builds the path as `{COTTON_DIR}/{name with dots as slashes}.html`.
- **The demo's loaders are django-cotton's loader, then the filesystem and app-directories loaders, inside the cached loader.** django-cotton's loader searches `TEMPLATES` `DIRS`, every installed app's `templates/` folder, and `BASE_DIR/templates` (or `COTTON_BASE_DIR/templates`) when it exists.
- **The gallery's annotation syntax reads every daisy-cotton component.** Its parser read all 82 components on main, and every one has a description. Props come back with type and options (`card`: `size` as a select of `xs`–`xl`), and slots with their names and descriptions.
- **django-mvp's components carry the same annotations.** 101 of its 105 component files have `@description`. 85 of them sit under the `mvp/` folder, which is why the list is by component rather than by folder.
- **The package has no management command today.** `daisy_cotton/` has no `management/` folder, so the command name is free.

## Planning notes answered

### Look at django-cotton-gallery first

**Adopted.** The gallery (MIT, 1.0.1) provides three things this feature needs:

- `core/annotations.py`, the parser for `@description`, `@prop`, `@slot` and `@trigger`, with the `Prop`, `Slot` and `ParsedComponent` types from `core/schemas.py`. It has no Django imports.
- The index rule in `core/catalog/scanner.py`: `<dir>/index.html` is the component named `<dir>`, and a sibling `<dir>.html` wins.
- The reference pattern in `core/component_graph.py`: `<c-([\w.-]+)\b`, skipping `vars`.

The gallery cannot be imported at runtime (Article XI), and django-mvp and the projects built on it do not install the gallery, so requiring it would leave the command unusable exactly where it is wanted. The parser and its three types are copied into the package with the gallery's MIT notice. The test suite runs the copy and the gallery's own parser over every component in the package and requires the same result, so drift shows up as a failing test. The scanner itself is not copied: it reads one folder, and this feature reads every folder in loader order.

### Keep the output small

**Adopted.** The list prints one line per component and a count, and the full documentation only through `--show`. The template body is never printed. Neither shape prints a header block or explanatory text beyond one line.

## Architecture

- **Folders, in loader order.** For each Django template engine, walk its loaders in order, unwrapping the cached loader's `loaders`, and take each loader's `get_dirs()`. Django's filesystem and app-directories loaders and django-cotton's loader all provide it, and django-cotton's adds `BASE_DIR/templates` (or `COTTON_BASE_DIR/templates`). Duplicates keep their first position.
- **Which copy wins.** django-cotton asks the loaders for `<COTTON_DIR>/<name>.html` and only when no folder has it for `<COTTON_DIR>/<name>/index.html` (`_component.py`). So a `<name>.html` in any folder beats a `<name>/index.html` in an earlier one. The winner is the first folder holding `<name>.html`, else the first holding `<name>/index.html`. Every other copy is an override.
- **Package.** The app whose `Path(app_config.path) / "templates"` equals the folder, by `label`. Otherwise `project`.
- **Uses.** Every file under every folder, excluding each folder's `COTTON_DIR` subtree, read as text (undecodable files skipped), matched with `<c-([\w.-]+)` (excluding `vars` and `component`) and `{%\s*cotton\s+([\w.-]+)`. Names are compared after replacing hyphens with underscores when `COTTON_SNAKE_CASED_NAMES` is on. Computed only for `--show`.
- **First sentence.** Up to the first `.`, `!` or `?` followed by whitespace and a capital letter, else the whole description.
- **Closest names.** `difflib.get_close_matches(term, names, n=5)`.

## What already exists

- Annotation parsing: **an installed package** (django-cotton-gallery's `AnnotationParser`), copied because it cannot be a runtime dependency.
- Template folders in loader order: **Django** (`Engine.template_loaders`, each loader's `get_dirs()`).
- The component file a tag resolves to: **django-cotton** (`get_template_name` rules), reproduced as the two-pass lookup above, since django-cotton exposes no listing.
- Closest-name suggestions: **the standard library** (`difflib`).
- JSON output: **the standard library** (`json`).
- Command-line options: **Django** (`BaseCommand`, `CommandError`).
- The catalog class (discovery, overrides, uses) and the command's two output shapes: **new code**. Nothing in Django, django-cotton or the gallery lists components across folders.
