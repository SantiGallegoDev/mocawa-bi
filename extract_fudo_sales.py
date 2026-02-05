import requests
import json
import csv
import time
import sys
import os

API_BASE = "https://api.fu.do/v1alpha1"
AUTH_URL = "https://auth.fu.do/api"
API_KEY = "MTBAOTE1NzA="
API_SECRET = "HMpoQYdTKD1bYWvi7c2khNWdvJBEIKWR"

PAGE_SIZE = 500
INCLUDES = "items,items.product,items.product.productCategory,payments.paymentMethod,discounts,tips,waiter,customer,items.subitems,items.subitems.product"

OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "fudo_sales.csv")
OUTPUT_JSON = os.path.join(os.path.dirname(__file__), "fudo_sales_raw.json")


def authenticate():
    print("Authenticating...")
    r = requests.post(AUTH_URL, json={"apiKey": API_KEY, "apiSecret": API_SECRET},
                      headers={"Content-Type": "application/json", "Accept": "application/json"})
    r.raise_for_status()
    data = r.json()
    print(f"Token obtained, expires at {data.get('exp')}")
    return data["token"]


def build_included_map(included_list):
    """Build a lookup dict from the JSON:API 'included' array."""
    m = {}
    for item in included_list:
        key = (item["type"], str(item["id"]))
        m[key] = item
    return m


def get_related(included_map, rel_data):
    """Resolve a relationship data reference to the included object."""
    if not rel_data:
        return None
    return included_map.get((rel_data["type"], str(rel_data["id"])))


