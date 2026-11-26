"""Tests for the component catalog."""

from pathlib import Path

import pytest
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django_cotton.templatetags._component import CottonComponentNode
from django_cotton_gallery.core.catalog.scanner import scan
from django_cotton_gallery.core.schemas import CatalogConfig

import daisy_cotton
from daisy_cotton.catalog import ComponentCatalog, ComponentNotFound

FIRST = "tests.fixtures.catalog_first"
SECOND = "tests.fixtures.catalog_second"
PACKAGE_COTTON = Path(daisy_cotton.__path__[0]).resolve() / "templates" / "cotton"
FIRST_PAGES = (
    Path(__file__).parent / "fixtures" / "catalog_first" / "templates" / "pages"
)


@pytest.fixture
def project_dir(tmp_path):
    """A project-level template folder, empty, that the engine searches first."""
    path = tmp_path / "project_templates"
    path.mkdir()
    return path


@pytest.fixture
def configure(settings, project_dir):
    """Return a function pointing Django at the fixture apps and the project folder."""

    def _configure(apps=(FIRST, SECOND), dirs=None, loaders=None, **extra):
        settings.INSTALLED_APPS = list(apps)
        options = {"loaders": loaders} if loaders else {}
        settings.TEMPLATES = [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [project_dir] if dirs is None else dirs,
                "APP_DIRS": not loaders,
                "OPTIONS": options,
            }
        ]
        for key, value in extra.items():
            setattr(settings, key, value)

    return _configure


def write(folder, relative, text="{# @description Written for a test. #}\n"):
    path = folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def names(components):
    return [c.name for c in components]


class TestComponentCatalogFolders:
    def test_lists_the_project_folder_before_the_app_folders(
        self, configure, project_dir
    ):
        configure()

        folders = ComponentCatalog().folders()

        assert folders[0] == project_dir.resolve()
        assert [f.parent.name for f in folders[1:]] == [
            "catalog_first",
            "catalog_second",
        ]

    def test_follows_installed_apps_order(self, configure):
        configure(apps=(SECOND, FIRST))

        folders = ComponentCatalog().folders()

        assert [f.parent.name for f in folders[1:]] == [
            "catalog_second",
            "catalog_first",
        ]

    def test_a_missing_folder_contributes_nothing(self, configure, tmp_path):
        configure(dirs=[tmp_path / "missing"])

        assert names(ComponentCatalog().components())

    def test_without_the_app_directories_loader_apps_contribute_nothing(
        self, configure, project_dir
    ):
        write(project_dir, "cotton/only_project.html")
        configure(loaders=["django.template.loaders.filesystem.Loader"])

        catalog = ComponentCatalog()

        assert catalog.folders() == [project_dir.resolve()]
        assert names(catalog.components()) == ["only_project"]


