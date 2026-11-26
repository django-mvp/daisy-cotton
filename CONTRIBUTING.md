# Contributing to daisy-cotton

Thanks for helping. This page covers setting up, running the component gallery, running the checks, and what a finished component looks like.

Three pages set the rules every change follows: [testing](docs/contributing/standards/testing.md), for what gets a test and how tests are structured, [code documentation](docs/contributing/standards/code-documentation.md), for docstrings, component annotations and comments, and [Django](docs/contributing/standards/django.md), for where code lives and when a new abstraction is worth adding.

## Set up

The project is built and developed with [uv](https://docs.astral.sh/uv/). From a checkout:

```bash
uv sync
```

This installs the package, its development tools and the component gallery into a local `.venv`. Prefix every command below with `uv run` so it uses that environment.

## Open the component gallery

```bash
uv run python manage.py runserver
```

Then open <http://127.0.0.1:8000/django-cotton-gallery/>. Every component is listed there with its description, attributes and slots, all read from the annotations at the top of its template. The gallery is a development tool and only runs with `DEBUG` on, which the demo project sets. Previews load the Bootstrap Icons font, so any icon attribute can be tried with a class such as `bi bi-house`.

## Run the checks

Check the annotations with the gallery's linter:

```bash
uv run python manage.py cotton_lint --warnings-as-errors
```

Run the test suite:

```bash
uv run pytest
```

Run the formatter, linter and type checks:

```bash
uv run pre-commit run --all-files
```

### What fails

Errors and warnings fail. Hints do not: a hint is advice the linter cannot be sure about, such as a template variable it can't see declared. The test suite applies the same rule, so `tests/test_gallery_lint.py` fails on any error or warning in any component, and the failure lists each finding as `<component> L<line> <rule>: <message>`.

`tests/test_gallery_annotations.py` adds four checks the linter does not make. Every template must have:

- exactly one `{# @description … #}`
- a default `{# @slot … #}` if it renders `{{ slot }}`
- every `{#` closed with `#}` on the same line
- every `variant`, `align`, `position` or `placement` prop typed `select['…']` with its values listed, so the gallery offers a dropdown

The annotation format is described in the gallery's [annotation reference](https://velezanthony.github.io/django-cotton-gallery/users/annotations/).

## When a component is done

A component is not done until it carries its annotations and the suite passes. In practice, a new or changed component in `daisy_cotton/templates/cotton/` needs:

1. A `@description`, one `@prop` for each name in `<c-vars>`, and a `@slot` and `@slot:name` for each slot it renders, at the top of the template.
2. `uv run python manage.py cotton_lint --warnings-as-errors` reporting no errors or warnings, apart from the `merge` warning described under "A component's own classes".
3. `uv run pytest` and `uv run pre-commit run --all-files` passing.
4. A line in the `[Unreleased]` section of the [CHANGELOG](CHANGELOG.md).

A new template is picked up by the linter and both checks automatically. There is no list to add it to.

## A component's own classes

A component that takes a `class` declares its fixed base classes in `<c-vars>` with `class:merge`, and renders `{{ class }}` on its root element:

```html
<c-vars overlay="" class:merge="hero" />
<div class="{{ class }}" {{ attrs }}>…</div>
```

Cotton puts the component's classes first and the caller's after them, so `<c-hero class="min-h-64" />` renders `class="hero min-h-64"`, and `<c-hero />` renders `class="hero"` with no trailing space.

Classes that come from template tags, such as `{% variation %}`, `{% responsive %}` or `{% if %}`, stay in the element's `class` attribute after `{{ class }}`, and only the static ones go in `<c-vars>`:

```html
<c-vars text="" variant="" class:merge="badge" />
<span class="{{ class }} {% variation variant "badge" "primary,secondary" %}" {{ attrs }}>{{ text }}</span>
```

`<c-badge variant="primary" class="ml-2" />` gets the classes `badge ml-2 badge-primary`, in that order. A component with no fixed base class, or whose base class changes with an attribute, declares `class=""` and writes `{{ class }}` where it belongs.

`class` is the only attribute Cotton merges. Since `class` is declared, it never reaches `{{ attrs }}`.

The gallery's linter does not know `class:merge` yet. It reads it as a second prop named `merge` and warns that no `@prop` documents it (issue #177). That warning is expected on these components. `tests/test_gallery_lint.py` ignores it and fails on anything else.

## Components used inside a sentence

`link`, `badge`, `kbd`, `status`, `icon` and `button` can sit in running text, where any whitespace the template emits around its element is drawn as a space: `(<c-badge text="new" />)` would read "( new )". Their templates are laid out so that nothing is emitted outside the element:

- The annotations sit inside one `{% comment %}` block, each still a `{# … #}` on its own line. The gallery reads them there as it does anywhere else.
- `{% load %}` comes before that block on the same line, and `<c-vars>` and the opening tag follow `{% endcomment %}` with nothing between them.
- The file ends on the closing tag, with no final newline. The end-of-file hook in `.pre-commit-config.yaml` skips these six files by name.

`tests/test_inline_whitespace.py` renders each of them between two characters and fails if anything separates them. A new component meant for running text gets the same layout, a line in that test's list and its name in the hook's `exclude`.
