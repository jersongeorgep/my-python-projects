from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time

# Login and Admin URLs
login_url = "http://localhost:8080/oshaiger-bgsoft/admin"
target_urls = [
    "http://localhost:8080/oshaiger-bgsoft/admin/leads",
    "http://localhost:8080/oshaiger-bgsoft/admin/clients",
    "http://localhost:8080/oshaiger-bgsoft/admin/proposals",
    "http://localhost:8080/oshaiger-bgsoft/admin/estimates",
    "http://localhost:8080/oshaiger-bgsoft/admin/invoices",
    "http://localhost:8080/oshaiger-bgsoft/admin/payments",
    "http://localhost:8080/oshaiger-bgsoft/admin/credit_notes",
    "http://localhost:8080/oshaiger-bgsoft/admin/new-estimate",
    "http://localhost:8080/oshaiger-bgsoft/admin/purchase/items",
    "http://localhost:8080/oshaiger-bgsoft/admin/purchase/vendor_items",
    "http://localhost:8080/oshaiger-bgsoft/admin/purchase/vendors",
    "http://localhost:8080/oshaiger-bgsoft/admin/purchase/purchase_request",
    "http://localhost:8080/oshaiger-bgsoft/admin/purchase/purchase_order",
    "http://localhost:8080/oshaiger-bgsoft/admin/purchase/proforma_invoice",
    "http://localhost:8080/oshaiger-bgsoft/admin/purchase/invoices",
    "http://localhost:8080/oshaiger-bgsoft/admin/purchase/order_returns",
    "http://localhost:8080/oshaiger-bgsoft/admin/purchase/debit_notes",
    "http://localhost:8080/oshaiger-bgsoft/admin/purchase/contracts",
    "http://localhost:8080/oshaiger-bgsoft/admin/warehouse/manage_purchase",
    "http://localhost:8080/oshaiger-bgsoft/admin/warehouse/manage_delivery",
    "http://localhost:8080/oshaiger-bgsoft/admin/warehouse/manage_internal_delivery",
    "http://localhost:8080/oshaiger-bgsoft/admin/warehouse/loss_adjustment",
    "http://localhost:8080/oshaiger-bgsoft/admin/warehouse/manage_packing_list",
    "http://localhost:8080/oshaiger-bgsoft/admin/warehouse/manage_order_return",
    "http://localhost:8080/oshaiger-bgsoft/admin/warehouse/warehouse_mange",
    "http://localhost:8080/oshaiger-bgsoft/admin/warehouse/warehouse_history",
    "http://localhost:8080/oshaiger-bgsoft/admin/accounting/banking?group=bank_accounts",
    "http://localhost:8080/oshaiger-bgsoft/admin/accounting/journal_entry",
    "http://localhost:8080/oshaiger-bgsoft/admin/accounting/transaction?group=sales",
    "http://localhost:8080/oshaiger-bgsoft/admin/utilities/bulk_pdf_exporter",
    "http://localhost:8080/oshaiger-bgsoft/admin/accounting/transfer",
    "http://localhost:8080/oshaiger-bgsoft/admin/accounting/chart_of_accounts",
    "http://localhost:8080/oshaiger-bgsoft/admin/hr_profile/job_positions",
    "http://localhost:8080/oshaiger-bgsoft/admin/hr_profile/organizational_chart",
    "http://localhost:8080/oshaiger-bgsoft/admin/hr_profile/reception_staff",
    "http://localhost:8080/oshaiger-bgsoft/admin/hr_profile/staff_infor",
    "http://localhost:8080/oshaiger-bgsoft/admin/hr_profile/training?group=training_program",
    "http://localhost:8080/oshaiger-bgsoft/admin/hr_profile/contracts",
    "http://localhost:8080/oshaiger-bgsoft/admin/hr_profile/dependent_persons",
    "http://localhost:8080/oshaiger-bgsoft/admin/hr_profile/resignation_procedures",
    "http://localhost:8080/oshaiger-bgsoft/admin/shipment/shipping_status_manage",
    "http://localhost:8080/oshaiger-bgsoft/admin/expenses",
]

email = "info@oshaigerpharma.com"
password = "123456"

# Setup Chrome
options = Options()
# Uncomment the line below to run headless (no browser UI)
# options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

# Step 1: Log in
driver.get(login_url)
driver.find_element(By.NAME, "email").send_keys(email)
driver.find_element(By.NAME, "password").send_keys(password)
driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]").click()

# Wait for successful login
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "aside.sidebar")))

# Step 2: Visit each page and collect <th> headers
all_th_texts = []

for url in target_urls:
    driver.get(url)
    time.sleep(2)  # Adjust if the page loads slowly

    headers = driver.find_elements(By.TAG_NAME, "th")

    for th in headers:
        th_text = th.text.strip()
        if th_text:  # Only capture non-empty headers
            all_th_texts.append({
                "PageURL": url,
                "TableHeader": th_text
            })

# Step 3: Save to CSV
df = pd.DataFrame(all_th_texts)
df.to_csv("table_headers.csv", index=False)
print("✅ Extracted table headers saved to 'table_headers.csv'")

# Close the browser
driver.quit()
