# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint
from frappe.utils import flt, getdate, datetime
from erpnext.stock.stock_balance import get_balance_qty_from_sle

def execute(filters=None):
	global filters_for_button
	global item_map 
	global whs_flag
	filters_for_button = filters
	if not filters: filters = {}

        validate_filters(filters)
	
        columns = get_columns()
	
        item_map = get_item_details(filters)
	
        iwb_map = get_item_warehouse_map(filters)
	

        data = []
        summ_data = [] 
        bom_prev = "" 
        bom_work = "" 
        bom_count = 0 
        tot_bal_qty = 0 
	reqd_qty = 0
        tot_bi_qty = 0
	tot_reqd_qty = 0
        
	for (bom, item, bi_item, whse) in sorted(iwb_map):
                qty_dict = iwb_map[(bom, item, bi_item, whse)]
		if bi_item != " ":
					
	                data.append([
	                        bom, item, item_map[bi_item]["description"],
	                        item_map[bi_item]["item_group"],
	                        item_map[bi_item]["item_name"], 
	                        item_map[bi_item]["stock_uom"], 
	                        qty_dict.bal_qty, qty_dict.bi_qty, whse,                                              
	                        qty_dict.project, qty_dict.bom_qty, bi_item, qty_dict.qty_to_make
	                    ])
		else:

			data.append([
	                        bom, bi_item, item_map[item]["description"],
	                        item_map[item]["item_group"],
	                        item_map[item]["item_name"], 
	                        item_map[item]["stock_uom"], 
	                        qty_dict.bal_qty, qty_dict.bi_qty, whse,                                              
	                        qty_dict.project, qty_dict.bom_qty, bi_item, qty_dict.qty_to_make
	                    ])

       		
	for rows in data: 

		if bom_count == 0: 

       			bom_prev = rows[0]
			
			reqd_qty = (rows[7] / rows[10]) * flt(rows[12])

	                tot_bal_qty = tot_bal_qty + rows[6] 
			tot_bi_qty = tot_bi_qty + rows[7]
			tot_reqd_qty = tot_reqd_qty + reqd_qty
                        summ_data.append([bom_prev, rows[1], rows[10], rows[2], 
		 	rows[3], rows[4], rows[5], rows[11], rows[7], reqd_qty, rows[6], rows[8] 
			
 			]) 
                else: 
			bom_work = rows[0] 

			if bom_prev == bom_work: 

				tot_bal_qty = tot_bal_qty + rows[6] 
				reqd_qty = (rows[7] / rows[10]) * flt(rows[12])
				tot_bi_qty = tot_bi_qty + rows[7]
				tot_reqd_qty = tot_reqd_qty + reqd_qty
        	                summ_data.append([bom_prev, rows[1], rows[10], rows[2], 
		 	rows[3], rows[4], rows[5], rows[11], rows[7], reqd_qty, rows[6], rows[8] 		 
 				]) 
			else: 

				summ_data.append([bom_prev, " ", " ", " ", " ", " ", " ", " ",
			 	tot_bi_qty, tot_reqd_qty,
				tot_bal_qty, " "
 				])				 

				summ_data.append([bom_work, rows[1], rows[10], rows[2], 
		 	rows[3], rows[4], rows[5], rows[11], rows[7], reqd_qty, rows[6], rows[8] 
 				]) 
        	                        
				tot_bal_qty = 0 
 
 				tot_bi_qty = 0
				tot_reqd_qty = 0
        	                tot_bal_qty = tot_bal_qty + rows[6] 
				reqd_qty = (rows[7] / rows[13]) * flt(rows[15])
				tot_bi_qty = tot_bi_qty + rows[7]
				tot_reqd_qty = tot_reqd_qty + reqd_qty
				bom_prev = bom_work 
                               
		bom_count = bom_count + 1 
	summ_data.append([bom_prev, " ", " ", " ", " ", " ", " ", " ",
			 	tot_bi_qty, tot_reqd_qty,
				tot_bal_qty, " "
 		])	 

						 
	return columns, summ_data 



def get_columns():
        """return columns"""
        columns = [
		_("BOM")+":Link/BOM:100",
                _("Item")+":Link/Item:100",
		_("BOM Qty")+"::100",
                _("Description")+"::140",
                _("Item Group")+"::100",
                _("Item Name")+"::150",           
                _("Stock UOM")+":Link/UOM:90",
		_("BOM Item")+":Link/Item:100",
		_("BoM Item Qty")+":Float:100",
		_("Required Qty")+":Float:100",
                _("Balance Qty")+":Float:100",
                _("Warehouse")+"::100",
                _("Purchase Order")+":Link/Purchase Order:100",
		_("Purchase Order Item")+"::100",
		_("Delivery Date")+"::100"

             
         ]

        return columns

