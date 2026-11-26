"""Tests for the cotton_components management command."""

import json
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from daisy_cotton.management.commands.cotton_components import Command


def run(*args):
    # The command instance is passed because the fixtures replace INSTALLED_APPS,
    # which would hide the command from Django's name lookup.
    out = StringIO()
    call_command(Command(), *args, stdout=out)
    return out.getvalue()


def listed_lines(output):
    """The component lines of a list: everything except the closing count line."""
    return [line for line in output.splitlines() if line.startswith("<c-")]


class TestCottonComponentsList:
    def test_every_component_appears_once_in_name_order_with_its_package(
        self, configured_project
    ):
        output = run()

        rows = [line.split()[:2] for line in listed_lines(output)]

        assert rows == [
            ["<c-badge>", "catalog_first"],
            ["<c-card>", "catalog_first"],
            ["<c-card.title>", "catalog_first"],
            ["<c-hover_gallery>", "catalog_first"],
            ["<c-mvp.card>", "catalog_second"],
            ["<c-wide>", "catalog_second"],
        ]

    def test_the_count_equals_the_number_listed(self, configured_project):
        output = run()

        count_line = output.strip().splitlines()[-1]

        assert int(count_line.split()[0]) == len(listed_lines(output))

    def test_a_component_with_a_description_shows_its_first_sentence(
        self, configured_project
    ):
        output = run()

        card_line = next(
            line for line in listed_lines(output) if line.startswith("<c-card> ")
        )

        assert "Card from the first app." in card_line
        assert "second sentence" not in card_line

    def test_overrides_are_noted_on_the_overriding_line_only(self, configured_project):
        (configured_project / "cotton").mkdir()
        (configured_project / "cotton" / "card.html").write_text("<div></div>\n")

        lines = {line.split()[0]: line for line in listed_lines(run())}

        assert lines["<c-card>"].split()[1] == "project"
        assert "catalog_first" in lines["<c-card>"]
        assert "catalog_second" in lines["<c-card>"]
        assert lines["<c-card.title>"].count("catalog_first") == 1

    def test_a_term_keeps_only_matching_components(self, configured_project):
        output = run("card")

        assert [line.split()[0] for line in listed_lines(output)] == [
            "<c-card>",
            "<c-card.title>",
            "<c-mvp.card>",
        ]

    def test_text_and_package_filters_apply(self, configured_project):
        output = run("--text", "author", "--package", "catalog_second")

        assert [line.split()[0] for line in listed_lines(output)] == ["<c-mvp.card>"]

    def test_a_term_that_matches_nothing_succeeds_with_no_components(
        self, configured_project
    ):
        output = run("zzzzzz")

        assert listed_lines(output) == []


class TestCottonComponentsJson:
    def test_prints_one_object_per_component_with_the_documented_fields(
        self, configured_project
    ):
        data = json.loads(run("--json"))

        card = next(item for item in data if item["name"] == "card")

        assert len(data) == 6
        assert set(card) == {"name", "tag", "package", "path", "summary", "overrides"}
        assert card["tag"] == "<c-card>"
        assert card["package"] == "catalog_first"
        assert card["path"].endswith("catalog_first/templates/cotton/card.html")
        assert card["summary"] == "Card from the first app."
        assert card["overrides"] == ["catalog_second"]

    def test_a_component_without_a_description_has_a_null_summary(
        self, configured_project
    ):
        data = json.loads(run("--json", "badge"))

        assert [(item["name"], item["summary"]) for item in data] == [("badge", None)]

    def test_filters_apply_to_the_json_list(self, configured_project):
        data = json.loads(run("--json", "--package", "catalog_second"))

        assert [item["name"] for item in data] == ["mvp.card", "wide"]

    def test_no_match_prints_an_empty_array(self, configured_project):
        assert json.loads(run("--json", "zzzzzz")) == []


class TestCottonComponentsRealProject:
    def test_lists_this_packages_own_components(self):
        out = StringIO()
        call_command("cotton_components", "--package", "daisy_cotton", stdout=out)
        output = out.getvalue()

        assert "<c-card>" in [line.split()[0] for line in listed_lines(output)]


RICH = """\
{# @description Rich component. It has a second sentence. #}
{# @prop size:select['sm', 'md'] | default:"md" | description:"Size." #}
{# @prop label:text | required | description:"Label." #}
{# @prop old:text | deprecated:"Use size" | hidden #}
{# @slot <b>Body</b> — Main content. #}
{# @slot:title <i>Heading</i> — Heading content. #}
<div {{ attrs }}>TEMPLATE-BODY-MARKER {{ slot }}</div>
"""


@pytest.fixture
def rich(configured_project):
    """A project component with every kind of annotation, used by two pages."""
    path = configured_project / "cotton" / "rich.html"
    path.parent.mkdir()
    path.write_text(RICH, encoding="utf-8")
    pages = configured_project / "pages"
    pages.mkdir()
    (pages / "one.html").write_text("<c-rich />\n", encoding="utf-8")
    (pages / "two.html").write_text("{% cotton rich %}{% endcotton %}\n")
    return path


def show_json(name):
    return json.loads(run("--show", name, "--json"))


