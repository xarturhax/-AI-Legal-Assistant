import pytest
from app.ostis.memory import readable_definition


@pytest.mark.parametrize(
    "reference",
    [
        "file://text/article.html",
        "/tmp/builder/part 1.html",
        r"C:\kb\article.html",
        r"\\server\kb\article.html",
        "./text/article.html",
        "text/article.html",
        "article.html",
    ],
)
def test_file_reference_is_not_presented_as_normative_text(reference):
    assert readable_definition([(101, reference)]) == ("", "unavailable_file_reference")
    text = "Арендное жильё — жилые помещения государственного жилищного фонда."
    assert readable_definition([(101, reference), (102, text)]) == (text, "available")


def test_empty_definition_has_distinct_status():
    assert readable_definition([(101, "")]) == ("", "unavailable")
