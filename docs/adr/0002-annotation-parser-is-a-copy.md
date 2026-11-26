# ADR 0002 — The annotation parser is a copy of django-cotton-gallery's

**Status:** accepted

## Decision

`daisy_cotton/annotations.py` is a copy of django-cotton-gallery's annotation parser (`core/annotations.py` and the `Prop`, `Slot` and `ParsedComponent` classes from `core/schemas.py`), joined into one module and carrying the gallery's MIT notice. Its header names the version it was copied from. It is changed only by re-copying a newer version, apart from shortening lines to the repository's line length, which the header records.

`tests/test_annotations.py` parses every component in `daisy_cotton/templates/cotton/` with both this copy and the gallery's parser and requires the results to be equal. The gallery stays a development dependency, so that test runs wherever the suite runs.

## Why

The `cotton_components` management command reads each component's `@description`, `@prop` and `@slot` comments, and those comments are written in the gallery's syntax. The constitution limits runtime dependencies to Django and django-cotton (Article XI), and the gallery also ships views, URLs and templates, so it cannot be imported at runtime.

Writing a parser of our own would mean two readings of one syntax that drift apart, with nothing to say which is right. A copy kept unchanged reads the comments exactly as the gallery does, and the equality test shows the day it stops doing so.

## Revisit if

- django-cotton-gallery splits its parser into a package with no views or templates. Depend on that instead and delete the copy.
- The constitution allows the gallery as a runtime dependency.
