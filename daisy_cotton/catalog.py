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

try:
    from django_cotton.templatetags._component import CottonComponentNode
except ImportError:  # pragma: no cover - django-cotton is a hard dependency
    CottonComponentNode = None

__all__ = ["Component", "ComponentCatalog", "ComponentNotFound"]

DEFAULT_COTTON_DIR = "cotton"
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


class ComponentCatalog:
    """Every component the project can render, found as the loaders find them.

    Components are searched where django-cotton looks, in its order: the
    configured ``COTTON_DIR`` first, then, in django-cotton 2.9 and later, the
    default ``cotton/`` folder. Each place is searched across every template
    folder in loader order before the next one.

    Attributes:
        cotton_dir: The ``COTTON_DIR`` setting, ``cotton`` when unset.
        snake_cased: The ``COTTON_SNAKE_CASED_NAMES`` setting, on when unset.
    """

    def __init__(self) -> None:
        self.cotton_dir: str = getattr(settings, "COTTON_DIR", DEFAULT_COTTON_DIR)
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
        copies: dict[str, list[tuple[str, Path]]] = {}
        names: set[str] = set()
        for folder in self.folders():
            package = packages.get(folder, PROJECT_PACKAGE)
            for directory in self.component_dirs():
                root = folder / directory
                for path in sorted(root.rglob("*.html")):
                    relative = path.relative_to(root)
                    name = self.locate(relative, directory != self.cotton_dir)
                    if name is not None:
                        names.add(name)
                        key = f"{directory}/{relative.as_posix()}"
                        copies.setdefault(key, []).append((package, path))
        return [self.build_component(name, copies) for name in sorted(names)]

    def component_dirs(self) -> tuple[str, ...]:
        """Template sub-folders that components are loaded from, in lookup order.

        Returns:
            The configured folder, then ``cotton`` when django-cotton falls back
            to it and it is a different folder.
        """
        if len(self.candidate_paths("x")) > 2:
            return (self.cotton_dir, DEFAULT_COTTON_DIR)
        return (self.cotton_dir,)

    def candidate_paths(self, name: str) -> tuple[str, ...]:
        """Template paths a tag with this name is rendered from, best first.

        Uses django-cotton's own list when the installed version has one (2.9
        and later), so the catalog follows its fallback to ``cotton/``. Older
        versions load the configured file, then its ``index.html``.

        Args:
            name: Dotted component name as it is written in the tag.

        Returns:
            Template paths in the order django-cotton tries them.
        """
        probe = getattr(CottonComponentNode, "_candidate_template_paths", None)
        if probe is not None:
            paths: tuple[str, ...] = probe(name, None)
            return paths
        base = f"{self.cotton_dir}/{name.replace('.', '/')}"
        return (f"{base}.html", f"{base}/index.html")

    def search(
        self, term: str = "", text: str = "", package: str = ""
    ) -> list[Component]:
        """Components that match every filter given.

        Args:
            term: Part of the name, ignoring case. Hyphens match underscores.
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
            name: Dotted name. Case is ignored, and hyphens match underscores.

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

        Templates inside any folder components are loaded from are not counted,
        and a dynamic ``<c-component is="...">`` reference cannot be matched to a name.

        Args:
            component: The component to look for.

        Returns:
            Paths of the templates that use it, once each, sorted.
        """
        wanted = self.normalise(component.name)
        found: set[Path] = set()
        for folder in self.folders():
            roots = [folder / directory for directory in self.component_dirs()]
            for path in folder.rglob("*.html"):
                if path in found or any(path.is_relative_to(r) for r in roots):
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                if self.refers_to(text, wanted):
                    found.add(path)
        return sorted(found)

    def refers_to(self, text: str, wanted: str) -> bool:
        """Whether the template text names the component.

        Args:
            text: The template's source.
            wanted: The component name, already normalised.

        Returns:
            True when a ``<c-name`` or ``{% cotton name %}`` tag names it.
        """
        for match in TAG_REFERENCE.finditer(text):
            name = match.group(1) or match.group(2)
            if name not in NOT_COMPONENTS and self.normalise(name) == wanted:
                return True
        return False

    def normalise(self, value: str) -> str:
        """Lower-case a name and read hyphens as underscores.

        Args:
            value: A component name.

        Returns:
            The name in the form names are compared in.
        """
        return value.lower().replace("-", "_")

    def collect_folders(self, loaders, found: list[Path]) -> None:
        """Append each loader's folders to ``found``, including wrapped loaders.

        Args:
            loaders: Template loaders, some of which wrap others.
            found: Resolved folders so far. Extended in place, each folder once.
        """
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
        """Map each installed app's template folder to the app's label.

        Returns:
            Resolved ``templates`` folder of every installed app, by its label.
        """
        return {
            Path(config.path, "templates").resolve(): config.label
            for config in apps.get_app_configs()
        }

    def locate(self, relative: Path, fallback: bool) -> str | None:
        """Name of the component a file below a component folder renders.

        Args:
            relative: The file's path below the folder.
            fallback: Whether the folder is the default ``cotton`` one that
                django-cotton falls back to, which only holds snake-cased names.

        Returns:
            The dotted name, or None when no tag can name the file.
        """
        parts = [*relative.parts[:-1], relative.stem]
        if any(part.startswith("_") or "." in part for part in parts):
            return None
        if (self.snake_cased or fallback) and any("-" in part for part in parts):
            return None
        is_file = relative.name != "index.html" or len(parts) == 1
        return ".".join(parts if is_file else parts[:-1])

    def build_component(
        self, name: str, copies: dict[str, list[tuple[str, Path]]]
    ) -> Component:
        """Pick the copy that renders and record the packages it overrides.

        Args:
            name: Dotted component name.
            copies: Every file found, by template path, in loader order.

        Returns:
            The component, rendered from the first path django-cotton tries that
            has a file, in the first folder that holds it.
        """
        found = [c for path in self.candidate_paths(name) for c in copies.get(path, [])]
        package, path = found[0]
        overrides = tuple(dict.fromkeys(p for p, _ in found if p != package))
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            source = ""
        return Component(name, path, package, overrides, source)