def get_conditions(filters):
        conditions = ""
	
	if filters.get("company"):
                conditions += " and bo.company = '%s'" % frappe.db.escape(filters.get("company"), percent=False)

        if filters.get("item_code"):
                conditions += " and bi.item_code = '%s'" % frappe.db.escape(filters.get("item_code"), percent=False)
     
        if filters.get("bom"):
                conditions += " and bi.parent = '%s'" % frappe.db.escape(filters.get("bom"), percent=False)
		
	
#       if filters.get("warehouse"):
  #             conditions += " and warehouse = '%s'" % frappe.db.escape(filters.get("warehouse"), percent=False)
        return conditions


def get_sales_order_entries(filters):
	conditions = get_conditions(filters)

	if filters.get("include_exploded_items") == "Y":
	        
        	return frappe.db.sql("""select bo.name as bom_name, bo.company, bo.item as bo_item, bo.quantity as bo_qty, bo.project, bi.item_code as bi_item, bi.qty as bi_qty
                	from `tabBOM` bo, `tabBOM Explosion Item` bi where bo.name = bi.parent and bo.docstatus = "1" %s
                	order by bo.name, bi.item_code""" % conditions, as_dict=1)
	else:

        	return frappe.db.sql("""select bo.name as bom_name, bo.company, bo.item as bo_item, bo.quantity as bo_qty, bo.project, bi.item_code as bi_item, bi.qty as bi_qty
                	from `tabBOM` bo, `tabBOM Item` bi where bo.name = bi.parent and bo.docstatus = "1" %s
                	order by bo.name, bi.item_code""" % conditions, as_dict=1)


def get_item_warehouse_map(filters):
        iwb_map = {}
	global qty_to_make
       
        sle = get_sales_order_entries(filters)
	
	company = filters.get("company")
	total_stock = 0
	temp_whse = []
	
	whs_flag = 0
	qty_to_make = filters.get("qty_to_make")
	
	if filters.get("warehouse"):
		temp_whse = filters.get("warehouse")
		
		if temp_whse == 'All Warehouse':
			whse, whs_flag = get_warehouses(company)
		else:
			whse, whs_flag = get_whs_branch(temp_whse, filters)
						
	else:
		whse = get_warehouses(company)
	
	
        for d in sle:
		total_stock = get_total_stock(d.bi_item)
		if total_stock > 0:
			if whs_flag == 1:

				for w in whse:
					
					whse_stock = get_stock(d.bi_item, w)

					if whse_stock > 0:
		                		key = (d.bom_name, d.bo_item, d.bi_item, w)
					
	        	        		if key not in iwb_map:
        		                		iwb_map[key] = frappe._dict({
        		                        		"opening_qty": 0.0, "opening_val": 0.0,
        		                        		"in_qty": 0.0, "in_val": 0.0,
        		                        		"out_qty": 0.0, "out_val": 0.0,
								"bal_qty": 0.0, "bom_qty": 0.0, 
        		                        		"bi_qty": 0.0, "qty_to_make": 0.0,
        		                        		"val_rate": 0.0, "uom": None
        		                		})

			                	qty_dict = iwb_map[(d.bom_name, d.bo_item, d.bi_item, w)]
			
						qty_dict.bal_qty = whse_stock
		
        			        	qty_dict.bi_qty = d.bi_qty
						qty_dict.bom_qty = d.bo_qty
						qty_dict.qty_to_make = qty_to_make
						qty_dict.project = d.project

			else:

				key = (d.bom_name, d.bo_item, d.bi_item, whse)
				
        	        	if key not in iwb_map:
        	                	iwb_map[key] = frappe._dict({
        	                        	"opening_qty": 0.0, "opening_val": 0.0,
        	                        	"in_qty": 0.0, "in_val": 0.0,
        	                        	"out_qty": 0.0, "out_val": 0.0,
						"bal_qty": 0.0, "bom_qty": 0.0,
        	                        	"bi_qty": 0.0, "qty_to_make": 0.0,
        	                        	"val_rate": 0.0, "uom": None
        	                	})

		                qty_dict = iwb_map[(d.bom_name, d.bo_item, d.bi_item, whse)]
		
				qty_dict.bal_qty = get_stock(d.bi_item, whse)
		
        		        qty_dict.bi_qty = d.bi_qty
				qty_dict.bom_qty = d.bo_qty
				qty_dict.qty_to_make = qty_to_make
				qty_dict.project = d.project

				
			
		else:

			key = (d.bom_name, d.bo_item, d.bi_item, " ")
					
        	       	if key not in iwb_map:
        	               	iwb_map[key] = frappe._dict({
        	                       	"opening_qty": 0.0, "opening_val": 0.0,
        	                       	"in_qty": 0.0, "in_val": 0.0,
        	                       	"out_qty": 0.0, "out_val": 0.0,
        	                       	"bal_qty": 0.0, "bom_qty": 0.0,
        	                       	"bi_qty": 0.0, "qty_to_make": 0.0,
        	                       	"val_rate": 0.0, "uom": None
        	               	})
		        qty_dict = iwb_map[(d.bom_name, d.bo_item, d.bi_item, " ")]
	
			qty_dict.bal_qty = 0
		
       			qty_dict.bi_qty = d.bi_qty
			qty_dict.bom_qty = d.bo_qty
			qty_dict.qty_to_make = qty_to_make
			qty_dict.project = d.project
					
	
				
	return iwb_map

	      