class TestComponentCatalogComponents:
    def test_lists_components_from_the_project_and_every_app(
        self, configure, project_dir
    ):
        write(project_dir, "cotton/dashboard.html")
        configure()

        by_name = {c.name: c.package for c in ComponentCatalog().components()}

        assert by_name["dashboard"] == "project"
        assert by_name["badge"] == "catalog_first"
        assert by_name["mvp.card"] == "catalog_second"

    def test_sorts_components_by_name(self, configure):
        configure()

        listed = names(ComponentCatalog().components())

        assert listed == sorted(listed)

    def test_folders_become_dots(self, configure):
        configure()

        assert "card.title" in names(ComponentCatalog().components())

    def test_index_file_is_named_after_its_folder(self, configure, project_dir):
        write(project_dir, "cotton/panel/index.html")
        configure()

        listed = names(ComponentCatalog().components())

        assert "panel" in listed
        assert "panel.index" not in listed

    def test_sibling_file_wins_over_folder_index_without_an_override(
        self, configure, project_dir
    ):
        file_copy = write(project_dir, "cotton/stat.html")
        write(project_dir, "cotton/stat/index.html")
        configure()

        stat = next(c for c in ComponentCatalog().components() if c.name == "stat")

        assert stat.path == file_copy.resolve()
        assert stat.overrides == ()

    def test_file_in_a_later_folder_wins_over_an_index_in_an_earlier_one(
        self, configure
    ):
        configure()

        wide = next(c for c in ComponentCatalog().components() if c.name == "wide")

        assert wide.package == "catalog_second"
        assert wide.overrides == ("catalog_first",)

    def test_project_folder_overrides_the_apps(self, configure, project_dir):
        copy = write(project_dir, "cotton/card.html")
        configure()

        cards = [c for c in ComponentCatalog().components() if c.name == "card"]

        assert len(cards) == 1
        assert cards[0].package == "project"
        assert cards[0].path == copy.resolve()
        assert cards[0].overrides == ("catalog_first", "catalog_second")

    @pytest.mark.parametrize(
        ("apps", "winner", "overridden"),
        [
            ((FIRST, SECOND), "catalog_first", ("catalog_second",)),
            ((SECOND, FIRST), "catalog_second", ("catalog_first",)),
        ],
    )
    def test_installed_apps_order_decides_between_apps(
        self, configure, apps, winner, overridden
    ):
        configure(apps=apps)

        card = next(c for c in ComponentCatalog().components() if c.name == "card")

        assert card.package == winner
        assert card.overrides == overridden

    def test_a_hyphenated_path_is_not_listed_when_names_are_snake_cased(
        self, configure, project_dir
    ):
        write(project_dir, "cotton/bad-name.html")
        write(project_dir, "cotton/dir-name/inner.html")
        configure()

        listed = names(ComponentCatalog().components())

        assert "bad-name" not in listed
        assert "dir-name.inner" not in listed

    def test_a_hyphenated_path_is_listed_when_snake_casing_is_off(
        self, configure, project_dir
    ):
        write(project_dir, "cotton/bad-name.html")
        configure(COTTON_SNAKE_CASED_NAMES=False)

        assert "bad-name" in names(ComponentCatalog().components())

    def test_a_stem_with_a_dot_is_not_listed(self, configure, project_dir):
        write(project_dir, "cotton/dotted.name.html")
        configure()

        assert not [n for n in names(ComponentCatalog().components()) if "dotted" in n]

    def test_private_folders_above_the_cotton_dir_do_not_hide_components(
        self, configure, tmp_path
    ):
        build = tmp_path / "_build" / "templates"
        write(build, "cotton/built.html")
        configure(dirs=[build])

        assert "built" in names(ComponentCatalog().components())

    def test_private_folders_and_files_below_the_cotton_dir_are_skipped(
        self, configure, project_dir
    ):
        write(project_dir, "cotton/_partials/inner.html")
        write(project_dir, "cotton/_x.html")
        write(project_dir, "cotton/card/_helper.html")
        configure()

        listed = names(ComponentCatalog().components())

        assert not [n for n in listed if "inner" in n or n == "_x" or "helper" in n]

    def test_files_that_are_not_html_are_ignored(self, configure, project_dir):
        write(project_dir, "cotton/notes.txt")
        write(project_dir, "cotton/styles.css")
        configure()

        listed = names(ComponentCatalog().components())

        assert "notes" not in listed
        assert "styles" not in listed

    def test_reads_the_configured_cotton_dir_then_falls_back_to_cotton(
        self, configure, project_dir
    ):
        write(project_dir, "components/chosen.html")
        write(project_dir, "cotton/fallback.html")
        write(project_dir, "other/ignored.html")
        configure(COTTON_DIR="components")

        listed = names(ComponentCatalog().components())

        assert {"chosen", "fallback", "badge"} <= set(listed)
        assert "ignored" not in listed

    def test_a_configured_copy_overrides_the_cotton_one(self, configure, project_dir):
        chosen = write(project_dir, "components/badge.html")
        configure(COTTON_DIR="components")

        badge = next(c for c in ComponentCatalog().components() if c.name == "badge")

        assert badge.path == chosen.resolve()
        assert badge.overrides == ("catalog_first",)

    def test_an_undecodable_file_is_listed_without_a_summary(
        self, configure, project_dir
    ):
        broken = project_dir / "cotton" / "broken.html"
        broken.parent.mkdir(parents=True)
        broken.write_bytes(b"\xff\xfe\x00 not utf-8 \xff")
        configure()

        broken_component = next(
            c for c in ComponentCatalog().components() if c.name == "broken"
        )

        assert broken_component.source == ""
        assert broken_component.summary == "—"


