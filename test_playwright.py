from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        
        print("Logging in...")
        page.goto('http://127.0.0.1:10000/login')
        page.fill('input[type="text"]', 'admin')
        page.fill('input[type="password"]', 'chang3m3N0w!')
        page.click('button[type="submit"]')
        
        page.wait_for_selector('text="Live Infrastructure Status"')
        print("Logged in!")
        
        print("Clicking Add Node...")
        page.click('text="Add Node"')
        page.wait_for_selector('#addNodeModal', state='visible')
        
        print("Filling form...")
        page.fill('#nodeName', 'Test1234')
        page.fill('#nodeHost', '1.1.1.1')
        
        print("Submitting...")
        page.click('button:has-text("Connect Node")')
        
        # Wait a bit
        time.sleep(2)
        
        # Check if node is in the table
        content = page.content()
        if "Test1234" in content:
            print("SUCCESS! Node is in the table.")
        else:
            print("FAILED! Node not found in table.")
            
        browser.close()

run()
