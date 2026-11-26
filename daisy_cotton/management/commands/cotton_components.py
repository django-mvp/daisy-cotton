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
            self.show_component(options["show"], as_json=options["json"])
            return
        components = ComponentCatalog().search(
            options["term"], text=options["text"], package=options["package"]
        )
        if options["json"]:
            self.stdout.write(
                json.dumps([self.as_dict(c) for c in components], indent=2)
            )
        elif components:
            self.write_list(components)
        else:
            self.stdout.write("No component matches.")

    def show_component(self, name: str, *, as_json: bool) -> None:
        """Print one component's documentation, as text or JSON.

        Args:
            name: The component name as the user typed it.
            as_json: Print one JSON object instead of text.

        Raises:
            CommandError: No component has the name. The message lists the
                closest names.
        """
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
            data = self.as_dict(component) | self.documentation_dict(component, uses)
            self.stdout.write(json.dumps(data, indent=2))
        else:
            self.write_documentation(component, uses)

    @staticmethod
    def documentation_dict(component: Component, uses: list) -> dict:
        """Collect the fields only one component's documentation carries.

        Args:
            component: The component being documented.
            uses: Paths of the page templates that use it.

        Returns:
            A JSON-ready dict of its description, props, slots, whether it
            passes extra attributes, and its uses.
        """
        parsed = component.documentation
        return {
            "description": parsed.description or None,
            "props": [asdict(prop) for prop in parsed.props],
            "slots": [asdict(slot) for slot in parsed.slots],
            "accepts_attrs": parsed.accepts_attrs,
            "uses": len(uses),
            "use_paths": [str(path) for path in uses],
        }

    def write_documentation(self, component: Component, uses: list) -> None:
        """Write the text form of one component's documentation.

        Args:
            component: The component being documented.
            uses: Paths of the page templates that use it.
        """
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
        self.write_section("Props", [self.prop_line(p) for p in parsed.props])
        self.write_section("Slots", [self.slot_line(s) for s in parsed.slots])
        self.stdout.write(
            "Passes extra attributes to its element."
            if parsed.accepts_attrs
            else "Does not pass extra attributes."
        )

    def write_section(self, title: str, lines: list[str]) -> None:
        """Write a heading and its indented lines, or the heading with `none`.

        Args:
            title: The section heading.
            lines: The section's lines, without indentation.
        """
        if not lines:
            self.stdout.write(f"{title}: none")
            return
        self.stdout.write(f"{title}:")
        for line in lines:
            self.stdout.write(f"  {line}")

    @staticmethod
    def prop_line(prop: Prop) -> str:
        """Format one prop: name, type, options, default, flags, description.

        Args:
            prop: The prop to describe.

        Returns:
            The prop on a single line.
        """
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
    def slot_line(slot: Slot) -> str:
        """Format one slot: name or default, description, example content.

        Args:
            slot: The slot to describe.

        Returns:
            The slot on a single line.
        """
        line = slot.name or "(default)"
        if slot.description:
            line += f"  — {slot.description}"
        if slot.content:
            line += f"  e.g. {slot.content}"
        return line

    def write_list(self, components: list[Component]) -> None:
        """Write one padded line per component, then the count.

        Args:
            components: The components to list, in the order to print them.
        """
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
    def as_dict(component: Component) -> dict:
        """Return the list fields of one component, ready for JSON.

        Args:
            component: The component to describe.

        Returns:
            Its name, tag, package, path, summary and overrides.
        """
        has_description = bool(component.documentation.description)
        return {
            "name": component.name,
            "tag": component.tag,
            "package": component.package,
            "path": str(component.path),
            "summary": component.summary if has_description else None,
            "overrides": list(component.overrides),
        }
