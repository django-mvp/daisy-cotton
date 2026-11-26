"""List the Cotton components a project can render."""

from __future__ import annotations

import json
from dataclasses import asdict

from django.core.management.base import BaseCommand, CommandError

from daisy_cotton.annotations import Prop, Slot
from daisy_cotton.catalog import (
    NO_DESCRIPTION,
    Component,
    ComponentCatalog,
    ComponentNotFound,
)


class Command(BaseCommand):
    """Print one line for each Cotton component the project can use."""

    help = "List the Cotton components the project can render, from every package."

    def add_arguments(self, parser):
        """Declare the search term and the filters."""
        parser.add_argument(
            "term", nargs="?", default="", help="Part of a component name."
        )
        parser.add_argument(
            "--text", default="", help="Words the description must contain."
        )
        parser.add_argument(
            "--package", default="", help="Only components from this package."
        )
        parser.add_argument(
            "--show",
            default="",
            metavar="NAME",
            help="Document one component. Ignores the term and the filters.",
        )
        parser.add_argument(
            "--json", action="store_true", help="Print JSON instead of text."
        )

    def handle(self, *args, **options):
        """Print the components that match, or one component's documentation."""
        if options["show"]:
            self._show(options["show"], as_json=options["json"])
            return
        components = ComponentCatalog().search(
            options["term"], text=options["text"], package=options["package"]
        )
        if options["json"]:
            self.stdout.write(
                json.dumps([self._as_dict(c) for c in components], indent=2)
            )
        elif components:
            self._write_list(components)
        else:
            self.stdout.write("No component matches.")

    def _show(self, name: str, *, as_json: bool) -> None:
        """Print one component's documentation, as text or JSON."""
        catalog = ComponentCatalog()
        try:
            component = catalog.get(name)
        except ComponentNotFound as error:
            message = f"No component named '{error.name}'."
            if error.suggestions:
                message += f" Closest: {', '.join(error.suggestions)}"
            raise CommandError(message) from error
        uses = catalog.uses(component)
        if as_json:
            data = self._as_dict(component) | self._documentation_dict(component, uses)
            self.stdout.write(json.dumps(data, indent=2))
        else:
            self._write_documentation(component, uses)

    @staticmethod
    def _documentation_dict(component: Component, uses: list) -> dict:
        """Collect the fields only one component's documentation carries."""
        parsed = component.documentation
        return {
            "description": parsed.description or None,
            "props": [asdict(prop) for prop in parsed.props],
            "slots": [asdict(slot) for slot in parsed.slots],
            "accepts_attrs": parsed.accepts_attrs,
            "uses": len(uses),
            "use_paths": [str(path) for path in uses],
        }

    def _write_documentation(self, component: Component, uses: list) -> None:
        """Write the text form of one component's documentation."""
        parsed = component.documentation
        package = f"Package: {component.package}"
        if component.overrides:
            package += f"   (overrides: {', '.join(component.overrides)})"
        self.stdout.write(component.tag)
        self.stdout.write(f"File: {component.path}")
        self.stdout.write(package)
        if uses:
            noun = "template" if len(uses) == 1 else "templates"
            self.stdout.write(
                f'Used by {len(uses)} {noun} (dynamic <c-component is="…"> '
                "references are not counted)"
            )
        else:
            self.stdout.write(
                "No template uses it (dynamic references are not counted)"
            )
        self.stdout.write("")
        self.stdout.write(" ".join(parsed.description.split()) or NO_DESCRIPTION)
        self.stdout.write("")
        self._write_section("Props", [self._prop_line(p) for p in parsed.props])
        self._write_section("Slots", [self._slot_line(s) for s in parsed.slots])
        self.stdout.write(
            "Passes extra attributes to its element."
            if parsed.accepts_attrs
            else "Does not pass extra attributes."
        )

    def _write_section(self, title: str, lines: list[str]) -> None:
        """Write a heading and its indented lines, or the heading with `none`."""
        if not lines:
            self.stdout.write(f"{title}: none")
            return
        self.stdout.write(f"{title}:")
        for line in lines:
            self.stdout.write(f"  {line}")

    @staticmethod
    def _prop_line(prop: Prop) -> str:
        """One line for a prop: name, type, options, default, flags, description."""
        parts = [prop.name, prop.type]
        if prop.options:
            parts[-1] += f" [{', '.join(prop.options)}]"
        if prop.has_default:
            parts.append(f"default {json.dumps(prop.default)}")
        if prop.required:
            parts.append("required")
        if prop.deprecated is not None:
            parts.append(f"deprecated: {prop.deprecated}")
        if prop.hidden:
            parts.append("hidden")
        line = "  ".join(parts)
        return f"{line}  — {prop.description}" if prop.description else line

    @staticmethod
    def _slot_line(slot: Slot) -> str:
        """One line for a slot: name or default, description, example content."""
        line = slot.name or "(default)"
        if slot.description:
            line += f"  — {slot.description}"
        if slot.content:
            line += f"  e.g. {slot.content}"
        return line

    def _write_list(self, components: list[Component]) -> None:
        tag_width = max(len(c.tag) for c in components)
        package_width = max(len(c.package) for c in components)
        for component in components:
            line = (
                f"{component.tag.ljust(tag_width)}  "
                f"{component.package.ljust(package_width)}  {component.summary}"
            )
            if component.overrides:
                line += f" (overrides {', '.join(component.overrides)})"
            self.stdout.write(line)
        noun = "component" if len(components) == 1 else "components"
        self.stdout.write(f"{len(components)} {noun}")

    @staticmethod
    def _as_dict(component: Component) -> dict:
        has_description = bool(component.documentation.description)
        return {
            "name": component.name,
            "tag": component.tag,
            "package": component.package,
            "path": str(component.path),
            "summary": component.summary if has_description else None,
            "overrides": list(component.overrides),
        }
