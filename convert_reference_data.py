import json
import csv
import os

BASE = os.path.dirname(__file__)


def load_json(filename):
    with open(os.path.join(BASE, filename), "r", encoding="utf-8") as f:
        return json.load(f)


def build_included_map(data):
    m = {}
    for item in data.get("included", []):
        m[(item["type"], str(item["id"]))] = item
    return m


def write_csv(filename, rows, fieldnames):
    path = os.path.join(BASE, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {filename}: {len(rows)} rows")


def convert_products():
    data = load_json("fudo_products.json")
    inc = build_included_map(data)
    rows = []
    for p in data["data"]:
        a = p["attributes"]
        cat_ref = p.get("relationships", {}).get("productCategory", {}).get("data")
        cat_obj = inc.get((cat_ref["type"], str(cat_ref["id"]))) if cat_ref else None
        cat_name = cat_obj["attributes"]["name"] if cat_obj else ""

        rows.append({
            "product_id": p["id"],
            "name": a.get("name", ""),
            "price": a.get("price", ""),
            "cost": a.get("cost", ""),
            "active": a.get("active", ""),
            "category": cat_name,
            "stock": a.get("stock", ""),
            "stock_control": a.get("stockControl", ""),
            "sell_alone": a.get("sellAlone", ""),
            "favourite": a.get("favourite", ""),
            "code": a.get("code", ""),
            "description": a.get("description", ""),
            "preparation_time": a.get("preparationTime", ""),
            "image_url": a.get("imageUrl", ""),
            "enable_online_menu": a.get("enableOnlineMenu", ""),
            "enable_qr_menu": a.get("enableQrMenu", ""),
        })
    write_csv("fudo_products.csv", rows, list(rows[0].keys()) if rows else [])


def convert_categories():
    data = load_json("fudo_categories.json")
    rows = []
    for c in data["data"]:
        a = c["attributes"]
        rows.append({
            "category_id": c["id"],
            "name": a.get("name", ""),
            "active": a.get("active", ""),
        })
    write_csv("fudo_categories.csv", rows, list(rows[0].keys()) if rows else [])


def convert_users():
    data = load_json("fudo_users.json")
    inc = build_included_map(data)
    rows = []
    for u in data["data"]:
        a = u["attributes"]
        role_ref = u.get("relationships", {}).get("role", {}).get("data")
        role_obj = inc.get((role_ref["type"], str(role_ref["id"]))) if role_ref else None
        role_name = role_obj["attributes"]["name"] if role_obj else ""

        rows.append({
            "user_id": u["id"],
            "name": a.get("name", ""),
            "email": a.get("email", ""),
            "active": a.get("active", ""),
            "admin": a.get("admin", ""),
            "role": role_name,
            "promotional_code": a.get("promotionalCode", ""),
        })
    write_csv("fudo_users.csv", rows, list(rows[0].keys()) if rows else [])


def convert_payment_methods():
    data = load_json("fudo_payment_methods.json")
    rows = []
    for pm in data["data"]:
        a = pm["attributes"]
        rows.append({
            "payment_method_id": pm["id"],
            "name": a.get("name", ""),
            "code": a.get("code", ""),
            "active": a.get("active", ""),
        })
    write_csv("fudo_payment_methods.csv", rows, list(rows[0].keys()) if rows else [])


def convert_customers():
    data = load_json("fudo_customers.json")
    rows = []
    for c in data["data"]:
        a = c["attributes"]
        rows.append({
            "customer_id": c["id"],
            "name": a.get("name", ""),
            "email": a.get("email", ""),
            "phone": a.get("phone", ""),
            "address": a.get("address", ""),
            "sales_count": a.get("salesCount", ""),
            "historical_sales_count": a.get("historicalSalesCount", ""),
        })
    write_csv("fudo_customers.csv", rows, list(rows[0].keys()) if rows else [])


def convert_expenses():
    data = load_json("fudo_expenses.json")
    inc = build_included_map(data)
    rows = []
    for e in data["data"]:
        a = e["attributes"]
        cat_ref = e.get("relationships", {}).get("expenseCategory", {}).get("data")
        cat_obj = inc.get((cat_ref["type"], str(cat_ref["id"]))) if cat_ref else None
        cat_name = cat_obj["attributes"]["name"] if cat_obj else ""

        # Payments
        pay_refs = e.get("relationships", {}).get("payments", {}).get("data", [])
        pay_methods = []
        pay_amounts = []
        for pr in pay_refs:
            p_obj = inc.get((pr["type"], str(pr["id"])))
            if p_obj:
                pm_ref = p_obj.get("relationships", {}).get("paymentMethod", {}).get("data")
                pm_obj = inc.get((pm_ref["type"], str(pm_ref["id"]))) if pm_ref else None
                pm_name = pm_obj["attributes"]["name"] if pm_obj else ""
                pay_methods.append(pm_name)
                pay_amounts.append(str(p_obj["attributes"].get("amount", 0)))

        rows.append({
            "expense_id": e["id"],
            "amount": a.get("amount", ""),
            "description": a.get("description", ""),
            "date": a.get("date", ""),
            "created_at": a.get("createdAt", ""),
            "status": a.get("status", ""),
            "receipt_number": a.get("receiptNumber", ""),
            "payment_date": a.get("paymentDate", ""),
            "due_date": a.get("dueDate", ""),
            "category": cat_name,
            "payment_methods": "|".join(pay_methods),
            "payment_amounts": "|".join(pay_amounts),
        })
    write_csv("fudo_expenses.csv", rows, list(rows[0].keys()) if rows else [])


def main():
    print("Converting reference data to CSV...")
    convert_products()
    convert_categories()
    convert_users()
    convert_payment_methods()
    convert_customers()
    convert_expenses()
    print("Done!")


if __name__ == "__main__":
    main()
