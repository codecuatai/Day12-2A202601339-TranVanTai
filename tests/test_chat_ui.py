"""Kiểm tra các route và hợp đồng dữ liệu của giao diện chat."""


def test_chat_page_and_static_assets(client):
    page = client.get("/chat")
    css = client.get("/static/style.css")
    js = client.get("/static/app.js")

    assert page.status_code == 200
    assert "Day 12 Agent" in page.text
    assert css.status_code == 200
    assert js.status_code == 200
    assert "X-API-Key" in js.text


def test_root_redirects_to_chat(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/chat"


def test_history_requires_api_key(client_real_store):
    response = client_real_store.get("/api/history")

    assert response.status_code == 401


def test_history_returns_messages_for_authenticated_user(client_real_store, auth_headers):
    ask_response = client_real_store.post(
        "/ask",
        headers=auth_headers,
        json={"question": "Xin chao"},
    )
    history_response = client_real_store.get(
        "/api/history",
        headers=auth_headers,
    )

    assert ask_response.status_code == 200
    assert history_response.status_code == 200
    assert history_response.json()["user_id"] == "sv-test"
    assert len(history_response.json()["messages"]) == 2
