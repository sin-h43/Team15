BASE = {"date": "2030-01-15", "start": "10:00", "end": "11:00"}


def search(client, **extra):
    query = dict(BASE)
    query.update(extra)
    return client.get("/rooms/search", query_string=query)


def test_visitor_is_sent_to_login(client):
    response = client.get("/rooms/search")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_search_form_loads_without_results(client, login):
    login("employee1", "emp123")
    response = client.get("/rooms/search")
    assert response.status_code == 200
    assert b"Search rooms" in response.data
    assert b"No rooms are available" not in response.data


def test_search_lists_free_rooms(client, login):
    login("employee1", "emp123")
    response = search(client)
    assert response.status_code == 200
    for name in [b"Alpha", b"Beta", b"Gamma", b"Delta", b"Epsilon"]:
        assert name in response.data


def test_capacity_filter_in_the_page(client, login):
    login("employee1", "emp123")
    response = search(client, capacity="10")
    assert b"Gamma" in response.data
    assert b"Epsilon" in response.data
    assert b"Alpha" not in response.data


def test_equipment_filter_in_the_page(client, login):
    login("employee1", "emp123")
    response = search(client, equipment=["projector", "whiteboard"])
    assert b"Beta" in response.data
    assert b"Delta" not in response.data


def test_json_format_returns_room_list(client, login):
    login("employee1", "emp123")
    response = search(client, format="json", location="Pune")
    assert response.status_code == 200
    data = response.get_json()
    assert [room["name"] for room in data] == ["Delta", "Epsilon"]
    assert data[0]["equipment"] == ["projector"]


def test_end_before_start_gives_400(client, login):
    login("employee1", "emp123")
    response = search(client, start="12:00", end="11:00")
    assert response.status_code == 400
    assert b"Invalid time range" in response.data


def test_json_without_times_gives_400(client, login):
    login("employee1", "emp123")
    response = client.get("/rooms/search", query_string={"format": "json"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_bad_capacity_gives_400(client, login):
    login("employee1", "emp123")
    assert search(client, capacity="abc").status_code == 400


def test_unknown_equipment_gives_400(client, login):
    login("employee1", "emp123")
    assert search(client, equipment=["laser"]).status_code == 400


def test_sql_injection_text_is_harmless(client, login):
    login("employee1", "emp123")
    response = search(client, location="' OR 1=1 --")
    assert response.status_code == 200
    assert b"No rooms are available" in response.data


def test_script_text_in_input_is_escaped(client, login):
    login("employee1", "emp123")
    response = search(client, equipment=["<script>alert(1)</script>"])
    assert response.status_code == 400
    assert b"<script>alert(1)</script>" not in response.data
    assert b"&lt;script&gt;" in response.data
