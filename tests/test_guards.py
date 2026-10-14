from flask import Flask

from crb.guards import login_required, role_required


def make_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test"

    @app.route("/private")
    @login_required
    def private():
        return "private page"

    @app.route("/admin-only")
    @role_required("admin")
    def admin_only():
        return "admin page"

    @app.route("/staff")
    @role_required("admin", "auditor")
    def staff():
        return "staff page"

    return app


def sign_in(client, role):
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["role"] = role


def test_anonymous_visitor_is_sent_to_login():
    response = make_app().test_client().get("/private")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_signed_in_user_can_open_private_page():
    client = make_app().test_client()
    sign_in(client, "employee")
    assert client.get("/private").status_code == 200


def test_anonymous_visitor_is_sent_to_login_for_role_pages():
    response = make_app().test_client().get("/admin-only")
    assert response.status_code == 302


def test_wrong_role_gets_403():
    client = make_app().test_client()
    sign_in(client, "employee")
    assert client.get("/admin-only").status_code == 403


def test_right_role_gets_through():
    client = make_app().test_client()
    sign_in(client, "admin")
    assert client.get("/admin-only").status_code == 200


def test_page_can_allow_two_roles():
    client = make_app().test_client()
    sign_in(client, "auditor")
    assert client.get("/staff").status_code == 200
    sign_in(client, "employee")
    assert client.get("/staff").status_code == 403