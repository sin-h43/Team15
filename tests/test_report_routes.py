from tests.helpers import make_booking, signed_in


def test_visitor_is_sent_to_login(client):
    assert client.get("/reports/utilisation").status_code == 302


def test_employee_and_auditor_get_403(app):
    assert signed_in(app, "employee1", "emp123").get("/reports/utilisation").status_code == 403
    assert signed_in(app, "auditor1", "aud123").get("/reports/utilisation").status_code == 403


def test_admin_sees_the_empty_form_first(app):
    page = signed_in(app, "admin1", "admin123").get("/reports/utilisation")
    assert page.status_code == 200
    assert b"Run report" in page.data
    assert b"Booked hours" not in page.data


def test_admin_runs_a_report(app):
    make_booking(app, start="2030-01-10 10:00", end="2030-01-10 12:00")
    page = signed_in(app, "admin1", "admin123").get(
        "/reports/utilisation", query_string={"start": "2030-01-01", "end": "2030-01-31"}
    )
    assert page.status_code == 200
    assert b"Booked hours" in page.data
    assert b"Alpha" in page.data
    assert b"2.0" in page.data


def test_bad_dates_show_an_error(app):
    page = signed_in(app, "admin1", "admin123").get(
        "/reports/utilisation", query_string={"start": "2030-02-01", "end": "2030-01-01"}
    )
    assert page.status_code == 400
    assert b"must not be before" in page.data


def test_menu_shows_the_report_link_to_admins_only(app):
    assert b"Utilisation report" in signed_in(app, "admin1", "admin123").get("/").data
    assert b"Utilisation report" not in signed_in(app, "employee1", "emp123").get("/").data