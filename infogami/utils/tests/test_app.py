import urllib.parse

import pytest
import web

from infogami.utils import app


def test_parse_accept():
    # testing examples from http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html
    assert app.parse_accept("audio/*; q=0.2, audio/basic") == [
        {"media_type": "audio/basic"},
        {"media_type": "audio/*", "q": 0.2},
    ]

    assert app.parse_accept(
        "text/plain; q=0.5, text/html, text/x-dvi; q=0.8, text/x-c"
    ) == [
        {"media_type": "text/html"},
        {"media_type": "text/x-c"},
        {"media_type": "text/x-dvi", "q": 0.8},
        {"media_type": "text/plain", "q": 0.5},
    ]

    # try empty
    assert app.parse_accept("") == [{'media_type': ''}]
    assert app.parse_accept(" ") == [{'media_type': ''}]
    assert app.parse_accept(",") == [{'media_type': ''}, {'media_type': ''}]

    # try some bad ones
    assert app.parse_accept("hc/url;*/*") == [{"media_type": "hc/url"}]
    assert app.parse_accept("text/plain;q=bad") == [{"media_type": "text/plain"}]

    assert app.parse_accept(";q=1") == [{"media_type": "", "q": 1.0}]


@pytest.mark.parametrize(
    ("url", "location"),
    [
        ("/books/OL1M/foo/", "/books/OL1M/foo"),
        ("/books/OL1M/foo/?m=edit", "/books/OL1M/foo?m=edit"),
        ("/books/ia:foo/", "/books/ia:foo"),
        (
            "/books/OL4210801M/Das_schwerho%CC%88rige_Kind/",
            "/books/OL4210801M/Das_schwerho%CC%88rige_Kind",
        ),
    ],
)
def test_path_processor_quotes_redirect(url, location):
    class Page:
        def GET(self):
            return "ok"

    application = web.application(("/.*", Page), {})
    application.add_processor(app.path_processor)
    # WSGI servers pass PATH_INFO percent-decoded, as latin-1 characters.
    response = application.request(urllib.parse.unquote(url, encoding="latin-1"))
    assert response.status == "303 See Other"
    assert response.headers["Location"] == "http://0.0.0.0:8080" + location
