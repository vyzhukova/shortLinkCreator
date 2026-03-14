from datetime import datetime, timedelta
from datetime import datetime, timedelta

async def test_register(client):
    response = await client.post("/register", json={"username": "testuser", "password": "secret"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data

async def test_register_already_registered(client):
    await client.post("/register", json={"username": "testuser", "password": "secret"})
    response = await client.post("/register", json={"username": "testuser", "password": "secret"})
    assert response.status_code == 400

async def test_login(client):
    await client.post("/register", json={"username": "testuser", "password": "secret"})
    response = await client.post("/login", data={"username": "testuser", "password": "secret"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token

async def test_invalid_login(client):
    await client.post("/register", json={"username": "user", "password": "pass"})
    response = await client.post("/login", data={"username": "user", "password": "wrong"})
    assert response.status_code == 401

async def test_stats_nonexistent_link(client):
    response = await client.get("/links/nonexistent/stats")
    assert response.status_code == 404

async def test_get_current_user_invalid_token(client):
    headers = {"Authorization": "Bearer invalid"}
    response = await client.get("/links/by_project", headers=headers)
    assert response.status_code == 401

async def test_create_duplicate_alias(client):
    # Регистрируем и логинимся
    await client.post("/register", json={"username": "u", "password": "p"})
    login = await client.post("/login", data={"username": "u", "password": "p"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/links/shorten", json={"original_url": "https://a.com", "custom_alias": "dup"}, headers=headers)
    response = await client.post("/links/shorten", json={"original_url": "https://b.com", "custom_alias": "dup"}, headers=headers)
    assert response.status_code == 400
    assert "already in use" in response.text

async def test_redirect(client):
    # Регистрируем и логинимся
    await client.post("/register", json={"username": "u", "password": "p"})
    login = await client.post("/login", data={"username": "u", "password": "p"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Создаём ссылку
    resp = await client.post("/links/shorten", json={"original_url": "https://target.com", "custom_alias": "code"}, headers=headers)
    code = resp.status_code
    # Переходим
    response = await client.get(f"/links/code", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://target.com/"

async def test_stats(client):
    # Регистрируем и логинимся
    await client.post("/register", json={"username": "u", "password": "p"})
    login = await client.post("/login", data={"username": "u", "password": "p"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/links/shorten", json={"original_url": "https://stats.com", "custom_alias": "code"}, headers=headers)
    # Делаем несколько переходов
    await client.get(f"/links/code")
    await client.get(f"/links/code")
    stats = await client.get(f"/links/code/stats", headers=headers)
    assert stats.status_code == 200
    data = stats.json()
    assert data["access_count"] == 2
    assert data["last_accessed_at"] is not None

async def test_update_link_auth(client):
    # Регистрируем и логинимся
    await client.post("/register", json={"username": "u", "password": "p"})
    login = await client.post("/login", data={"username": "u", "password": "p"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/links/shorten", json={"original_url": "https://old.com", "custom_alias": "code"}, headers=headers)
    update = await client.put(f"/links/code", json={"original_url": "https://new.com"}, headers=headers)
    assert update.status_code == 200
    assert update.json()["original_url"] == "https://new.com/"
    # Проверяем, что редирект ведёт на новый URL
    redirect = await client.get(f"/links/code", follow_redirects=False)
    assert redirect.headers["location"] == "https://new.com/"

async def test_delete_link_auth(client):
    await client.post("/register", json={"username": "u", "password": "p"})
    login = await client.post("/login", data={"username": "u", "password": "p"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post("/links/shorten", json={"original_url": "https://del.com"}, headers=headers)
    code = create.json()["code"]
    delete = await client.delete(f"/links/{code}", headers=headers)
    assert delete.status_code == 204
    # Проверяем, что ссылка исчезла
    get = await client.get(f"/{code}")
    assert get.status_code == 404

async def test_search_by_original_url(client):
    url = "https://search.me/path"
    # Регистрируем и логинимся
    await client.post("/register", json={"username": "u", "password": "p"})
    login = await client.post("/login", data={"username": "u", "password": "p"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/links/shorten", json={"original_url": url}, headers=headers)
    response = await client.get("/links/search", params={"original_url": url}, headers=headers)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["original_url"] == url 

async def test_search_by_original_url_negative(client):
    url = "https://search.me/path"
    # Регистрируем и логинимся
    await client.post("/register", json={"username": "u", "password": "p"})
    login = await client.post("/login", data={"username": "u", "password": "p"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get("/links/search", params={"original_url": url}, headers=headers)
    assert response.status_code == 404

async def test_by_project_grouping(client):
    # Регистрация и логин
    await client.post("/register", json={"username": "p", "password": "p"})
    login = await client.post("/login", data={"username": "p", "password": "p"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    await client.post("/links/shorten", json={"original_url": "https://a.com", "project": "work"}, headers=headers)
    await client.post("/links/shorten", json={"original_url": "https://b.com", "project": "work"}, headers=headers)
    await client.post("/links/shorten", json={"original_url": "https://c.com"}, headers=headers)
    resp = await client.get("/links/by_project", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "work" in data
    assert len(data["work"]) == 2
    assert "default" in data
    assert len(data["default"]) == 1

async def test_expired_links(client):
    # Создаём ссылку с expires_at в прошлом
    past = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
    # Регистрируем и логинимся
    await client.post("/register", json={"username": "u", "password": "p"})
    login = await client.post("/login", data={"username": "u", "password": "p"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/links/shorten", json={"original_url": "https://expired.com", "expires_at": past}, headers=headers)
    # Должна быть ошибка валидации, поэтому ожидаем 422
    assert resp.status_code == 422

async def test_stats_nonexistent_link(client):
    response = await client.get("/links/nonexistent/stats")
    assert response.status_code == 404

async def test_redirect_expired_link(client, db_session):
    # Создаём ссылку с истекшим сроком напрямую через БД, ну чтоб не ждать пока она истечет
    from app.models import Link
    from datetime import datetime, timezone, timedelta
    expired_link = Link(
        original_url="https://expired.com",
        code="expired_code",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    db_session.add(expired_link)
    await db_session.commit()
    # Пытаемся перейти
    response = await client.get("/links/expired_code", follow_redirects=False)
    assert response.status_code == 410
