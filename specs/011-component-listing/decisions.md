# Decisions: List the Cotton components a project can use

Choices made while writing the spec, with the reasoning too long for *Clarifications* in `spec.md`.

## D1: The command lives in daisy-cotton

daisy-cotton is the package every project built on these components already installs, including projects that use none of django-mvp. Putting the command here means it is available in all of them, and in daisy-cotton's own demo. The README's *Scope & philosophy* is widened by exactly this one item, and says so.

**ADR:** none — where one command lives; the README's scope section already records the exception

## D2: No new runtime dependency

Article XI limits the package's runtime dependencies to Django and django-cotton. django-cotton-gallery owns the annotation syntax and has a parser for it (MIT licence, no Django imports in its parser), but it also ships views, URLs and templates, and today it is a development dependency only, used by the demo. The command therefore cannot import it at runtime. Reading the annotations in the gallery's syntax is the requirement (FR-013); how that is done is for the plan, with these constraints: copying the gallery's code keeps its MIT notice, and SC-002 checks the result against the gallery's own parser in the test suite, where the gallery is installed.

**ADR:** docs/adr/0002-annotation-parser-is-a-copy.md

## D3: Overrides follow the template loaders, not the list of installed apps

A project's own template folder usually overrides a package's component, and between apps the first one in `INSTALLED_APPS` wins. Both follow from Django asking its template loaders in order and taking the first file found. The command follows the same order rather than reproducing either rule, so it agrees with what a page renders (SC-004). django-cotton's own loader also searches `BASE_DIR/templates` when that folder exists, even if `TEMPLATES` `DIRS` does not name it, so the command covers that folder too.

**ADR:** none — follows from how Django's loaders already work, nothing new for later work to abide by

## D4: Usage counts page templates, not components

"How many templates use it" is counted across every folder the project loads templates from, including installed packages, but never inside a `COTTON_DIR` folder. A component used inside another component is a building block of that component, not a choice a page made, so counting it would make a near-copy look settled on. The JSON output gives the paths of the templates it counted.

**ADR:** none — a behaviour of this command, recorded in its spec

## D5: A name that matches nothing suggests the closest names

`--show` exists for a name the developer already believes is right, so a miss is usually a typo or a wrong folder. Listing the closest names (`card.title` for `card.titel`) gets the next attempt right, where an error alone costs a full list.

**ADR:** none — a behaviour of this command, recorded in its spec

## D6: Hidden props are shown

The gallery's `hidden` marker hides a prop from the gallery's interactive controls. A developer reading the documentation still needs to know the prop exists, so it is shown and marked hidden.

**ADR:** none — a behaviour of this command, recorded in its spec

## D7: Housekeeping on this branch

Three conformance repairs that main needed before the build could start green: `ruff-base.toml` re-copied from the shared templates (with the repo's own carve-outs moved to `extend-per-file-ignores`, which merges rather than replaces), `docs/brainstorm.md` moved to `docs/developer/`, and the documentation standard added under `docs/contributing/standards/` with a pointer from Article VI. None changes behaviour.

**ADR:** none — repairs to match existing standards, no decision for later work

## D8: Design review outcome

No critical or high findings. Applied as plan and task edits: a malformed-annotation test (DR-001), automated checks for SC-001 and SC-004 under django-cotton's real loader chain (DR-002, DR-004), an app-against-app override test in both orders (DR-003), unreachable file names left out (DR-005), the copied parser exempt from docstring rules so it stays verbatim (DR-006), the private-folder check limited to parts below `COTTON_DIR` (DR-007), descriptions parsed once at list time (DR-008), slot example content in the JSON test (DR-010). DR-009: the worktree's environment has the locked versions, django-cotton 2.9.0 and django-cotton-gallery 1.0.1.

**ADR:** none — review record, local to this feature

## D9: A prop with a default is never required

The copied parser drops `required` on a prop that also has a `default`, since a default means the prop never has to be given. The command shows what the parser reads, so such a prop is not listed as required. The copy stays unchanged (D2).

**ADR:** none — covered by docs/adr/0002-annotation-parser-is-a-copy.md

## D10: The catalog is documented as a Python API

The repository's documentation check requires every new public name to be quoted on a page. `Component` and `ComponentCatalog` are useful from Python as well as through the command, so the README documents them in one paragraph, and `catalog.py` declares `__all__` as those two and `ComponentNotFound`. The copied parser is exempt from that check in `pyproject.toml`, because its names are the gallery's, not this package's.

**ADR:** none — local to this feature

## D11: No browser check

The feature adds a management command and no page, so there is nothing to load in a browser.

**ADR:** none — local to this feature

## D12: The catalog follows django-cotton's fallback to `cotton/`

django-cotton 2.9 renders a component from the default layout (`cotton/`, snake-cased file names) when the configured `COTTON_DIR` or hyphenated name finds no file. Earlier versions do not. The catalog follows whichever version is installed, by using django-cotton's own list of candidate paths when it has one, so the list keeps agreeing with what a page renders (Clarification Q1, SC-004). US1 scenario 8, the snake-cased edge case, FR-002 and FR-011 were corrected to say so. The runtime floor stays at django-cotton 2.6.

**ADR:** none — a behaviour of this command that follows the installed django-cotton
