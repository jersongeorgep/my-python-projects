import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

def mark_attendance():
    options = Options()
    options.add_argument("--headless")  # Run in background without opening browser
    options.add_argument("--disable-gpu")  # Disable GPU for better performance
    options.add_argument("--no-sandbox")  # Bypass OS security model

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # Open the localhost URL
        driver.get("http://192.168.1.100/eofficeais/attendance.php")
        time.sleep(3)

        # Find the "Mark In" button by ID or other selector and click it
        markin_button = driver.find_element(By.ID, "markin")  # Replace 'markin' with the actual button ID
        """ markin_button.click() """
        if(markin_button):
            print("Mark In button found and clicked.")

        print("Attendance marked successfully!")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    mark_attendance()
