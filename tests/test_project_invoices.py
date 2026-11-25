"""The Invoices page of a project.

/projects/<id>/invoices lists the invoices of one project with the same table as the Invoices page.
"New Invoice" there opens the usual create form with that project already selected. Delete and bulk
actions started on that page return to it.
"""

import io
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app import db
from app.models import Invoice, Project, Settings

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _invoices_module_on(app):
    with app.app_context():
        settings = Settings.get_settings()
        disabled = list(settings.disabled_module_ids or [])
        if "invoices" in disabled:
            settings.disabled_module_ids = [m for m in disabled if m != "invoices"]
            db.session.commit()


def _make_invoice(project, created_by, number, status="draft"):
    invoice = Invoice(
        invoice_number=number,
        project_id=project.id,
        client_name=project.client_obj.name if project.client_obj else "Client",
        due_date=date.today() + timedelta(days=30),
        created_by=created_by,
        client_id=project.client_id,
    )
    invoice.status = status
    db.session.add(invoice)
    db.session.commit()
    return invoice


@pytest.fixture
def other_project(app, project):
    other = Project(
        name="Other Project",
        client_id=project.client_id,
        billable=True,
        hourly_rate=Decimal("50.00"),
    )
    other.status = "active"
    db.session.add(other)
    db.session.commit()
    return other


def _page(client, project):
    return client.get(f"/projects/{project.id}/invoices")


class TestProjectInvoicesPage:
    def test_lists_only_invoices_of_the_project(self, admin_authenticated_client, admin_user, project, other_project):
        _make_invoice(project, admin_user.id, "PI-ONE")
        _make_invoice(project, admin_user.id, "PI-TWO")
        _make_invoice(other_project, admin_user.id, "PI-OTHER")

        resp = _page(admin_authenticated_client, project)

        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "PI-ONE" in html and "PI-TWO" in html
        assert "PI-OTHER" not in html
        assert "2 invoices found" in html

    def test_non_admin_sees_only_own_invoices(self, authenticated_client, user, admin_user, project):
        _make_invoice(project, user.id, "PI-MINE")
        _make_invoice(project, admin_user.id, "PI-ADMINS")

        html = _page(authenticated_client, project).get_data(as_text=True)

        assert "PI-MINE" in html
        assert "PI-ADMINS" not in html

    def test_new_invoice_and_export_carry_the_project(self, admin_authenticated_client, admin_user, project):
        _make_invoice(project, admin_user.id, "PI-ONE")

        html = _page(admin_authenticated_client, project).get_data(as_text=True)

        assert f"/invoices/new?project_id={project.id}" in html
        assert f"/invoices/export/excel?project_id={project.id}" in html

    def test_empty_project_offers_to_create_the_first_invoice(self, admin_authenticated_client, project):
        html = _page(admin_authenticated_client, project).get_data(as_text=True)

        assert "This project has no invoices yet" in html
        assert f"/invoices/new?project_id={project.id}" in html

    def test_unknown_project_is_404(self, admin_authenticated_client):
        assert admin_authenticated_client.get("/projects/999999/invoices").status_code == 404

    def test_project_out_of_scope_is_403(self, authenticated_client, project, monkeypatch):
        import app.utils.scope_filter as scope_filter

        monkeypatch.setattr(scope_filter, "user_can_access_project", lambda user, project_id: False)

        assert _page(authenticated_client, project).status_code == 403

    def test_module_off_is_not_shown(self, app, admin_authenticated_client, project):
        settings = Settings.get_settings()
        settings.disabled_module_ids = list(settings.disabled_module_ids or []) + ["invoices"]
        db.session.commit()

        # The module_enabled decorator sends an admin away with a "module is disabled" notice
        assert _page(admin_authenticated_client, project).status_code in (302, 403)


class TestProjectPageLink:
    def test_project_page_links_to_its_invoices(self, admin_authenticated_client, project):
        html = admin_authenticated_client.get(f"/projects/{project.id}").get_data(as_text=True)

        assert f"/projects/{project.id}/invoices" in html

    def test_no_link_when_invoices_module_is_off(self, app, admin_authenticated_client, project):
        settings = Settings.get_settings()
        settings.disabled_module_ids = list(settings.disabled_module_ids or []) + ["invoices"]
        db.session.commit()

        html = admin_authenticated_client.get(f"/projects/{project.id}").get_data(as_text=True)

        assert f"/projects/{project.id}/invoices" not in html


