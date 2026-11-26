"""Tests for the component catalog."""

import pytest

from daisy_cotton.catalog import ComponentCatalog

FIRST = "tests.fixtures.catalog_first"
SECOND = "tests.fixtures.catalog_second"


@pytest.fixture
def project_dir(tmp_path):
    """A project-level template folder, empty, that the engine searches first."""
    path = tmp_path / "project_templates"
    path.mkdir()
    return path


@pytest.fixture
def configure(settings, project_dir):
    """Return a function that points Django at the fixture apps and the project folder."""

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

    def test_reads_only_the_configured_cotton_dir(self, configure, project_dir):
        write(project_dir, "components/chosen.html")
        write(project_dir, "cotton/ignored.html")
        configure(COTTON_DIR="components")

        assert names(ComponentCatalog().components()) == ["chosen"]

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

    def test_hyphen_and_underscore_differ_when_snake_casing_is_off(self, configure):
        configure(COTTON_SNAKE_CASED_NAMES=False)

        assert "hover_gallery" not in names(ComponentCatalog().search("hover-gallery"))

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
