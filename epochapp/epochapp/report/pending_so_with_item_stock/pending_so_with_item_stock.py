# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import flt, getdate

def execute(filters=None):
        if not filters: filters = {}

        validate_filters(filters)

        columns = get_columns()
       
        item_map = get_item_details(filters)
        iwb_map = get_item_warehouse_map(filters)

        data = []
        summ_data = [] 
        order_prev = "" 
        order_work = "" 
        order_count = 0 
        tot_bal_qty = 0 
	tot_si_qty = 0
	tot_del_qty = 0
	tot_pend_qty = 0

        for (company, sales_order, item, warehouse) in sorted(iwb_map):
                qty_dict = iwb_map[(company, sales_order, item, warehouse)]
                data.append([
                        sales_order, item, item_map[item]["item_group"],
			item_map[item]["description"], item_map[item]["stock_uom"],                    
                        item_map[item]["item_name"], 
			qty_dict.si_qty, qty_dict.del_qty, qty_dict.pend_qty,
			warehouse,
                        qty_dict.bal_qty,                                               
                        company
                    ])
	for rows in data: 
       		if order_count == 0: 
       			order_prev = rows[0] 
			tot_si_qty = tot_si_qty + rows[6]
                        tot_del_qty = tot_del_qty + rows[7] 
			tot_pend_qty = tot_pend_qty + rows[8] 
			tot_bal_qty = tot_bal_qty + rows[10]
                        summ_data.append([order_prev, rows[1], rows[2],
			 	rows[3], rows[4], rows[5], rows[6], 
				rows[7], rows[8], rows[9],
				rows[10], rows[11]
 				]) 
                else: 
			order_work = rows[0] 
			if order_prev == order_work: 
				tot_si_qty = tot_si_qty + rows[6]
                        	tot_del_qty = tot_del_qty + rows[7] 
				tot_pend_qty = tot_pend_qty + rows[8] 
				tot_bal_qty = tot_bal_qty + rows[10]
        	                summ_data.append([order_prev, rows[1], rows[2],
			 	rows[3], rows[4], rows[5], rows[6], 
				rows[7], rows[8], rows[9],
				rows[10], rows[11]
 				]) 
			else: 
				summ_data.append([order_prev, " ", 
			 	" ", " ", " ", " ", tot_si_qty, tot_del_qty,
				tot_pend_qty, " ", 
				tot_bal_qty, " "
 				])				 

				summ_data.append([order_work, rows[1], rows[2],
			 	rows[3], rows[4], rows[5], rows[6], 
				rows[7], rows[8], rows[9],
				rows[10], rows[11]
 				]) 
                                
				tot_bal_qty = 0 
				tot_si_qty = 0
				tot_del_qty = 0
				tot_pend_qty = 0
                                tot_si_qty = tot_si_qty + rows[6]
                        	tot_del_qty = tot_del_qty + rows[7] 
				tot_pend_qty = tot_pend_qty + rows[8] 
				tot_bal_qty = tot_bal_qty + rows[10]
				order_prev = order_work 
                                
		order_count = order_count + 1 
	summ_data.append([order_prev, " ", 
			 	" ", " ", " ", " ", tot_si_qty, tot_del_qty,
				tot_pend_qty, " ", 
				tot_bal_qty, " "
 				])		 
		 
		 
						 
	return columns, summ_data 


def get_columns():
        """return columns"""
        columns = [
		_("Sales Order Number")+"::150",
                _("Item")+":Link/Item:100",
		_("Item Group")+"::100",
	        _("Description")+"::140",
       	        _("Stock UOM")+":Link/UOM:90",       
                _("Item Name")+"::150",
		_("Sales Order Qty")+":Float:100",
		_("Delivered Qty")+":Float:100",
         	_("Pending Qty")+":Float:100",   
                _("Warehouse")+":Link/Warehouse:100",            
		_("Balance Qty")+":Float:100",
                _("Company")+":Link/Company:100"
                
         ]

        return columns