class TestComponent:
    @pytest.mark.parametrize(
        ("description", "expected"),
        [
            ("", "—"),
            ("One sentence.", "One sentence."),
            ("First one. Second one.", "First one."),
            (
                "Works since v1.2 of the library. Then more.",
                "Works since v1.2 of the library.",
            ),
            ("Shows e.g. a card. Then more.", "Shows e.g. a card."),
            ("No full stop at the end", "No full stop at the end"),
        ],
    )
    def test_summary_is_the_first_sentence(
        self, configure, project_dir, description, expected
    ):
        text = (
            f"{{# @description {description} #}}\n" if description else "<div></div>\n"
        )
        write(project_dir, "cotton/sample.html", text)
        configure()

        sample = next(c for c in ComponentCatalog().components() if c.name == "sample")

        assert sample.summary == expected

    def test_tag_is_the_name_in_angle_brackets(self, configure):
        configure()

        title = next(
            c for c in ComponentCatalog().components() if c.name == "card.title"
        )

        assert title.tag == "<c-card.title>"


class TestComponentCatalogSearch:
    def test_a_term_matches_anywhere_in_the_name(self, configure, project_dir):
        write(project_dir, "cotton/profile_card.html")
        configure()

        found = names(ComponentCatalog().search("card"))

        assert {"card", "card.title", "mvp.card", "profile_card"} <= set(found)
        assert "badge" not in found

    def test_a_term_ignores_case(self, configure):
        configure()
        catalog = ComponentCatalog()

        assert names(catalog.search("CARD")) == names(catalog.search("card"))

    def test_hyphen_in_the_term_finds_an_underscored_name(self, configure):
        configure()

        assert "hover_gallery" in names(ComponentCatalog().search("hover-gallery"))

    def test_hyphen_finds_the_underscored_file_when_snake_casing_is_off(
        self, configure
    ):
        configure(COTTON_SNAKE_CASED_NAMES=False)

        assert "hover_gallery" in names(ComponentCatalog().search("hover-gallery"))

    def test_text_keeps_components_whose_description_contains_the_words(
        self, configure
    ):
        configure()

        found = names(ComponentCatalog().search(text="AUTHOR"))

        assert found == ["mvp.card"]

    def test_text_and_term_must_both_match(self, configure):
        configure()
        catalog = ComponentCatalog()

        assert names(catalog.search("card", text="author")) == ["mvp.card"]
        assert catalog.search("badge", text="author") == []

    def test_package_keeps_only_that_package(self, configure):
        configure()

        found = ComponentCatalog().search(package="catalog_second")

        assert found
        assert {c.package for c in found} == {"catalog_second"}

    def test_package_combines_with_a_term(self, configure):
        configure()

        found = names(ComponentCatalog().search("card", package="catalog_second"))

        assert found == ["mvp.card"]

    def test_no_filters_returns_every_component(self, configure):
        configure()
        catalog = ComponentCatalog()

        assert catalog.search() == catalog.components()


