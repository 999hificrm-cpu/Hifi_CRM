"""Manual organization smoke test.

This file intentionally exposes no import-time side effects so pytest can
collect the repository safely. Run it directly only against a disposable
database configured through the normal application environment.
"""

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal
from app.main import app


def main() -> None:
    client = TestClient(app)
    db = SessionLocal()
    try:
        db.execute(text("DELETE FROM organizations WHERE slug = 'adani-industries-ltd'"))
        db.execute(text("DELETE FROM users WHERE email = 'admin@adani.com'"))
        db.commit()

        super_admin_login = client.post(
            "/api/v1/auth/login",
            json={"email": "superadmin@jarvis.local", "password": "JarvisAdmin@2026"},
        )
        super_admin_login.raise_for_status()
        token = super_admin_login.json()["access_token"]

        response = client.post(
            "/api/v1/organizations/",
            json={
                "name": "Adani Industries LTD.",
                "slug": "adani-industries-ltd",
                "admin_name": "Gautam Adani",
                "admin_email": "admin@adani.com",
                "admin_password": "AdaniAdmin@2026",
                "plan_code": "GROWTH",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()

        organization_login = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@adani.com", "password": "AdaniAdmin@2026"},
        )
        organization_login.raise_for_status()
        organization_headers = {"Authorization": f"Bearer {organization_login.json()['access_token']}"}
        leads_response = client.get("/api/v1/leads/", headers=organization_headers)
        print("LEADS RESPONSE:", leads_response.status_code, leads_response.text)
    finally:
        db.execute(text("DELETE FROM organizations WHERE slug = 'adani-industries-ltd'"))
        db.execute(text("DELETE FROM users WHERE email = 'admin@adani.com'"))
        db.commit()
        db.close()


if __name__ == "__main__":
    main()
