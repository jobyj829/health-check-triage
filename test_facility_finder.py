"""
Test nearby facility finder with two zip codes: 10001 and 90210
"""

from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:5001"

def test_facility_finder_with_zip(page, zip_code, test_name):
    """Test facility finder with a specific zip code."""
    
    print(f"\n{'=' * 70}")
    print(f"{test_name}")
    print(f"{'=' * 70}")
    
    # Go to homepage (or start over)
    if page.url != BASE_URL + "/":
        print("\n[STEP] Starting over...")
        start_over = page.locator('a:has-text("Start Over"), a[href="/restart"], a[href="/"]').first
        if start_over.count() > 0:
            start_over.click()
            page.wait_for_load_state('networkidle')
        else:
            page.goto(BASE_URL)
            page.wait_for_load_state('networkidle')
    else:
        page.goto(BASE_URL)
        page.wait_for_load_state('networkidle')
    
    print("✓ On homepage")
    
    # Step 1: Accept disclaimer
    print("\n[STEP 1] Accepting disclaimer...")
    consent_checkbox = page.locator('input[type="checkbox"]#consent')
    consent_checkbox.check()
    time.sleep(0.3)
    
    continue_button = page.locator('button:has-text("I Understand"), button:has-text("Continue"), button[type="submit"]')
    continue_button.first.click()
    page.wait_for_load_state('networkidle')
    print("✓ Clicked 'I Understand, Continue'")
    
    # Step 2: Name
    print("\n[STEP 2] Name: Alex...")
    time.sleep(0.5)
    name_input = page.locator('input[type="text"], input[name="answer"]').first
    if name_input.count() > 0:
        name_input.fill('Alex')
        name_input.press('Enter')
        page.wait_for_load_state('networkidle')
        print("✓ Typed Alex and pressed Continue")
    
    # Step 3: Answering for
    print("\n[STEP 3] Selecting 'I'm filling this out for myself'...")
    time.sleep(0.5)
    first_button = page.locator('button').first
    first_button.click()
    page.wait_for_load_state('networkidle')
    print("✓ Selected first option")
    
    # Step 4: Age
    print("\n[STEP 4] Age: 50...")
    time.sleep(0.5)
    age_input = page.locator('input[type="number"]')
    if age_input.count() > 0:
        age_input.fill('50')
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
        print("✓ Entered 50")
    
    # Step 5: Sex
    print("\n[STEP 5] Sex: Male...")
    time.sleep(0.5)
    male_button = page.locator('button[name="answer"][value="male"], button:has-text("Male")').first
    if male_button.count() > 0:
        male_button.click()
        page.wait_for_load_state('networkidle')
        print("✓ Selected Male")
    
    # Step 6: Symptoms
    print("\n[STEP 6] Symptoms: 'chest pain and shortness of breath'...")
    time.sleep(0.5)
    
    # Check question text to verify we're at symptoms
    page_content = page.content()
    if "bothering" in page_content.lower() or "symptoms" in page_content.lower():
        print("  ✓ At symptoms question")
        textarea = page.locator('textarea[name="answer"]')
        if textarea.count() > 0:
            textarea.fill('chest pain and shortness of breath')
            page.locator('button[type="submit"]').click()
            page.wait_for_load_state('networkidle')
            print("  ✓ Entered symptoms and clicked Continue")
    
    # Step 7: PMH
    print("\n[STEP 7] PMH: 'heart problems'...")
    time.sleep(0.5)
    
    page_content = page.content()
    if "medical history" in page_content.lower() or "health conditions" in page_content.lower():
        print("  ✓ At PMH question")
        textarea = page.locator('textarea[name="answer"]')
        if textarea.count() > 0:
            textarea.fill('heart problems')
            page.locator('button[type="submit"]').click()
            page.wait_for_load_state('networkidle')
            print("  ✓ Entered PMH and clicked Continue")
    
    # Step 8: Zip code
    print(f"\n[STEP 8] Zip code: '{zip_code}'...")
    time.sleep(0.5)
    
    # Check if we're at zip code question
    page_content = page.content()
    
    if 'zip' in page_content.lower() or 'postal' in page_content.lower() or 'location' in page_content.lower():
        print(f"  ✓ Zip code question found")
        zip_input = page.locator('input[type="text"], input[name="answer"]')
        if zip_input.count() > 0:
            zip_input.fill(zip_code)
            # Click the Continue button (not Skip)
            continue_btn = page.locator('button:has-text("Continue")')
            continue_btn.click()
            page.wait_for_load_state('networkidle')
            print(f"  ✓ Entered {zip_code} and clicked Continue")
    elif '/results' in page.url:
        print(f"  ⚠️  Already at results (red flag triggered before zip code)")
    else:
        print(f"  ⚠️  Zip code question not found")
        print(f"  Current URL: {page.url}")
        
    # Check if there are follow-up questions and answer them quickly
    max_followups = 10
    followup_count = 0
    
    while followup_count < max_followups and '/interview' in page.url:
        time.sleep(0.5)
        page_content = page.content()
        
        # Check if there's a question to answer
        if 'button[name="answer"]' in page.content():
            # Try to click the first option (usually safest/quickest)
            first_button = page.locator('button[name="answer"]').first
            if first_button.count() > 0:
                first_button.click()
                page.wait_for_load_state('networkidle')
                followup_count += 1
                print(f"  ✓ Answered follow-up {followup_count}")
        elif textarea.count() > 0:
            textarea.fill('yes')
            page.locator('button[type="submit"]').click()
            page.wait_for_load_state('networkidle')
            followup_count += 1
            print(f"  ✓ Answered follow-up {followup_count}")
        else:
            break
    
    if followup_count > 0:
        print(f"  ✓ Completed {followup_count} follow-up questions")
    
    # Step 9-10: Check if at results and take screenshot
    print("\n[STEPS 9-10] Checking for results page...")
    time.sleep(1)
    
    if '/results' in page.url:
        print("  ✓ At results page (red flag triggered)")
        
        # Take initial screenshot
        page.screenshot(path=f'screenshots/facility_{zip_code}_results_top.png', full_page=False)
        print(f"  📸 Screenshot saved: facility_{zip_code}_results_top.png")
    else:
        print(f"  ⚠️  Not at results yet, current URL: {page.url}")
    
    # Steps 11-13: Look for facilities section and wait
    print("\n[STEPS 11-13] Looking for 'Nearby Emergency Departments'...")
    
    # Scroll down to find the section
    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
    time.sleep(1)
    
    page_content = page.content()
    
    if 'Nearby' in page_content or 'Emergency Departments' in page_content or 'Facilities' in page_content:
        print("  ✓ 'Nearby Emergency Departments' section found")
        
        # Wait 5 seconds for API call
        print("  ⏳ Waiting 5 seconds for facility search to complete...")
        time.sleep(5)
        
        # Check for loading/error messages
        if 'loading' in page_content.lower() or 'searching' in page_content.lower():
            print("  ⏳ Still loading facilities...")
            time.sleep(3)
        
        if 'error' in page_content.lower():
            print("  ⚠️  Error message detected")
        
        # Refresh page content after waiting
        page_content = page.content()
        
        # Look for hospital names (common patterns)
        import re
        
        # Check for specific hospital/facility patterns
        hospitals_found = []
        
        # Common hospital name patterns
        hospital_patterns = [
            r'([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Hospital|Medical Center|Medical Centre)',
            r'Mount [A-Z][a-z]+\s+(?:Hospital|Medical)',
            r'St\.\s+[A-Z][a-z]+(?:\'s)?\s+Hospital',
            r'New York\-Presbyterian',
            r'Cedars-Sinai',
            r'UCLA',
        ]
        
        for pattern in hospital_patterns:
            matches = re.findall(pattern, page_content)
            hospitals_found.extend(matches)
        
        if hospitals_found:
            print(f"  ✓ Found {len(hospitals_found)} hospitals:")
            for hospital in hospitals_found[:5]:
                print(f"    - {hospital}")
        else:
            print("  ⚠️  No hospital names detected yet")
        
        # Check for Google Maps link
        if 'Google Maps' in page_content or 'maps.google' in page_content or 'Open in' in page_content:
            print("  ✓ Google Maps link found")
        else:
            print("  ⚠️  Google Maps link not found")
        
        # Take screenshot of facilities section
        page.screenshot(path=f'screenshots/facility_{zip_code}_facilities.png', full_page=True)
        print(f"  📸 Screenshot saved: facility_{zip_code}_facilities.png")
        
    else:
        print("  ⚠️  'Nearby Emergency Departments' section not found")
        
        # Take screenshot anyway
        page.screenshot(path=f'screenshots/facility_{zip_code}_no_facilities.png', full_page=True)
        print(f"  📸 Screenshot saved: facility_{zip_code}_no_facilities.png")
    
    # Extract visible text from facilities section for reporting
    print("\n[ANALYSIS] Extracting facility information...")
    
    # Try to find facility cards/sections
    facility_cards = page.locator('[class*="facility"], [class*="hospital"], .bg-white.border').all()
    
    if facility_cards:
        print(f"  Found {len(facility_cards)} potential facility cards")
        for i, card in enumerate(facility_cards[:3]):
            text = card.text_content().strip()
            if len(text) > 10 and len(text) < 500:
                print(f"  Card {i+1}: {text[:100]}")

def main():
    """Run facility finder tests with two zip codes."""
    
    print("=" * 70)
    print("NEARBY FACILITY FINDER TEST")
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 900})
        page = context.new_page()
        
        try:
            # Test 1: Zip code 10001 (Manhattan, NYC)
            test_facility_finder_with_zip(page, "10001", "TEST 1: ZIP CODE 10001 (Manhattan, NYC)")
            
            time.sleep(3)
            
            # Test 2: Zip code 90210 (Beverly Hills, CA)
            test_facility_finder_with_zip(page, "90210", "TEST 2: ZIP CODE 90210 (Beverly Hills, CA)")
            
            print("\n" + "=" * 70)
            print("TESTS COMPLETE")
            print("=" * 70)
            
            time.sleep(5)
            
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            browser.close()

if __name__ == "__main__":
    import os
    os.makedirs('screenshots', exist_ok=True)
    
    main()