class TestComponentCatalogGet:
    def test_returns_the_component_with_that_exact_name(self, configure):
        configure()

        assert ComponentCatalog().get("card.title").name == "card.title"

    def test_a_hyphen_finds_an_underscored_name(self, configure):
        configure()

        assert ComponentCatalog().get("hover-gallery").name == "hover_gallery"

    def test_a_hyphenated_name_gets_the_file_django_renders_when_snake_casing_is_off(
        self, configure
    ):
        configure(COTTON_SNAKE_CASED_NAMES=False)

        found = ComponentCatalog().get("hover-gallery")

        rendered = CottonComponentNode._candidate_template_paths("hover-gallery", None)
        assert found.path == Path(get_template(rendered[2]).origin.name).resolve()

    def test_the_name_ignores_case(self, configure):
        configure()

        assert ComponentCatalog().get("Card.Title").name == "card.title"

    def test_a_hyphen_finds_the_underscored_file_when_snake_casing_is_off(
        self, configure
    ):
        configure(COTTON_SNAKE_CASED_NAMES=False)

        assert ComponentCatalog().get("hover-gallery").name == "hover_gallery"

    def test_an_unknown_name_suggests_the_closest_names(self, configure):
        configure()

        with pytest.raises(ComponentNotFound) as caught:
            ComponentCatalog().get("card.titel")

        assert caught.value.name == "card.titel"
        assert "card.title" in caught.value.suggestions

    def test_at_most_five_names_are_suggested(self, configure, project_dir):
        for suffix in "abcdefgh":
            write(project_dir, f"cotton/widget_{suffix}.html")
        configure()

        with pytest.raises(ComponentNotFound) as caught:
            ComponentCatalog().get("widget_z")

        assert len(caught.value.suggestions) == 5

    def test_a_name_unlike_any_component_suggests_nothing(self, configure):
        configure()

        with pytest.raises(ComponentNotFound) as caught:
            ComponentCatalog().get("nothing")

        assert caught.value.suggestions == ()


class TestComponentCatalogUses:
    @pytest.fixture
    def title(self, configure, project_dir):
        write(project_dir, "pages/a.html", "<c-card.title>A</c-card.title>\n")
        write(project_dir, "pages/b.html", '<c-card.title class="x" />\n')
        write(project_dir, "pages/c.html", "{% cotton card.title %}C{% endcotton %}\n")
        write(project_dir, "pages/twice.html", "<c-card.title /><c-card.title />\n")
        write(project_dir, "pages/dynamic.html", '<c-component is="card.title" />\n')
        write(project_dir, "pages/other.html", "<c-card>x</c-card>\n")
        write(project_dir, "cotton/uses_title.html", "<c-card.title />\n")
        write(project_dir, "cotton/nested/uses_title.html", "<c-card.title />\n")
        configure()
        return ComponentCatalog().get("card.title")

    def test_counts_each_page_template_that_references_the_component(
        self, title, project_dir
    ):
        used = ComponentCatalog().uses(title)

        assert [p.name for p in used if project_dir.resolve() in p.parents] == [
            "a.html",
            "b.html",
            "c.html",
            "twice.html",
        ]

    def test_a_file_with_two_references_counts_once(self, title):
        used = ComponentCatalog().uses(title)

        assert [p.name for p in used].count("twice.html") == 1

    def test_component_files_are_not_counted(self, title):
        used = ComponentCatalog().uses(title)

        assert not [p for p in used if "uses_title" in p.name]

    def test_a_dynamic_reference_is_not_counted(self, title):
        used = ComponentCatalog().uses(title)

        assert "dynamic.html" not in [p.name for p in used]

    def test_a_longer_name_is_not_a_use(self, configure, project_dir):
        write(project_dir, "pages/longer.html", "<c-card.titles />\n")
        configure()
        catalog = ComponentCatalog()

        assert catalog.uses(catalog.get("card.title")) == [
            (FIRST_PAGES / "home.html").resolve()
        ]

    def test_hyphenated_references_match_an_underscored_name(
        self, configure, project_dir
    ):
        write(project_dir, "pages/hover.html", "<c-hover-gallery />\n")
        configure()
        catalog = ComponentCatalog()

        used = catalog.uses(catalog.get("hover_gallery"))

        assert [p.name for p in used] == ["hover.html"]

    def test_a_component_nobody_uses_has_no_paths(self, configure):
        configure()
        catalog = ComponentCatalog()

        assert catalog.uses(catalog.get("badge")) == []

    def test_templates_in_an_app_folder_count_as_well_as_the_project_folder(
        self, title
    ):
        used = ComponentCatalog().uses(title)

        assert "home.html" in [p.name for p in used]
        assert len({p.parent for p in used}) == 2

    def test_an_undecodable_template_is_skipped(self, configure, project_dir):
        broken = project_dir / "pages" / "broken.html"
        broken.parent.mkdir(parents=True)
        broken.write_bytes(b"\xff\xfe <c-badge /> \xff")
        write(project_dir, "pages/fine.html", "<c-badge />\n")
        configure()
        catalog = ComponentCatalog()

        used = catalog.uses(catalog.get("badge"))

        assert [p.name for p in used] == ["fine.html"]

    def test_paths_are_sorted(self, title):
        used = ComponentCatalog().uses(title)

        assert used == sorted(used)

    def test_every_folder_components_load_from_is_excluded(
        self, configure, project_dir
    ):
        write(project_dir, "components/badge.html")
        write(project_dir, "components/user.html", "<c-badge />\n")
        write(project_dir, "cotton/fallback_user.html", "<c-badge />\n")
        page = write(project_dir, "pages/page.html", "<c-badge />\n")
        configure(COTTON_DIR="components")
        catalog = ComponentCatalog()

        assert catalog.uses(catalog.get("badge")) == [page.resolve()]


