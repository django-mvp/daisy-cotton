"""List the Cotton components a project can render."""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from daisy_cotton.catalog import Component, ComponentCatalog


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
            "--json", action="store_true", help="Print JSON instead of text."
        )

    def handle(self, *args, **options):
        """Print the components that match, as text or JSON."""
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
