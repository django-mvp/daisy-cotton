# Feature Specification: List the Cotton components a project can use

**Feature Branch**: `011-component-listing`

**Created**: 2026-11-26

**Status**: Draft

**Serves**: G2 · **Roadmap**: — · **Depends on**: —

**Input**: Issue #171, "List the Cotton components a project can use": a management command that lists every Cotton component a project can use, its own and every installed package's, and prints the documentation of any one of them from its comment header. A developer, or a coding agent working in the project, finds the component that already does the job before writing a new one. Searching by any part of a name keeps the list short, and a component's full documentation shows its props, its slots and how many of the project's templates already use it.

## Scope

A project that installs daisy-cotton gains a `cotton_components` management command. It reads the components the project can render and the annotations at the top of each one (`@description`, `@prop`, `@slot`), and prints them in two shapes:

| Shape | Invoked as | Prints |
|---|---|---|
| List | `manage.py cotton_components [term]` | One line per component: its tag, the package it comes from, and the first sentence of its description |
| Full documentation | `manage.py cotton_components --show <name>` | One component's file, package, what it overrides, description, props, slots and how many templates use it |

The command covers every Cotton component the project can render, not only daisy-cotton's own. It never prints a component's template body.

**This widens the package's scope by one item.** The README's *Scope & philosophy* says the package is one Cotton component for each base daisyUI component and nothing else. This command is the one exception, and the README says so. It adds no runtime dependency: the package still depends on Django and django-cotton alone (Article XI).

Out of scope:

- Rendering or previewing a component. The component gallery does that.
- Checking annotations for mistakes. The gallery's `cotton_lint` does that.
- Changing any component or its annotations.

## Clarifications

### Session 2026-11-26

- Q: Which components does the command list? → A: Every component the project can render with a `<c-…>` tag: those in the project's own template folders and those in every installed app's `templates/` folder, under the project's `COTTON_DIR` (default `cotton`). It finds them the way django-cotton does when a page renders, so the list never shows a component the project cannot use, or misses one it can.
- Q: What name does each component get? → A: The name used in its tag: folders become dots (`cotton/card/title.html` is `card.title`), and `<folder>/index.html` is the component named after the folder (`cotton/card/index.html` is `card`). A file that sits beside a folder of the same name wins over the folder's `index.html`, as it does in django-cotton.
- Q: What happens when two template folders provide a component with the same name? → A: It is listed once, under the copy that renders, which is the first one Django's template loaders find. Its line notes that it overrides another package's copy, and `--show` names the package it overrides.
- Q: What does "the package it comes from" mean? → A: The installed app whose `templates/` folder holds the file, by its app label. A file in a project-level template folder (`TEMPLATES` `DIRS`) is shown as `project`.
- Q: How does the search term match? → A: Anywhere in the component's name, ignoring case. `card` matches `card`, `card.title`, `mvp.card` and `profile_card`. Hyphens and underscores in the term and the name are treated as the same character, because django-cotton treats `<c-hover-gallery>` and `<c-hover_gallery>` as the same component by default.
- Q: Can a developer search descriptions? → A: Yes, with `--text <words>`, which keeps components whose description contains the words, ignoring case. It combines with the name term: both must match.
- Q: Can the list be limited to one package? → A: Yes, with `--package <label>`, which combines with the other filters.
- Q: How long is a description in the list? → A: Its first sentence. A description is often several sentences, and the list is meant to be scanned. The full description appears under `--show`.
- Q: What does the list show for a component with no `@description`? → A: An em dash in place of the description. It is still listed.
- Q: Which files are skipped? → A: Any file in a folder, or with a name, that starts with `_`, the convention the component gallery uses for private partials. Only `.html` files are components.
- Q: What does "how many templates use it" count? → A: The template files, in every folder the project loads templates from, that reference the component by its tag (`<c-card.title`) or by the `{% cotton card.title %}` tag. Templates inside a `COTTON_DIR` folder are not counted: they are components themselves, and one component using another says nothing about which component the project's pages have settled on. The full documentation prints the count. A dynamic reference (`<c-component is="…">`) names the component only at render time, so it is not counted, and the documentation says the count excludes dynamic references.
- Q: What does `--show` do with a name that matches nothing? → A: It exits with an error that names the term and lists up to five components with the closest names, so the next attempt can be exact.
- Q: Is there machine-readable output? → A: Yes. `--json` prints the same information as JSON, for the list and for `--show`. In JSON, `--show` also gives the paths of the templates that use the component, not only the count.
- Q: What does the bare command print in a project with many components? → A: Every component, one line each, followed by a count. A django-mvp project has about 190 components, which is short enough to read once. The search and filters exist to shorten it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A developer finds the components that fit a need (Priority: P1)

A developer, or a coding agent, about to write a page needs a card for an author. They run `manage.py cotton_components card` and see every component whose name contains "card", from the project and every installed package, each with the tag to write, where it comes from, and one sentence on what it is. They pick one instead of writing a new card.

**Why this priority**: Finding what exists is the whole point. Without the list, a developer has to know which packages ship components and open their folders one by one, and most never do.

