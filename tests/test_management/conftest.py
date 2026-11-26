"""Fixtures for the management command tests."""

import pytest

FIRST = "tests.fixtures.catalog_first"
SECOND = "tests.fixtures.catalog_second"


@pytest.fixture
def project_dir(tmp_path):
    """A project-level template folder, empty, that the engine searches first."""
    path = tmp_path / "project_templates"
    path.mkdir()
    return path


@pytest.fixture
def configured_project(settings, project_dir):
    """Point Django at the two fixture apps and the project folder, and return the folder."""
    settings.INSTALLED_APPS = [FIRST, SECOND]
    settings.TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [project_dir],
            "APP_DIRS": True,
        }
    ]
    return project_dir
