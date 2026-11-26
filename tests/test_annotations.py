"""Tests for the annotation parser copied from django-cotton-gallery."""

from dataclasses import asdict
from pathlib import Path

import pytest
from django_cotton_gallery.core.annotations import AnnotationParser as GalleryParser

from daisy_cotton.annotations import AnnotationParser

COTTON_DIR = (
    Path(__file__).resolve().parent.parent / "daisy_cotton" / "templates" / "cotton"
)
COMPONENT_FILES = sorted(COTTON_DIR.rglob("*.html"))


class TestAnnotationParser:
    @pytest.mark.parametrize(
        "path", COMPONENT_FILES, ids=lambda p: str(p.relative_to(COTTON_DIR))
    )
    def test_matches_the_gallery_parser_on_every_component(self, path):
        source = path.read_text(encoding="utf-8")

        ours = asdict(AnnotationParser().parse(source))
        theirs = asdict(GalleryParser().parse(source))

        assert ours == theirs

    def test_package_has_components_to_compare(self):
        assert COMPONENT_FILES

    def test_reads_required_deprecated_hidden_and_default_props(self):
        source = (
            "{# @prop lat:text | required #}\n"
            '{# @prop old-api:text | deprecated:"Use new-api" | hidden #}\n'
            "{# @prop size:select['sm', 'md'] | default:\"md\" #}\n"
        )

        lat, old_api, size = AnnotationParser().parse(source).props

        assert (lat.name, lat.required) == ("lat", True)
        assert (old_api.deprecated, old_api.hidden) == ("Use new-api", True)
        assert (size.options, size.default, size.has_default) == (
            ("sm", "md"),
            "md",
            True,
        )

    def test_malformed_annotations_leave_the_valid_parts(self):
        source = (
            "{# @description A card. #}\n"
            '{# @prop broken head | description:"x" #}\n'
            '{# @prop title:text | description:"Heading" | ??? #}\n'
            "{# @slot:footer — Footer area #}\n"
        )

        parsed = AnnotationParser().parse(source)

        assert parsed.description == "A card."
        assert [p.name for p in parsed.props] == ["title"]
        assert parsed.props[0].description == "Heading"
        assert [s.name for s in parsed.slots] == ["footer"]
