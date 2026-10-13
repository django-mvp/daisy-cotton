"""An inline component adds no whitespace of its own to the text around it.

A caller who writes ``(<c-badge text="new" />)`` gets the badge directly
between the brackets. Whether a space separates a component from its
neighbours is the caller's choice, made by typing one or not.
"""

import pytest

INLINE_COMPONENTS = [
    '<c-link href="/" text="the guide" />',
    '<c-link href="/">the guide</c-link>',
    '<c-badge text="new" />',
    "<c-badge>new</c-badge>",
    '<c-kbd text="K" />',
    "<c-kbd>K</c-kbd>",
    "<c-status />",
    '<c-status label="Online" />',
    '<c-icon name="bi bi-house" />',
    '<c-button text="Save" />',
    '<c-button href="/" icon="bi bi-house" text="Save" />',
    "<c-button>Save</c-button>",
]


class TestInlineComponentWhitespace:
    @pytest.mark.parametrize("source", INLINE_COMPONENTS)
    def test_component_touches_the_characters_around_it(
        self, cotton_render_string, source
    ):
        html = cotton_render_string(f"({source}).")

        assert html.startswith("(<")
        assert html.endswith(">).")