**Independent Test**: In a project with components in its own template folder, in daisy-cotton and in a second installed app, run the command with and without a term, `--text` and `--package`, and compare what it prints with the files on disk.

**Acceptance Scenarios**:

1. **Given** a project with components in its own template folder and in two installed apps, **When** the developer runs `cotton_components` with no arguments, **Then** it prints one line per component, including every component from all three places, each with its tag, its package and the first sentence of its description, followed by the number of components listed.
2. **Given** components named `card`, `card.title`, `mvp.card` and `badge`, **When** the developer runs `cotton_components card`, **Then** the first three are listed and `badge` is not.
3. **Given** the term `CARD`, **When** the command runs, **Then** it lists the same components as `card`.
4. **Given** a component file `hover_gallery.html`, **When** the developer searches for `hover-gallery`, **Then** the component is listed.
5. **Given** `cotton/card/index.html` and `cotton/card/title.html`, **When** the list prints, **Then** they appear as `card` and `card.title`.
6. **Given** both `cotton/stat.html` and `cotton/stat/index.html` in one folder, **When** the list prints, **Then** `stat` appears once, from `stat.html`.
7. **Given** a project that overrides daisy-cotton's `card` in its own template folder, **When** the list prints, **Then** `card` appears once, from `project`, and its line says it overrides `daisy_cotton`.
8. **Given** a project whose settings set `COTTON_DIR = "components"`, **When** the command runs, **Then** it lists the components under `components/` in each template folder, and also those under `cotton/` when the installed django-cotton falls back to that folder for a name `components/` does not provide. A name found in both is the `components/` copy.
9. **Given** a component with no `@description`, **When** the list prints, **Then** its line shows an em dash in place of the description.
10. **Given** a file under `cotton/_partials/`, **When** the list prints, **Then** it is not listed.
11. **Given** `--text "author"`, **When** the command runs, **Then** it lists only components whose description contains "author", ignoring case. Given a name term as well, it lists only components that match both.
12. **Given** `--package daisy_cotton`, **When** the command runs, **Then** it lists only daisy-cotton's components.
13. **Given** a term that matches nothing, **When** the command runs, **Then** it says no component matches and exits successfully.
14. **Given** `--json`, **When** the command runs, **Then** it prints a JSON array with one object per listed component carrying its name, tag, package, file path, description summary and the package it overrides, if any.

---

### User Story 2 - A developer reads one component's documentation (Priority: P2)

Having found `card.title`, the developer runs `manage.py cotton_components --show card.title` to learn how to use it: every prop with its type, options and default, every slot, and the file it lives in. They also see that 14 of the project's templates already use it, which tells them it is the one the project has settled on, not a near-copy nobody uses.

**Why this priority**: The list says what exists. Using a component well needs its props and slots, which today means opening the template. It comes second because a developer who knows the name can still open the file.

**Independent Test**: Run `--show` against components with props, select options, defaults, required props, named slots and none of these, in a project where some templates use them, and compare the output with each file's annotations and the templates on disk.

**Acceptance Scenarios**:

1. **Given** daisy-cotton's `card`, **When** the developer runs `cotton_components --show card`, **Then** it prints the component's tag, its file path, its package, its full description, every prop and every slot, and never the template body.
2. **Given** a prop annotated `variant:select['primary','secondary'] | default:"primary" | description:"…"`, **When** the documentation prints, **Then** that prop shows its name, its type, its two options, its default and its description.
3. **Given** a prop annotated `required`, **When** the documentation prints, **Then** the prop is marked required. A prop annotated `deprecated:"…"` is marked deprecated with its message. A prop annotated `hidden` is still shown, marked hidden.
4. **Given** a default slot and named slots, **When** the documentation prints, **Then** each slot shows its name, or that it is the default slot, its description and its example content where the annotation gives one.
5. **Given** a component that renders `{{ attrs }}`, **When** the documentation prints, **Then** it says the component passes extra attributes to its element.
6. **Given** a component that three page templates reference with `<c-card.title`, one with `{% cotton card.title %}`, and two other components use inside their own markup, **When** the documentation prints, **Then** it says four templates use it. The two components are not counted.
7. **Given** a component no template uses, **When** the documentation prints, **Then** it says no template uses it.
8. **Given** a component the project overrides, **When** the developer runs `--show` for it, **Then** the documentation is that of the copy that renders, and it names the package whose copy it overrides.
9. **Given** `--show card.titel`, a name that does not exist, **When** the command runs, **Then** it exits with an error naming the term and lists up to five components with the closest names, `card.title` among them.
10. **Given** `--show card --json`, **When** the command runs, **Then** it prints one JSON object with the same information, including the paths of the templates that use the component.
11. **Given** a component with no annotations at all, **When** the documentation prints, **Then** it shows the tag, file and package, an em dash for the description, and that the component declares no props and no slots.

---

### Edge Cases

