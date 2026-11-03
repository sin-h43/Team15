from html.parser import HTMLParser

from tests.helpers import make_booking, signed_in

SKIPPED_TYPES = ("hidden", "submit", "button")


class PageChecker(HTMLParser):
    """Collects simple accessibility problems (CRB-NF-005, a basic check, not a full audit)."""

    def __init__(self):
        super().__init__()
        self.open_labels = 0
        self.problems = []
        self.lang = None
        self.has_title = False
        self.has_h1 = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "html":
            self.lang = attributes.get("lang")
        elif tag == "title":
            self.has_title = True
        elif tag == "h1":
            self.has_h1 = True
        elif tag == "label":
            self.open_labels += 1
        elif tag in ("input", "select", "textarea"):
            if attributes.get("type") in SKIPPED_TYPES:
                return
            if self.open_labels == 0 and "aria-label" not in attributes:
                self.problems.append(tag + " " + str(attributes.get("name")) + " has no label")

    def handle_endtag(self, tag):
        if tag == "label":
            self.open_labels -= 1


def check(page):
    checker = PageChecker()
    checker.feed(page.data.decode("utf-8"))
    return checker


def test_every_form_field_has_a_label_on_every_main_page(app):
    booking_id = make_booking(app)
    admin = signed_in(app, "admin1", "admin123")
    urls = [
        "/rooms/search", "/rooms/1/book", "/recurring", "/reports/utilisation",
        "/admin/rooms", "/admin/rooms/new", "/admin/rooms/1/edit", "/admin/blocks",
        "/bookings/" + str(booking_id), "/bookings/" + str(booking_id) + "/attendees",
        "/bookings/" + str(booking_id) + "/reschedule", "/my-bookings", "/audit", "/outbox",
    ]
    for url in urls:
        page = admin.get(url)
        assert page.status_code == 200, url
        checker = check(page)
        assert checker.problems == [], (url, checker.problems)


def test_login_page_fields_have_labels(client):
    checker = check(client.get("/login"))
    assert checker.problems == []


def test_pages_have_a_language_a_title_and_a_heading(app):
    admin = signed_in(app, "admin1", "admin123")
    for url in ["/", "/rooms/search", "/recurring", "/reports/utilisation", "/admin/rooms"]:
        checker = check(admin.get(url))
        assert checker.lang == "en", url
        assert checker.has_title, url
        assert checker.has_h1, url


def test_tables_have_header_cells(app):
    make_booking(app)
    admin = signed_in(app, "admin1", "admin123")
    for url in ["/my-bookings", "/admin/rooms", "/audit"]:
        page = admin.get(url).data
        if b"<table" in page:
            assert b"<th>" in page, url