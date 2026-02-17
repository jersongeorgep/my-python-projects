from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time

# Setup Chrome
options = Options()
# options.add_argument('--headless')  # Run without opening browser window
driver = webdriver.Chrome(options=options)

# Go to login page
driver.get("http://localhost:8080/oshaiger-bgsoft/admin")

# Login
driver.find_element(By.NAME, "email").send_keys("Sales08@oshaigerpharma.com")
driver.find_element(By.NAME, "password").send_keys("123456")
driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]").click()

# Wait for dashboard to load (wait for sidebar)
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "aside.sidebar"))
)

# Expand all parent menus by clicking them (if needed)
parent_menus = driver.find_elements(By.CSS_SELECTOR, "aside.sidebar ul li")

menus = []

for menu_item in parent_menus:
    try:
        # Get the main menu name
        menu_link = menu_item.find_element(By.CSS_SELECTOR, 'a')
        menu_text = menu_link.text.strip()
        
        # Expand the menu if it has submenu
        try:
            submenu_ul = menu_item.find_element(By.CSS_SELECTOR, 'ul')
            driver.execute_script("arguments[0].click();", menu_link)
            time.sleep(0.5)

            submenu_links = submenu_ul.find_elements(By.TAG_NAME, 'a')
            for sub in submenu_links:
                sub_text = sub.text.strip()
                menus.append({"Menu": menu_text, "Submenu": sub_text})
        except:
            # No submenu
            menus.append({"Menu": menu_text, "Submenu": None})

    except Exception as e:
        print("Skipping item:", e)

# Save to Excel
df = pd.DataFrame(menus)
df.to_excel("sidebar_menus.xlsx", index=False)
print("✅ Menus saved to sidebar_menus.xlsx")

driver.quit()