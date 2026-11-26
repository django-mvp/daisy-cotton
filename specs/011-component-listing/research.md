# Research: List the Cotton components a project can use

## Assumptions checked

Checked 2026-11-26 in this repository's demo project (django-cotton as locked in `uv.lock`, django-cotton-gallery 1.0.0).

- **Components named after a folder resolve through `index.html`.** `<c-card>` renders `daisy_cotton/templates/cotton/card/index.html`. django-cotton falls back to `<name>/index.html` when `<name>.html` does not exist (`django_cotton/templatetags/_component.py`).
- **Hyphens and underscores name the same component by default.** `<c-hover-gallery>` and `<c-hover_gallery>` both render `hover_gallery.html`. django-cotton replaces hyphens with underscores unless `COTTON_SNAKE_CASED_NAMES` is `False`, and builds the path as `{COTTON_DIR}/{name with dots as slashes}.html`.
- **The demo's loaders are django-cotton's loader, then the filesystem and app-directories loaders, inside the cached loader.** django-cotton's loader searches `TEMPLATES` `DIRS`, every installed app's `templates/` folder, and `BASE_DIR/templates` (or `COTTON_BASE_DIR/templates`) when it exists.
- **The gallery's annotation syntax reads every daisy-cotton component.** Its parser read all 82 components on main, and every one has a description. Props come back with type and options (`card`: `size` as a select of `xs`–`xl`), and slots with their names and descriptions.
- **django-mvp's components carry the same annotations.** 101 of its 105 component files have `@description`. 85 of them sit under the `mvp/` folder, which is why the list is by component rather than by folder.
- **The package has no management command today.** `daisy_cotton/` has no `management/` folder, so the command name is free.
