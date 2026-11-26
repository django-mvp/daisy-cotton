# Decisions: List the Cotton components a project can use

Choices made while writing the spec, with the reasoning too long for *Clarifications* in `spec.md`.

## The command lives in daisy-cotton

daisy-cotton is the package every project built on these components already installs, including projects that use none of django-mvp. Putting the command here means it is available in all of them, and in daisy-cotton's own demo. The README's *Scope & philosophy* is widened by exactly this one item, and says so.

## No new runtime dependency

Article XI limits the package's runtime dependencies to Django and django-cotton. django-cotton-gallery owns the annotation syntax and has a parser for it (MIT licence, no Django imports in its parser), but it also ships views, URLs and templates, and today it is a development dependency only, used by the demo. The command therefore cannot import it at runtime. Reading the annotations in the gallery's syntax is the requirement (FR-013); how that is done is for the plan, with these constraints: copying the gallery's code keeps its MIT notice, and SC-002 checks the result against the gallery's own parser in the test suite, where the gallery is installed.

## Overrides follow the template loaders, not the list of installed apps

A project's own template folder usually overrides a package's component, and between apps the first one in `INSTALLED_APPS` wins. Both follow from Django asking its template loaders in order and taking the first file found. The command follows the same order rather than reproducing either rule, so it agrees with what a page renders (SC-004). django-cotton's own loader also searches `BASE_DIR/templates` when that folder exists, even if `TEMPLATES` `DIRS` does not name it, so the command covers that folder too.

## Usage counts page templates, not components

"How many templates use it" is counted across every folder the project loads templates from, including installed packages, but never inside a `COTTON_DIR` folder. A component used inside another component is a building block of that component, not a choice a page made, so counting it would make a near-copy look settled on. The JSON output gives the paths of the templates it counted.

## A name that matches nothing suggests the closest names

`--show` exists for a name the developer already believes is right, so a miss is usually a typo or a wrong folder. Listing the closest names (`card.title` for `card.titel`) gets the next attempt right, where an error alone costs a full list.

## Hidden props are shown

The gallery's `hidden` marker hides a prop from the gallery's interactive controls. A developer reading the documentation still needs to know the prop exists, so it is shown and marked hidden.
