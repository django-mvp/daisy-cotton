"""Tests for the cotton_components management command."""

import json
from io import StringIO

from django.core.management import call_command

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