class TestCreateFormPreselect:
    def test_project_from_query_is_selected(self, admin_authenticated_client, project, other_project):
        html = admin_authenticated_client.get(f"/invoices/new?project_id={project.id}").get_data(as_text=True)

        assert f'<option value="{project.client_id}" selected' in html
        assert f'name="project_ids" value="{project.id}" checked' in html
        assert f'id="project_id" value="{project.id}"' in html

    def test_without_query_nothing_is_selected(self, admin_authenticated_client, project):
        html = admin_authenticated_client.get("/invoices/new").get_data(as_text=True)

        assert f'<option value="{project.client_id}" selected' not in html
        assert 'name="project_ids"' not in html

    def test_project_not_in_the_list_leaves_form_empty(self, admin_authenticated_client, project):
        project.billable = False
        db.session.commit()

        resp = admin_authenticated_client.get(f"/invoices/new?project_id={project.id}")

        assert resp.status_code == 200
        assert f'name="project_ids" value="{project.id}"' not in resp.get_data(as_text=True)


class TestReturnToProjectPage:
    def test_delete_returns_to_the_page_it_came_from(self, admin_authenticated_client, admin_user, project):
        invoice = _make_invoice(project, admin_user.id, "PI-DEL")
        back = f"/projects/{project.id}/invoices"

        resp = admin_authenticated_client.post(f"/invoices/{invoice.id}/delete", data={"next": back})

        assert resp.status_code == 302
        assert resp.headers["Location"].endswith(back)
        assert db.session.get(Invoice, invoice.id) is None

    def test_bulk_status_returns_to_the_page_it_came_from(self, admin_authenticated_client, admin_user, project):
        invoice = _make_invoice(project, admin_user.id, "PI-BULK")
        back = f"/projects/{project.id}/invoices"

        resp = admin_authenticated_client.post(
            "/invoices/bulk-status", data={"invoice_ids[]": [invoice.id], "status": "sent", "next": back}
        )

        assert resp.status_code == 302
        assert resp.headers["Location"].endswith(back)

    def test_without_next_goes_to_invoices_list(self, admin_authenticated_client, admin_user, project):
        invoice = _make_invoice(project, admin_user.id, "PI-DEL2")

        resp = admin_authenticated_client.post(f"/invoices/{invoice.id}/delete")

        assert resp.headers["Location"].endswith("/invoices")

    def test_external_next_is_ignored(self, admin_authenticated_client, admin_user, project):
        invoice = _make_invoice(project, admin_user.id, "PI-DEL3")

        resp = admin_authenticated_client.post(f"/invoices/{invoice.id}/delete", data={"next": "https://evil.example/"})

        assert "evil.example" not in resp.headers["Location"]
        assert resp.headers["Location"].endswith("/invoices")


class TestExportByProject:
    def test_export_with_project_id_has_only_that_project(
        self, admin_authenticated_client, admin_user, project, other_project
    ):
        from openpyxl import load_workbook

        _make_invoice(project, admin_user.id, "PI-XL-ONE")
        _make_invoice(other_project, admin_user.id, "PI-XL-OTHER")

        resp = admin_authenticated_client.get(f"/invoices/export/excel?project_id={project.id}")

        assert resp.status_code == 200
        values = {c for row in load_workbook(io.BytesIO(resp.data)).active.iter_rows(values_only=True) for c in row}
        assert "PI-XL-ONE" in values
        assert "PI-XL-OTHER" not in values


class TestServiceFilter:
    def test_list_invoices_filters_by_project(self, app, admin_user, project, other_project):
        from app.services import InvoiceService

        _make_invoice(project, admin_user.id, "PI-S-ONE")
        _make_invoice(other_project, admin_user.id, "PI-S-OTHER")

        result = InvoiceService().list_invoices(project_id=project.id, user_id=admin_user.id, is_admin=True)

        assert [i.invoice_number for i in result["invoices"]] == ["PI-S-ONE"]
