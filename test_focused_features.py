"""
Two focused tests:
A. Verify answering_for options, zip code, and triage nurse card
B. Verify unable to respond immediate redirect
"""

from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:5001"

def test_a_answering_for_and_zip(page):
    """Test A: Verify answering_for screen and zip code question."""
    
    print("\n" + "=" * 70)
    print("TEST A: ANSWERING FOR OPTIONS + ZIP CODE")
    print("=" * 70)
    
    # Step 1: Go to homepage
    print("\n[STEP 1] Going to http://localhost:5001...")
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    print("✓ Homepage loaded")
    
    # Step 2: Accept disclaimer
    print("\n[STEP 2] Accepting disclaimer...")
    consent_checkbox = page.locator('input[type="checkbox"]#consent')
    consent_checkbox.check()
    time.sleep(0.3)
    
    # Look for "I Understand, Continue" or similar
    continue_button = page.locator('button:has-text("I Understand"), button:has-text("Continue"), button[type="submit"]')
    continue_button.first.click()
    page.wait_for_load_state('networkidle')
    print("✓ Clicked 'I Understand, Continue'")
    
    # Step 3: Name
    print("\n[STEP 3] Entering name 'Alex'...")
    time.sleep(0.5)
    name_input = page.locator('input[type="text"], input[name="answer"]').first
    if name_input.count() > 0:
        name_input.fill('Alex')
        print("  → Typed: Alex")
        
        continue_btn = page.locator('button:has-text("Continue"), button[type="submit"]')
        continue_btn.first.click()
        page.wait_for_load_state('networkidle')
        print("  ✓ Pressed Continue")
    
    # Step 4: SCREENSHOT of "Who is this health check for?" screen
    print("\n[STEP 4] Taking screenshot of 'Who is this health check for?' screen...")
    time.sleep(0.5)
    
    # Get question text
    question = page.locator('h1, h2, .text-2xl, .text-xl').first
    if question.count() > 0:
        question_text = question.text_content().strip()
        print(f"  Question: {question_text}")
    
    # Take screenshot
    page.screenshot(path='screenshots/test_a_answering_for_screen.png', full_page=True)
    print("  📸 SCREENSHOT SAVED: test_a_answering_for_screen.png")
    
    # Step 5: Count and verify options
    print("\n[STEP 5] Verifying 5 options with icons...")
    
    all_buttons = page.locator('button[name="answer"], button[type="button"]').all()
    print(f"  Found {len(all_buttons)} options:")
    
    for i, btn in enumerate(all_buttons[:6]):
        text = btn.text_content().strip()
        
        # Check for icons (SVG or emoji)
        has_icon = 'svg' in btn.inner_html().lower() or any(emoji in text for emoji in ['🟢', '😊', '👥', '⚠️', '🔴'])
        icon_indicator = " [icon]" if has_icon else ""
        
        print(f"    {i+1}. {text[:70]}{icon_indicator}")
    
    # Step 6: Select first option
    print("\n[STEP 6] Selecting 'I'm filling this out for myself'...")
    if len(all_buttons) > 0:
        all_buttons[0].click()
        page.wait_for_load_state('networkidle')
        print("  ✓ Selected first option")
    
    # Step 7: Age and Sex
    print("\n[STEP 7] Age: 45, Sex: Male...")
    time.sleep(0.5)
    
    age_input = page.locator('input[type="number"]')
    if age_input.count() > 0:
        age_input.fill('45')
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
        print("  → Age: 45")
    
    time.sleep(0.5)
    male_button = page.locator('button[name="answer"][value="male"], button:has-text("Male")').first
    if male_button.count() > 0:
        male_button.click()
        page.wait_for_load_state('networkidle')
        print("  → Sex: Male")
    
    # Step 8: Body map - click "Belly"
    print("\n[STEP 8] Body map: clicking 'Belly'...")
    time.sleep(0.5)
    
    # Try to click the Belly button
    belly_button = page.locator('button:has-text("Belly")').first
    if belly_button.count() > 0:
        belly_button.click()
        print("  → Clicked: Belly button")
        time.sleep(0.3)
        
        continue_btn = page.locator('button:has-text("Continue"), button[type="submit"]')
        if continue_btn.count() > 0:
            continue_btn.click()
            page.wait_for_load_state('networkidle')
            print("  ✓ Clicked Continue")
    
    # Step 9: Symptoms
    print("\n[STEP 9] Symptoms: 'stomach ache'...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        textarea.fill('stomach ache')
        print("  → Typed: stomach ache")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 10: PMH
    print("\n[STEP 10] PMH: 'none'...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        textarea.fill('none')
        print("  → Typed: none")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 11-12: ZIP CODE QUESTION
    print("\n[STEPS 11-12] Looking for ZIP CODE question...")
    time.sleep(0.5)
    
    page_content = page.content()
    question_elem = page.locator('h1, h2, .text-2xl, .text-xl').first
    if question_elem.count() > 0:
        question_text = question_elem.text_content().strip()
        print(f"  Current question: {question_text}")
    
    if 'zip' in page_content.lower() or 'postal' in page_content.lower() or 'location' in page_content.lower():
        print("  ✓ ZIP CODE question found!")
        
        # Check for "Skip this step" link
        skip_link = page.locator('a:has-text("Skip"), button:has-text("Skip")')
        if skip_link.count() > 0:
            print("  ✓ 'Skip this step' link found")
        else:
            print("  ⚠️  'Skip this step' link not found")
        
        # Take screenshot
        page.screenshot(path='screenshots/test_a_zip_code_question.png', full_page=True)
        print("  📸 SCREENSHOT SAVED: test_a_zip_code_question.png")
        
        # Step 13: Enter zip code
        print("\n[STEP 13] Entering zip code '10001'...")
        zip_input = page.locator('input[type="text"], input[name="answer"]')
        if zip_input.count() > 0:
            zip_input.fill('10001')
            print("  → Typed: 10001")
            page.locator('button[type="submit"]').click()
            page.wait_for_load_state('networkidle')
    else:
        print("  ⚠️  ZIP CODE question not found")
        print(f"  Current page content preview: {page_content[:200]}")
    
    # Step 14: Follow-ups with low-risk answers
    print("\n[STEP 14] Answering follow-ups with LOW-RISK answers...")
    
    question_count = 0
    max_questions = 20
    
    while question_count < max_questions:
        time.sleep(0.3)
        
        if '/results' in page.url:
            print(f"  ✓ Reached results after {question_count} questions")
            break
        
        try:
            # Check for emoji severity slider
            emoji_mild = page.locator('button:has-text("😊")')
            if emoji_mild.count() > 0:
                print("    → Found severity slider, clicking Mild")
                emoji_mild.first.click()
                page.wait_for_load_state('networkidle')
                question_count += 1
                continue
            
            if page.locator('button[name="answer"]').count() > 0:
                buttons = page.locator('button[name="answer"]').all()
                
                # Find low-risk answers
                clicked = False
                for btn in buttons:
                    btn_text = btn.text_content().strip().lower()
                    if any(word in btn_text for word in ['no', 'mild', 'slowly', 'dull', 'all over']):
                        btn.click()
                        clicked = True
                        break
                
                if not clicked:
                    # Default to first option
                    buttons[0].click()
            
            page.wait_for_load_state('networkidle')
            question_count += 1
            
        except:
            break
    
    # Step 15: Take screenshot of results
    print("\n[STEP 15] Taking screenshot of results page...")
    time.sleep(0.5)
    
    page_content = page.content()
    
    # Check for triage nurse card
    if 'Show This to the Triage Nurse' in page_content:
        print("  ✓ Triage nurse card found")
    
    # Check for nearby facilities
    if 'Nearby' in page_content or 'Emergency Departments' in page_content:
        print("  ✓ Nearby facilities section found")
    
    # Check for "When in doubt" message
    if 'when in doubt' in page_content.lower():
        print("  ✓ 'When in doubt' message found")
    
    page.screenshot(path='screenshots/test_a_final_results.png', full_page=True)
    print("  📸 SCREENSHOT SAVED: test_a_final_results.png")

def test_b_unable_to_respond(page):
    """Test B: Unable to respond immediate redirect."""
    
    print("\n" + "=" * 70)
    print("TEST B: UNABLE TO RESPOND - IMMEDIATE REDIRECT")
    print("=" * 70)
    
    # Step 16: Start Over
    print("\n[STEP 16] Starting over...")
    start_over = page.locator('a:has-text("Start Over"), a[href="/restart"], a[href="/"]').first
    if start_over.count() > 0:
        start_over.click()
        page.wait_for_load_state('networkidle')
        print("✓ Returned to homepage")
    else:
        page.goto(BASE_URL)
        page.wait_for_load_state('networkidle')
    
    # Step 17: Accept disclaimer
    print("\n[STEP 17] Accepting disclaimer...")
    consent_checkbox = page.locator('input[type="checkbox"]#consent')
    consent_checkbox.check()
    time.sleep(0.3)
    continue_button = page.locator('button:has-text("I Understand"), button:has-text("Continue"), button[type="submit"]')
    continue_button.first.click()
    page.wait_for_load_state('networkidle')
    
    # Step 18: Name
    print("\n[STEP 18] Entering name 'Sam'...")
    time.sleep(0.5)
    name_input = page.locator('input[type="text"], input[name="answer"]').first
    if name_input.count() > 0:
        name_input.fill('Sam')
        print("  → Typed: Sam")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 19: Select "can't respond" option (5th/last option)
    print("\n[STEP 19] Selecting 'can't respond' option...")
    time.sleep(0.5)
    
    all_buttons = page.locator('button[name="answer"], button[type="button"]').all()
    
    print(f"  Found {len(all_buttons)} options")
    
    # Look for the "can't respond" option (should be last)
    cant_respond_clicked = False
    for btn in all_buttons:
        btn_text = btn.text_content().strip().lower()
        if "can't respond" in btn_text or "cannot respond" in btn_text or "unresponsive" in btn_text:
            print(f"  → Clicking: {btn.text_content().strip()[:60]}")
            btn.click()
            page.wait_for_load_state('networkidle')
            cant_respond_clicked = True
            break
    
    if not cant_respond_clicked:
        print("  ⚠️  Could not find 'can't respond' option, trying last button...")
        if len(all_buttons) >= 5:
            all_buttons[-1].click()  # Last button
            page.wait_for_load_state('networkidle')
            print(f"  → Clicked last button: {all_buttons[-1].text_content().strip()[:60]}")
    
    # Step 20-21: Check for immediate redirect
    print("\n[STEPS 20-21] Checking for IMMEDIATE redirect to results...")
    time.sleep(0.5)
    
    current_url = page.url
    print(f"  Current URL: {current_url}")
    
    if '/results' in current_url:
        print("  ✓✓✓ IMMEDIATELY REDIRECTED to results! ✓✓✓")
        
        page_content = page.content()
        
        # Check for emergency alert
        if 'Emergency' in page_content or 'Call 911' in page_content:
            print("  ✓ Emergency recommendation found")
        
        # Check for red flag
        if 'red flag' in page_content.lower() or 'unresponsive' in page_content.lower() or 'unable to respond' in page_content.lower():
            print("  ✓ Red flag alert detected")
        
        # Take screenshot
        page.screenshot(path='screenshots/test_b_unable_respond_results.png', full_page=True)
        print("\n  📸 SCREENSHOT SAVED: test_b_unable_respond_results.png")
    else:
        print("  ✗ Did NOT redirect to results")
        print("  Still on interview page")
        
        # Take screenshot of current page
        page.screenshot(path='screenshots/test_b_no_redirect.png')
        print("  📸 Screenshot saved: test_b_no_redirect.png")

def main():
    """Run both focused tests."""
    
    print("=" * 70)
    print("FOCUSED FEATURES TEST")
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 900})
        page = context.new_page()
        
        try:
            # Test A
            test_a_answering_for_and_zip(page)
            
            time.sleep(2)
            
            # Test B
            test_b_unable_to_respond(page)
            
            print("\n" + "=" * 70)
            print("TESTS COMPLETE")
            print("=" * 70)
            
            time.sleep(3)
            
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
