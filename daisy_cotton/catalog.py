"""Find the Cotton components a project can render, in template-loader order."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.template import engines
from django.template.backends.django import DjangoTemplates

from daisy_cotton.annotations import AnnotationParser, ParsedComponent

__all__ = ["Component", "ComponentCatalog", "ComponentNotFound"]

PROJECT_PACKAGE = "project"
NO_DESCRIPTION = "—"
FIRST_SENTENCE = re.compile(r"(.+?[.!?])(?=\s+[A-Z])", re.S)
TAG_REFERENCE = re.compile(r"<c-([\w.-]+)|\{%\s*cotton\s+([\w.-]+)")
NOT_COMPONENTS = frozenset({"vars", "component"})
SUGGESTION_LIMIT = 5
SUGGESTION_CUTOFF = 0.6


@dataclass(frozen=True)
class Component:
    """One Cotton component the project can render.

    Attributes:
        name: Dotted name used in the tag, for example `card.title`.
        path: Absolute path of the copy that renders.
        package: App label that holds the copy, or `project`.
        overrides: Packages of the other copies, in loader order.
        source: File text, or an empty string when the file cannot be read.
    """

    name: str
    path: Path
    package: str
    overrides: tuple[str, ...]
    source: str

    @property
    def tag(self) -> str:
        """The opening tag a template writes to use this component."""
        return f"<c-{self.name}>"

    @cached_property
    def documentation(self) -> ParsedComponent:
        """The annotations read from the file, parsed once."""
        return AnnotationParser().parse(self.source)

    @property
    def summary(self) -> str:
        """The first sentence of the description, or an em dash when there is none."""
        description = " ".join(self.documentation.description.split())
        if not description:
            return NO_DESCRIPTION
        match = FIRST_SENTENCE.match(description)
        return match.group(1) if match else description


class ComponentNotFound(LookupError):
    """No component has the name asked for.

    Attributes:
        name: The name as it was asked for.
        suggestions: Up to five real names that are close to it, closest first.
    """

    def __init__(self, name: str, suggestions: tuple[str, ...] = ()) -> None:
        """Keep the name and the closest real names.

        Args:
            name: The name that matched no component.
            suggestions: Real component names close to ``name``.
        """
        super().__init__(name)
        self.name = name
        self.suggestions = suggestions


@dataclass(frozen=True)
class Candidate:
    """A template file that could render a component, before overrides are settled."""

    folder_index: int
    is_file: bool
    path: Path
    package: str


class ComponentCatalog:
    """Every component the project can render, found as the loaders find them."""

    def __init__(self) -> None:
        """Read the settings that say where components live and how they are named."""
        self.cotton_dir: str = getattr(settings, "COTTON_DIR", "cotton")
        self.snake_cased: bool = getattr(settings, "COTTON_SNAKE_CASED_NAMES", True)

    def folders(self) -> list[Path]:
        """Template folders in the order the template loaders search them.

        Returns:
            Resolved folders, each once, first position kept.
        """
        found: list[Path] = []
        for engine in engines.all():
            if isinstance(engine, DjangoTemplates):
                self.collect_folders(engine.engine.template_loaders, found)
        return found

    def components(self) -> list[Component]:
        """Every component, once each as the copy that renders.

        Returns:
            Components sorted by name.
        """
        packages = self.package_labels()
        candidates: dict[str, list[Candidate]] = {}
        for index, folder in enumerate(self.folders()):
            package = packages.get(folder, PROJECT_PACKAGE)
            root = folder / self.cotton_dir
            for path in sorted(root.rglob("*.html")):
                located = self.locate(path.relative_to(root))
                if located is not None:
                    name, is_file = located
                    candidates.setdefault(name, []).append(
                        Candidate(index, is_file, path, package)
                    )
        return [
            self.build_component(name, found)
            for name, found in sorted(candidates.items())
        ]

    def search(
        self, term: str = "", text: str = "", package: str = ""
    ) -> list[Component]:
        """Components that match every filter given.

        Args:
            term: Part of the name, ignoring case. Hyphens match underscores when
                snake-cased names are on.
            text: Words the description must contain, ignoring case.
            package: Exact package label.

        Returns:
            Matching components sorted by name.
        """
        wanted_name = self.normalise(term)
        wanted_text = text.lower()
        return [
            component
            for component in self.components()
            if wanted_name in self.normalise(component.name)
            and wanted_text in component.documentation.description.lower()
            and (not package or component.package == package)
        ]

    def get(self, name: str) -> Component:
        """Find the component a tag with this name renders.

        Args:
            name: Dotted name. Case is ignored, and hyphens match underscores when
                snake-cased names are on.

        Returns:
            The matching component.

        Raises:
            ComponentNotFound: No component has the name. It carries up to five
                close names.
        """
        components = self.components()
        wanted = self.normalise(name)
        for component in components:
            if self.normalise(component.name) == wanted:
                return component
        by_normalised = {self.normalise(c.name): c.name for c in components}
        close = difflib.get_close_matches(
            wanted, by_normalised, n=SUGGESTION_LIMIT, cutoff=SUGGESTION_CUTOFF
        )
        raise ComponentNotFound(name, tuple(by_normalised[n] for n in close))

    def uses(self, component: Component) -> list[Path]:
        """Page templates that reference the component by tag.

        Templates inside any folder's cotton directory are not counted, and a
        dynamic ``<c-component is="...">`` reference cannot be matched to a name.

        Args:
            component: The component to look for.

        Returns:
            Paths of the templates that use it, once each, sorted.
        """
        wanted = self.normalise(component.name)
        found: set[Path] = set()
        for folder in self.folders():
            components_root = folder / self.cotton_dir
            for path in folder.rglob("*.html"):
                if path.is_relative_to(components_root) or path in found:
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                if self.refers_to(text, wanted):
                    found.add(path)
        return sorted(found)

    def refers_to(self, text: str, wanted: str) -> bool:
        """Whether the template text names the component, already normalised."""
        for match in TAG_REFERENCE.finditer(text):
            name = match.group(1) or match.group(2)
            if name not in NOT_COMPONENTS and self.normalise(name) == wanted:
                return True
        return False

    def normalise(self, value: str) -> str:
        """Lower-case a name, reading hyphens as underscores in snake-cased names."""
        value = value.lower()
        return value.replace("-", "_") if self.snake_cased else value

    def collect_folders(self, loaders, found: list[Path]) -> None:
        """Append each loader's folders to ``found``, including wrapped loaders."""
        for loader in loaders:
            get_dirs = getattr(loader, "get_dirs", None)
            if get_dirs is not None:
                for folder in get_dirs():
                    resolved = Path(folder).resolve()
                    if resolved not in found:
                        found.append(resolved)
            self.collect_folders(getattr(loader, "loaders", ()), found)

    @staticmethod
    def package_labels() -> dict[Path, str]:
        """Map each installed app's template folder to the app's label."""
        return {
            Path(config.path, "templates").resolve(): config.label
            for config in apps.get_app_configs()
        }

    def locate(self, relative: Path) -> tuple[str, bool] | None:
        """Name and kind of a file below the cotton folder, or None if no tag can."""
        parts = [*relative.parts[:-1], relative.stem]
        if any(part.startswith("_") or "." in part for part in parts):
            return None
        if self.snake_cased and any("-" in part for part in parts):
            return None
        is_file = relative.name != "index.html" or len(parts) == 1
        return ".".join(parts if is_file else parts[:-1]), is_file

    @staticmethod
    def build_component(name: str, found: list[Candidate]) -> Component:
        """Pick the copy that renders and record the packages it overrides."""
        winner = next((c for c in found if c.is_file), found[0])
        overrides: list[str] = []
        for candidate in found:
            if (
                candidate.package != winner.package
                and candidate.package not in overrides
            ):
                overrides.append(candidate.package)
        try:
            source = winner.path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            source = ""
        return Component(name, winner.path, winner.package, tuple(overrides), source)