def fetch_all_sales(token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    all_rows = []
    all_raw = []
    page = 1
    total_sales = 0

    while True:
        url = f"{API_BASE}/sales?page%5Bsize%5D={PAGE_SIZE}&page%5Bnumber%5D={page}&sort=createdAt&include={INCLUDES}"
        try:
            r = requests.get(url, headers=headers, timeout=60)
        except requests.exceptions.Timeout:
            print(f"  Timeout on page {page}, retrying in 5s...")
            time.sleep(5)
            continue

        if r.status_code == 401:
            print("  Token expired, re-authenticating...")
            token = authenticate()
            headers["Authorization"] = f"Bearer {token}"
            continue

        if r.status_code != 200:
            print(f"  Error {r.status_code} on page {page}: {r.text[:200]}")
            time.sleep(2)
            continue

        data = r.json()
        sales = data.get("data", [])
        included = data.get("included", [])

        if not sales:
            break

        all_raw.append(data)
        inc_map = build_included_map(included)

        for sale in sales:
            sale_id = sale["id"]
            attrs = sale["attributes"]
            rels = sale["relationships"]

            # Waiter
            waiter_ref = rels.get("waiter", {}).get("data")
            waiter_obj = get_related(inc_map, waiter_ref)
            waiter_name = waiter_obj["attributes"]["name"] if waiter_obj else ""

            # Customer
            customer_ref = rels.get("customer", {}).get("data")
            customer_obj = get_related(inc_map, customer_ref)
            customer_name_rel = customer_obj["attributes"].get("name", "") if customer_obj else ""
            customer_name = attrs.get("customerName") or customer_name_rel or ""
            customer_phone = ""
            customer_email = ""
            if customer_obj:
                customer_phone = customer_obj["attributes"].get("phone", "") or ""
                customer_email = customer_obj["attributes"].get("email", "") or ""
            anon = attrs.get("anonymousCustomer")
            if anon and not customer_name:
                customer_name = anon.get("name", "")
                customer_phone = anon.get("phone", "") or customer_phone

            # Discounts
            discount_refs = rels.get("discounts", {}).get("data", [])
            discounts_total = 0.0
            for dr in discount_refs:
                d_obj = get_related(inc_map, dr)
                if d_obj:
                    discounts_total += d_obj["attributes"].get("amount", 0) or 0

            # Tips
            tip_refs = rels.get("tips", {}).get("data", [])
            tips_total = 0.0
            for tr in tip_refs:
                t_obj = get_related(inc_map, tr)
                if t_obj:
                    tips_total += t_obj["attributes"].get("amount", 0) or 0

            # Payments
            payment_refs = rels.get("payments", {}).get("data", [])
            payment_methods = []
            payment_amounts = []
            for pr in payment_refs:
                p_obj = get_related(inc_map, pr)
                if p_obj:
                    p_attrs = p_obj["attributes"]
                    pm_ref = p_obj.get("relationships", {}).get("paymentMethod", {}).get("data")
                    pm_obj = get_related(inc_map, pm_ref)
                    pm_name = pm_obj["attributes"]["name"] if pm_obj else ""
                    payment_methods.append(pm_name)
                    payment_amounts.append(str(p_attrs.get("amount", 0)))

            # Items
            item_refs = rels.get("items", {}).get("data", [])
            if not item_refs:
                # Sale with no items - still record it
                row = {
                    "sale_id": sale_id,
                    "created_at": attrs.get("createdAt", ""),
                    "closed_at": attrs.get("closedAt", ""),
                    "sale_total": attrs.get("total", 0),
                    "sale_type": attrs.get("saleType", ""),
                    "sale_state": attrs.get("saleState", ""),
                    "people": attrs.get("people", ""),
                    "comment": attrs.get("comment", ""),
                    "customer_name": customer_name,
                    "customer_phone": customer_phone,
                    "customer_email": customer_email,
                    "waiter": waiter_name,
                    "discount_total": discounts_total,
                    "tips_total": tips_total,
                    "payment_methods": "|".join(payment_methods),
                    "payment_amounts": "|".join(payment_amounts),
                    "product_name": "",
                    "product_category": "",
                    "item_quantity": "",
                    "item_price": "",
                    "item_cost": "",
                    "item_comment": "",
                    "item_canceled": "",
                    "subitems": "",
                }
                all_rows.append(row)
            else:
                for ir in item_refs:
                    i_obj = get_related(inc_map, ir)
                    if not i_obj:
                        continue
                    i_attrs = i_obj["attributes"]

                    # Product
                    prod_ref = i_obj.get("relationships", {}).get("product", {}).get("data")
                    prod_obj = get_related(inc_map, prod_ref)
                    prod_name = prod_obj["attributes"]["name"] if prod_obj else ""
                    prod_cost = prod_obj["attributes"].get("cost", "") if prod_obj else ""

                    # Product category
                    cat_name = ""
                    if prod_obj:
                        cat_ref = prod_obj.get("relationships", {}).get("productCategory", {}).get("data")
                        cat_obj = get_related(inc_map, cat_ref)
                        if cat_obj:
                            cat_name = cat_obj["attributes"].get("name", "")

                    # Subitems (modifiers)
                    sub_refs = i_obj.get("relationships", {}).get("subitems", {}).get("data", [])
                    sub_names = []
                    for sr in sub_refs:
                        s_obj = get_related(inc_map, sr)
                        if s_obj:
                            sp_ref = s_obj.get("relationships", {}).get("product", {}).get("data")
                            sp_obj = get_related(inc_map, sp_ref)
                            s_name = sp_obj["attributes"]["name"] if sp_obj else f"subitem#{sr['id']}"
                            sub_names.append(s_name)

                    row = {
                        "sale_id": sale_id,
                        "created_at": attrs.get("createdAt", ""),
                        "closed_at": attrs.get("closedAt", ""),
                        "sale_total": attrs.get("total", 0),
                        "sale_type": attrs.get("saleType", ""),
                        "sale_state": attrs.get("saleState", ""),
                        "people": attrs.get("people", ""),
                        "comment": attrs.get("comment", ""),
                        "customer_name": customer_name,
                        "customer_phone": customer_phone,
                        "customer_email": customer_email,
                        "waiter": waiter_name,
                        "discount_total": discounts_total,
                        "tips_total": tips_total,
                        "payment_methods": "|".join(payment_methods),
                        "payment_amounts": "|".join(payment_amounts),
                        "product_name": prod_name,
                        "product_category": cat_name,
                        "item_quantity": i_attrs.get("quantity", ""),
                        "item_price": i_attrs.get("price", ""),
                        "item_cost": prod_cost,
                        "item_comment": i_attrs.get("comment", ""),
                        "item_canceled": i_attrs.get("canceled", ""),
                        "subitems": "|".join(sub_names),
                    }
                    all_rows.append(row)

        total_sales += len(sales)
        last_date = sales[-1]["attributes"].get("createdAt", "")
        print(f"  Page {page}: {len(sales)} sales (total: {total_sales}) | last: {last_date}")
        sys.stdout.flush()

        if len(sales) < PAGE_SIZE:
            break

        page += 1
        time.sleep(0.3)  # be nice to the API

    return all_rows, all_raw, token


def main():
    print("=" * 60)
    print("FUDO Sales Extractor - Mocawa Cafe")
    print("=" * 60)

    token = authenticate()

    print(f"\nFetching all sales (page size {PAGE_SIZE})...\n")
    rows, raw_data, token = fetch_all_sales(token)

    # Write CSV
    if rows:
        fieldnames = list(rows[0].keys())
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nCSV saved: {OUTPUT_CSV}")
        print(f"  {len(rows)} rows (line items)")

    # Write raw JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False)
    print(f"Raw JSON saved: {OUTPUT_JSON}")

    # Summary
    sale_ids = set(r["sale_id"] for r in rows)
    print(f"\nSummary:")
    print(f"  Total unique sales: {len(sale_ids)}")
    print(f"  Total line items: {len(rows)}")
    if rows:
        print(f"  Date range: {rows[0]['created_at']} to {rows[-1]['created_at']}")
    print("\nDone!")


if __name__ == "__main__":
    main()