def get_conditions(filters):
        conditions = ""
        if not filters.get("from_date"):
                frappe.throw(_("'From Date' is required"))

        if filters.get("to_date"):
                conditions += " and posting_date <= '%s'" % frappe.db.escape(filters["to_date"])
        else:
                frappe.throw(_("'To Date' is required"))

        if filters.get("item_code"):
                conditions += " and si.item_code = '%s'" % frappe.db.escape(filters.get("item_code"), percent=False)
     
        if filters.get("name"):
                conditions += " and si.parent = '%s'" % frappe.db.escape(filters.get("name"), percent=False)

        if filters.get("warehouse"):
                conditions += " and sl.warehouse = '%s'" % frappe.db.escape(filters.get("warehouse"), percent=False)
        return conditions

def get_stock_ledger_entries(filters):
        conditions = get_conditions(filters)
	
        return frappe.db.sql("""select si.parent as sales_order, si.item_code, sl.warehouse, posting_date, si.qty as si_qty, si.delivered_qty as del_qty, sl.actual_qty, sl.valuation_rate, sl.company, voucher_type, qty_after_transaction, stock_value_difference
                from `tabStock Ledger Entry` sl, `tabSales Order Item` si, `tabSales Order` so
                where sl.docstatus < 2 and sl.item_code = si.item_code and so.status != "Cancelled" and so.name = si.parent %s order by si.parent, si.item_code, sl.warehouse, sl.name""" %
                conditions, as_dict=1)

def get_item_warehouse_map(filters):
        iwb_map = {}
        from_date = getdate(filters["from_date"])
        to_date = getdate(filters["to_date"])
	
        sle = get_stock_ledger_entries(filters)
	
        for d in sle:
                key = (d.company, d.sales_order, d.item_code, d.warehouse)
                if key not in iwb_map:
                        iwb_map[key] = frappe._dict({
                                "opening_qty": 0.0, "opening_val": 0.0,
                                "in_qty": 0.0, "in_val": 0.0,
                                "out_qty": 0.0, "out_val": 0.0,
                                "bal_qty": 0.0, "bal_val": 0.0,
                                "si_qty": 0.0, "del_qty": 0.0,
				"pend_qty": 0.0,
                                "val_rate": 0.0, "uom": None
                        })

                qty_dict = iwb_map[(d.company, d.sales_order, d.item_code, d.warehouse)]

                if d.voucher_type == "Stock Reconciliation":
                        qty_diff = flt(d.qty_after_transaction) - qty_dict.bal_qty
                else:
                        qty_diff = flt(d.actual_qty)

                value_diff = flt(d.stock_value_difference)
                qty_dict.si_qty = d.si_qty
                qty_dict.del_qty = d.del_qty
                
                if qty_dict.si_qty > qty_dict.del_qty:
                	qty_dict.pend_qty = qty_dict.si_qty - qty_dict.del_qty

                if d.posting_date < from_date:
                        qty_dict.opening_qty += qty_diff
                        qty_dict.opening_val += value_diff

                elif d.posting_date >= from_date and d.posting_date <= to_date:
                        if qty_diff > 0:
                                qty_dict.in_qty += qty_diff
                                qty_dict.in_val += value_diff
                        else:
                                qty_dict.out_qty += abs(qty_diff)
                                qty_dict.out_val += abs(value_diff)

                qty_dict.val_rate = d.valuation_rate
                qty_dict.bal_qty += qty_diff
                qty_dict.bal_val += value_diff

        return iwb_map

def get_item_details(filters):
        condition = ''
        value = ()
        if filters.get("item_code"):
                condition = "where item_code=%s"
                value = (filters["item_code"],)
	
        items = frappe.db.sql("""select item_group, item_name, stock_uom, name, brand, description
                from tabItem {condition}""".format(condition=condition), value, as_dict=1)

        return dict((d.name, d) for d in items)

def validate_filters(filters):
        if not (filters.get("item_code") or filters.get("warehouse")):
                sle_count = flt(frappe.db.sql("""select count(name) from `tabStock Ledger Entry`""")[0][0])
                if sle_count > 500000:
                        frappe.throw(_("Please set filter based on Item or Warehouse"))