class TestCottonComponentsShowJson:
    def test_carries_the_location_and_the_description(self, rich):
        data = show_json("rich")

        assert data["name"] == "rich"
        assert data["tag"] == "<c-rich>"
        assert data["package"] == "project"
        assert data["path"] == str(rich.resolve())
        assert data["overrides"] == []
        assert data["description"].startswith("Rich component.")
        assert data["summary"] == "Rich component."

    def test_every_prop_carries_every_field(self, rich):
        props = {p["name"]: p for p in show_json("rich")["props"]}

        assert set(props) == {"size", "label", "old"}
        assert props["size"]["type"] == "select"
        assert props["size"]["options"] == ["sm", "md"]
        assert props["size"]["default"] == "md"
        assert props["size"]["required"] is False
        assert props["label"]["required"] is True
        assert props["old"]["deprecated"] == "Use size"
        assert props["old"]["hidden"] is True
        assert {
            "type",
            "options",
            "default",
            "required",
            "deprecated",
            "hidden",
        } <= set(props["size"])

    def test_every_slot_carries_its_name_and_content(self, rich):
        slots = {s["name"]: s for s in show_json("rich")["slots"]}

        assert set(slots) == {None, "title"}
        assert slots[None]["content"] == "<b>Body</b>"
        assert slots["title"]["content"] == "<i>Heading</i>"

    def test_a_component_rendering_attrs_accepts_them(self, rich):
        assert show_json("rich")["accepts_attrs"] is True

    def test_a_component_not_rendering_attrs_does_not(self, configured_project):
        assert show_json("card")["accepts_attrs"] is False

    def test_counts_the_templates_that_use_it(self, rich):
        data = show_json("rich")

        assert data["uses"] == 2
        assert sorted(p.rsplit("/", 1)[1] for p in data["use_paths"]) == [
            "one.html",
            "two.html",
        ]

    def test_a_component_nobody_uses_has_zero_uses(self, configured_project):
        data = show_json("badge")

        assert data["uses"] == 0
        assert data["use_paths"] == []

    def test_a_component_without_annotations_has_no_description_props_or_slots(
        self, configured_project
    ):
        data = show_json("badge")

        assert data["description"] is None
        assert data["summary"] is None
        assert data["props"] == []
        assert data["slots"] == []

    def test_an_overridden_component_is_documented_from_the_winning_copy(
        self, configured_project
    ):
        data = show_json("card")

        assert data["package"] == "catalog_first"
        assert data["overrides"] == ["catalog_second"]
        assert (
            data["description"] == "Card from the first app. It has a second sentence."
        )

    def test_the_name_may_use_a_hyphen_for_an_underscore(self, configured_project):
        assert show_json("hover-gallery")["name"] == "hover_gallery"

    def test_show_ignores_the_list_filters(self, configured_project):
        data = json.loads(run("--show", "card", "--json", "--package", "nothing"))

        assert data["name"] == "card"


class TestCottonComponentsShowText:
    def test_prints_the_tag_file_and_package_first(self, rich):
        lines = run("--show", "rich").splitlines()

        assert lines[0] == "<c-rich>"
        assert lines[1].startswith("File: ")
        assert lines[1].endswith(str(rich.resolve()))
        assert lines[2].startswith("Package: project")

    def test_never_prints_the_template_body(self, rich):
        output = run("--show", "rich")

        assert "TEMPLATE-BODY-MARKER" not in output
        assert "{{ slot }}" not in output

    def test_lists_every_prop_and_slot_by_name(self, rich):
        output = run("--show", "rich")

        for expected in ("size", "sm", "md", "required", "old", "hidden", "title"):
            assert expected in output
        assert "deprecated: Use size" in output
        assert "<b>Body</b>" in output

    def test_says_whether_extra_attributes_are_passed(self, rich):
        accepted = run("--show", "rich").splitlines()[-1]
        refused = run("--show", "card").splitlines()[-1]

        assert accepted != refused

    def test_names_the_packages_it_overrides(self, configured_project):
        package_line = run("--show", "card").splitlines()[2]

        assert package_line.startswith("Package: catalog_first")
        assert "catalog_second" in package_line

    def test_an_unannotated_component_has_no_props_or_slots(self, configured_project):
        output = run("--show", "badge")

        assert "Props: none" in output
        assert "Slots: none" in output

    def test_says_how_many_templates_use_it(self, rich):
        assert "Used by 2 templates" in run("--show", "rich")

    def test_says_when_no_template_uses_it(self, configured_project):
        output = run("--show", "badge")

        assert "Used by" not in output
        assert "No template uses" in output


class TestCottonComponentsShowNotFound:
    def test_an_unknown_name_raises_a_command_error_naming_it(self, configured_project):
        with pytest.raises(CommandError) as caught:
            run("--show", "card.titel")

        assert "card.titel" in str(caught.value)

    def test_the_error_lists_the_closest_names(self, configured_project):
        with pytest.raises(CommandError) as caught:
            run("--show", "card.titel")

        assert "card.title" in str(caught.value)

    def test_a_name_unlike_any_component_lists_no_names(self, configured_project):
        with pytest.raises(CommandError) as caught:
            run("--show", "nothing")

        assert "Closest" not in str(caught.value)