class TestComponentCatalogWithoutTheFallback:
    """django-cotton before 2.9 has no list of candidate paths."""

    @pytest.fixture(autouse=True)
    def old_django_cotton(self, monkeypatch):
        monkeypatch.setattr("daisy_cotton.catalog.CottonComponentNode", None)

    def test_only_the_configured_folder_is_read(self, configure, project_dir):
        write(project_dir, "components/chosen.html")
        write(project_dir, "cotton/ignored.html")
        configure(COTTON_DIR="components")

        assert names(ComponentCatalog().components()) == ["chosen"]

    def test_the_index_file_is_the_second_choice(self, configure, project_dir):
        write(project_dir, "cotton/stat/index.html")
        configure()

        assert "stat" in names(ComponentCatalog().components())

    def test_uses_counts_cotton_templates_as_pages_when_they_are_not_components(
        self, configure, project_dir
    ):
        write(project_dir, "components/badge.html")
        page = write(project_dir, "cotton/page.html", "<c-badge />\n")
        configure(COTTON_DIR="components")
        catalog = ComponentCatalog()

        assert catalog.uses(catalog.get("badge")) == [page.resolve()]


class TestComponentCatalogAgreesWithDjango:
    """Each listed name resolves to the file django-cotton renders for its tag."""

    @staticmethod
    def rendered_path(name):
        for candidate in CottonComponentNode._candidate_template_paths(name, None):
            try:
                return Path(get_template(candidate).origin.name).resolve()
            except TemplateDoesNotExist:
                continue
        return None

    def assert_every_listed_name_agrees(self):
        components = ComponentCatalog().components()
        assert components
        for component in components:
            assert self.rendered_path(component.name) == component.path, component.name
        return {c.name: c for c in components}

    def test_every_listed_component_resolves_to_the_listed_path(self):
        self.assert_every_listed_name_agrees()

    def test_agrees_where_components_are_provided_more_than_once(
        self, configure, project_dir
    ):
        write(project_dir, "cotton/card.html")
        write(project_dir, "cotton/stat/index.html")
        write(project_dir, "cotton/stat.html")
        configure()

        listed = self.assert_every_listed_name_agrees()

        assert listed["card"].overrides
        assert listed["wide"].package == "catalog_second"

    def test_agrees_when_components_live_in_a_configured_folder(
        self, configure, project_dir
    ):
        override = write(project_dir, "components/card.html")
        write(project_dir, "components/only_here.html")
        configure(COTTON_DIR="components")

        listed = self.assert_every_listed_name_agrees()

        assert listed["card"].path == override.resolve()
        assert listed["card"].overrides == ("catalog_first", "catalog_second")
        assert listed["badge"].package == "catalog_first"
        assert listed["wide"].package == "catalog_second"
        assert "only_here" in listed

    def test_agrees_when_snake_casing_is_off(self, configure):
        configure(COTTON_SNAKE_CASED_NAMES=False)

        listed = self.assert_every_listed_name_agrees()

        assert "hover_gallery" in listed

    def test_the_components_are_the_ones_the_gallery_finds(self):
        config = CatalogConfig(cotton_dir=PACKAGE_COTTON)

        gallery = {component.tag_path for component in scan(config)}
        listed = {
            c.name
            for c in ComponentCatalog().components()
            if c.package == "daisy_cotton"
        }

        assert gallery
        assert listed == gallery