def get_warehouses(company):
		whse = frappe.db.sql("""select name from `tabWarehouse` where company = %s""", company)
		whs_flag = 1
		return whse, whs_flag

def get_whs_branch(temp_whs, filters):
		whse = frappe.db.sql("""select name from `tabWarehouse` where parent_warehouse = %s""", temp_whs)
		if whse:
			whs_flag = 1
			return whse, whs_flag
		else:
			whs_flag = 0
			whse = filters.get("warehouse")
			return whse, whs_flag

def get_stock(bi_item, warehouse):

		
#	max_posting_date = frappe.db.sql("""select max(posting_date) from `tabStock Ledger Entry`
#		where item_code=%s and warehouse = %s""",
#		(bi_item, warehouse))[0][0]
#	max_posting_date = getdate(max_posting_date)
#	max_posting_date1 = datetime.datetime.strftime(max_posting_date, "%Y-%m-%d")
	
#	max_posting_time = frappe.db.sql("""select max(posting_time) from `tabStock Ledger Entry`
#		where item_code=%s and warehouse = %s and posting_date = %s""",
#		(bi_item, warehouse, max_posting_date))[0][0]
	
#	max_posting_time = gettime(max_posting_time)
#	max_posting_time1 = datetime.datetime.strftime(max_posting_time, "%H:%M:%S")

#	ssle = frappe.db.sql("""select voucher_no, voucher_type, actual_qty, qty_after_transaction
#		from `tabStock Ledger Entry` sle
#		where item_code=%s and warehouse = %s and posting_date = %s and posting_time = %s""",
#		(bi_item, warehouse, getdate(max_posting_date1), max_posting_time))

#	if ssle:

#		item_stock = ssle[0][3]
#	else:
#		item_stock = 0
	item_stock = get_balance_qty_from_sle(bi_item, warehouse)	
				
	return item_stock

def get_total_stock(item_code):
		
                item_stock = flt(frappe.db.sql("""select sum(actual_qty)
			from `tabStock Ledger Entry`
			where item_code=%s""",
			(item_code))[0][0])
		
		stock_recon = flt(frappe.db.sql("""select sum(qty_after_transaction)
			from `tabStock Ledger Entry`
			where item_code=%s and voucher_type = 'Stock Reconciliation'""",
			(item_code))[0][0])

		tot_stock = item_stock + stock_recon
		return tot_stock

def get_stock_val(item_code, warehouse):
		
                item_stock_val = flt(frappe.db.sql("""select sum(stock_value)
			from `tabStock Ledger Entry`
			where item_code=%s and warehouse = %s""",
			(item_code, warehouse))[0][0])

		stock_recon_val = flt(frappe.db.sql("""select sum(stock_value_difference)
			from `tabStock Ledger Entry`
			where item_code=%s and voucher_type = 'Stock Reconciliation'""",
			(item_code))[0][0])

		tot_stock_val = item_stock_val + stock_recon_val
		
       	        return tot_stock_val

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






@frappe.whitelist()
def make_stock_requisition(filters=None):
	
	innerJson = ""
	company = filters_for_button.get("company")
	newJson = {
	"company": company,
	"doctype": "Stock Requisition",
	"title": "Purchase",
	"material_request_type": "Purchase",

	"items": [
]
}
	sle = get_sales_order_entries(filters_for_button)

	no_requisition = 0
	for d in sle:
		
		bal_qty = 0
		if filters_for_button.get("warehouse"):
			whse = filters_for_button.get("warehouse")
			bal_qty = get_stock(d.bi_item, whse)
		
		req_qty=(bal_qty-(d.bi_qty * flt(qty_to_make)))
		
		if req_qty < 0:
			no_requisition += req_qty
			innerJson =	{

			"doctype": "Stock Requisition Item",
			"item_code": d.bi_item,
			"description": item_map[d.bi_item]["description"],
			"uom": item_map[d.bi_item]["stock_uom"],
			"qty": -req_qty,
			"schedule_date": "2017-05-31",



			"warehouse": filters_for_button.get("warehouse")
			  }
			newJson["items"].append(innerJson)


	if no_requisition == 0:
		frappe.msgprint("All Items are in Stock !! Stock Requisition is not required  ")
	else:
		doc = frappe.new_doc("Stock Requisition")
		doc.update(newJson)
		doc.save()


		return doc.name