- A template folder that does not exist, or a `cotton` folder that holds no `.html` files, contributes nothing and raises no error.
- A component file that cannot be read as text is listed with an em dash and does not stop the command.
- An annotation the parser cannot read (a malformed `@prop`) is left out of the documentation, and the rest of the component's documentation still prints.
- A project that sets `COTTON_SNAKE_CASED_NAMES = False` keeps hyphens and underscores distinct when matching a term to a name, except where the installed django-cotton itself falls back to the snake-cased file under `cotton/`: such a component is found by its hyphenated name too.
- A project with `APP_DIRS` turned off, and no `app_directories` loader, gets no components from installed apps, because it cannot render them either.
- A description's first sentence ends at the first full stop followed by a space and a capital letter, or at the end of the description, so a version number ("v1.2") or an abbreviation inside a sentence does not cut it short.

## Requirements *(mandatory)*

### Functional Requirements

**Finding components**

- **FR-001**: The package MUST provide a `cotton_components` management command, available in any project that has `daisy_cotton` in `INSTALLED_APPS`. *(US1, US2)*
- **FR-002**: The command MUST find components in the folders, and in the order, that the project's template loaders search, under the project's `COTTON_DIR` setting (default `cotton`), and under `cotton/` with snake-cased names wherever the installed django-cotton falls back to it. *(US1)*
- **FR-003**: Each component's name MUST be the name django-cotton resolves from a tag: folders joined with dots, `<folder>/index.html` named after its folder, and a file beside a folder of the same name winning over the folder's `index.html`. *(US1)*
- **FR-004**: A component provided by more than one folder MUST be listed once, as the copy the template loaders find first, recording the package of each copy it overrides. *(US1, US2)*
- **FR-005**: Each component MUST record its package: the label of the installed app whose `templates/` folder holds it, or `project` for a project-level template folder. *(US1, US2)*
- **FR-006**: Files and folders whose names start with `_`, and files that are not `.html`, MUST NOT be listed. *(US1)*

**The list**

- **FR-007**: With no `--show`, the command MUST print one line per component, sorted by name, giving its tag, its package, the first sentence of its `@description` (or an em dash) and any package it overrides, followed by the number of components listed. *(US1)*
- **FR-008**: An optional search term MUST keep only components whose name contains it, ignoring case, and treating hyphens and underscores as the same when `COTTON_SNAKE_CASED_NAMES` is on (its default). *(US1)*
- **FR-009**: `--text <words>` MUST keep only components whose description contains the words, ignoring case. `--package <label>` MUST keep only that package's components. Every filter given MUST apply together. *(US1)*

**One component's documentation**

- **FR-010**: `--show <name>` MUST print the named component's tag, file path, package, any packages it overrides, full description, every prop (name, type, options, default, required, deprecated, hidden, description), every slot (name or default, description, example content) and whether it passes extra attributes to its element. It MUST NOT print the template body. *(US2)*
- **FR-011**: `--show` MUST print the number of template files, in every folder the project loads templates from, that reference the component by `<c-name` or `{% cotton name %}`, excluding every template inside a folder components are loaded from (`COTTON_DIR`, and `cotton/` where django-cotton falls back to it), and MUST state that dynamic references are not counted. *(US2)*
- **FR-012**: `--show` with a name that is not a component MUST exit with an error that names the term and lists up to five components with the closest names. *(US2)*

**Both**

- **FR-013**: Annotations MUST be read in the syntax the component gallery defines (`@description`, `@prop`, `@slot`), and a component whose annotations are partly malformed MUST still be listed and documented from what can be read. *(US1, US2)*
- **FR-014**: `--json` MUST print the list, or one component's documentation, as JSON carrying the same information, with the documentation also giving the paths of the templates that use the component. *(US1, US2)*
- **FR-015**: The command MUST add no runtime dependency beyond Django and django-cotton. *(US1, US2)*
- **FR-016**: The README MUST document the command, and its *Scope & philosophy* MUST name the command as the package's one item that is not a component. CONTEXT.md MUST say that the command lists any Cotton component, not only this package's. *(US1, US2)*

### Key Entities

- **Component**: one Cotton component the project can render. Its name, tag, file, package, the packages it overrides, and its annotations.
- **Annotation**: a `{# @description … #}`, `{# @prop … #}` or `{# @slot … #}` comment at the top of a component, in the gallery's syntax.
- **Use**: a template file that references a component by tag.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In the demo project, the bare command lists every one of daisy-cotton's components, and the number it prints equals the number of component files the gallery shows.
- **SC-002**: For every daisy-cotton component, `--show` reports the same props, slots and description as the gallery's own parser reads from the file.
- **SC-003**: A search for any part of a component's name, in either case and with either separator, lists that component.
- **SC-004**: In a project that overrides a component, the list and `--show` agree with what Django renders for that tag.
- **SC-005**: The package's runtime dependencies are unchanged, and `deptry` passes.

## Assumptions

- Components carry their annotations in the gallery's syntax, as daisy-cotton's and django-mvp's already do.
- A project's template loaders are Django's standard ones, or django-cotton's own loader, which searches the same folders.
- The gallery's annotation syntax stays as it is at 1.0. A later change to it is handled as a defect in this command.
