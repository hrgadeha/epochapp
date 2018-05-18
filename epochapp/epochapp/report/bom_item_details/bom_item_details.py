# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint

def execute(filters=None):
#	if not filters: filters = {}
	columns = get_columns()
	summ_data = []

	data = get_bom_stock(filters)

	for rows in data:
	        item_map = get_item_details(rows[0])
        	summ_data.append([
                        rows[0], item_map[rows[0]]["detail"], rows[2], rows[1], item_map[rows[0]]["manufacturer_part_no"], rows[3], filters.get("warehouse"), rows[4]
                        
                    ])


	return columns, summ_data

def get_columns():
	"""return columns"""
	columns = [
		_("Item") + ":Link/Item:100",
		_("Item Detail") + "::200",
		_("Item Reference") + "::100",
		_("Description") + "::100",
		_("Manufacturer Part Number") + "::100",
		_("Required Qty") + ":Float:100",
		_("Warehouse") + "::100",
		_("Stock Qty") + ":Float:100",
	]

	return columns

def get_bom_stock(filters):
	conditions = ""
	bom = filters.get("bom")

	table = "`tabBOM Item`"
	qty_field = "qty"

	if filters.get("show_exploded_view"):
		table = "`tabBOM Explosion Item`"
		qty_field = "stock_qty"

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value("Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
		if warehouse_details:
			conditions += " and exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and ledger.warehouse = wh.name)" % (warehouse_details.lft,
				warehouse_details.rgt)
		else:
			conditions += " and ledger.warehouse = '%s'" % frappe.db.escape(filters.get("warehouse"))

	else:
		conditions += ""

	return frappe.db.sql("""
			SELECT
				bom_item.item_code,
				bom_item.description, bom_item.reference,
				bom_item.{qty_field},
				sum(ledger.actual_qty) as actual_qty,
				sum(FLOOR(ledger.actual_qty / bom_item.{qty_field}))as to_build
			FROM
				{table} AS bom_item
				LEFT JOIN `tabBin` AS ledger
				ON bom_item.item_code = ledger.item_code
				{conditions}
				
			WHERE
				bom_item.parent = '{bom}' and bom_item.parenttype='BOM'

			GROUP BY bom_item.item_code""".format(qty_field=qty_field, table=table, conditions=conditions, bom=bom))

def get_item_details(item_code):
        condition = ''
        value = ()

        items = frappe.db.sql("""select it.item_group, it.item_name, it.stock_uom, it.name, it.brand, it.description, it.manufacturer_part_no, it.detail
                from tabItem it where it.item_code = %s""", item_code, as_dict=1)

        return dict((d.name, d) for d in items)

