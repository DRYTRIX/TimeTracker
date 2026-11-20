"""The row added with "Add Item" on the invoice edit page must not be a grid itself.

Its two children (the field grid and the per-line tax/discount strip) are siblings. When the outer row
carried the 12-column grid classes, each child took one column and the new row collapsed into a strip.
"""

import re

import pytest

pytestmark = [pytest.mark.integration]


def test_added_item_row_is_not_a_grid(app, authenticated_client, invoice):
    html = authenticated_client.get(f"/invoices/{invoice.id}/edit").get_data(as_text=True)
    outer = re.search(r"row\.className = '([^']*invoice-item-row[^']*)'", html).group(1)
    assert "grid" not in outer.split()
    assert "md:grid-cols-12" not in outer.split()
