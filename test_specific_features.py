"""
Test two specific features:
1. Mental status red flag immediate redirect
2. Severity slider with emojis and context tags
"""

from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:5001"

def test_mental_status_flag(page):
    """Test 1: Mental status red flag should redirect immediately."""
    
    print("\n" + "=" * 70)
    print("TEST 1: MENTAL STATUS RED FLAG")
    print("=" * 70)
    
    # Step 1: Go to homepage
    print("\n[STEP 1] Going to homepage...")
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    print("✓ Homepage loaded")
    
    # Step 2: Accept disclaimer
    print("\n[STEP 2] Accepting disclaimer...")
    consent_checkbox = page.locator('input[type="checkbox"]#consent')
    consent_checkbox.check()
    time.sleep(0.3)
    
    get_started = page.locator('button:has-text("Get Started"), button[type="submit"]')
    get_started.first.click()
    page.wait_for_load_state('networkidle')
    print("✓ Clicked Get Started")
    
    # Step 3: Name
    print("\n[STEP 3] Entering name 'Test'...")
    time.sleep(0.5)
    name_input = page.locator('input[type="text"], input[name="answer"]').first
    if name_input.count() > 0:
        name_input.fill('Test')
        print("  → Typed: Test")
        
        # Click Continue or press Enter
        continue_btn = page.locator('button:has-text("Continue"), button[type="submit"]')
        if continue_btn.count() > 0:
            continue_btn.click()
        else:
            name_input.press('Enter')
        
        page.wait_for_load_state('networkidle')
        print("  ✓ Name submitted")
    
    # Step 4: Mental status question - click the 4th/last option
    print("\n[STEP 4] Looking for mental status question...")
    time.sleep(0.5)
    
    # Get the question text to confirm we're on the right screen
    question_text = page.locator('h1, h2, .text-2xl, .text-xl').first.text_content()
    print(f"  Question: {question_text}")
    
    # Look for the specific button - "won't wake up or can't respond"
    # The test showed it's the 4th button, so let's get all buttons and click the 4th one
    all_buttons = page.locator('button[name="answer"], button[type="button"]').all()
    
    if len(all_buttons) >= 4:
        fourth_button = all_buttons[3]  # 4th button (0-indexed)
        button_text = fourth_button.text_content().strip()
        print(f"  ✓ Found 4th button: {button_text}")
        fourth_button.click()
        page.wait_for_load_state('networkidle')
        print("  → Clicked the button")
        
        # Step 5: Check if redirected to results
        print("\n[STEP 5] Checking for redirect to results...")
        time.sleep(0.5)
        
        current_url = page.url
        print(f"  Current URL: {current_url}")
        
        if '/results' in current_url:
            print("  ✓ REDIRECTED to results page!")
            
            # Check for emergency content
            page_content = page.content()
            
            if 'Emergency' in page_content or 'Call 911' in page_content:
                print("  ✓ Emergency recommendation found")
            
            if 'red flag' in page_content.lower() or 'immediate' in page_content.lower():
                print("  ✓ Red flag language detected")
            
            # Take screenshot
            page.screenshot(path='screenshots/mental_status_results.png', full_page=True)
            print("\n  📸 Screenshot saved: screenshots/mental_status_results.png")
            
            return True
        else:
            print("  ✗ Did NOT redirect to results")
            print(f"  Still on: {current_url}")
            
            # Take screenshot of current page
            page.screenshot(path='screenshots/mental_status_no_redirect.png')
            print("  📸 Screenshot saved: screenshots/mental_status_no_redirect.png")
            
            return False
    else:
        print("  ✗ Could not find 'won't wake up / can't respond' button")
        
        # List all buttons to see what's available
        print("\n  Available buttons:")
        buttons = page.locator('button').all()
        for i, btn in enumerate(buttons[:6]):
            print(f"    {i+1}. {btn.text_content().strip()[:60]}")
        
        return False

def test_severity_slider(page):
    """Test 2: Severity slider with emojis and context tags."""
    
    print("\n" + "=" * 70)
    print("TEST 2: SEVERITY SLIDER + CONTEXT TAGS")
    print("=" * 70)
    
    # Step 7: Start Over
    print("\n[STEP 7] Starting over...")
    start_over = page.locator('a:has-text("Start Over"), a[href="/restart"], a[href="/"]').first
    if start_over.count() > 0:
        start_over.click()
        page.wait_for_load_state('networkidle')
        print("✓ Returned to homepage")
    else:
        page.goto(BASE_URL)
        page.wait_for_load_state('networkidle')
        print("✓ Went to homepage")
    
    # Step 8: Accept disclaimer
    print("\n[STEP 8] Accepting disclaimer...")
    consent_checkbox = page.locator('input[type="checkbox"]#consent')
    consent_checkbox.check()
    time.sleep(0.3)
    get_started = page.locator('button:has-text("Get Started"), button[type="submit"]')
    get_started.first.click()
    page.wait_for_load_state('networkidle')
    print("✓ Started")
    
    # Step 9: Name
    print("\n[STEP 9] Name: Alex...")
    time.sleep(0.5)
    name_input = page.locator('input[type="text"], input[name="answer"]').first
    if name_input.count() > 0:
        name_input.fill('Alex')
        print("  → Typed: Alex")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 10: Answering for myself (FIRST option)
    print("\n[STEP 10] Answering for: myself (FIRST option)...")
    time.sleep(0.5)
    myself_button = page.locator('button').first  # First button
    if myself_button.count() > 0:
        button_text = myself_button.text_content().strip()
        print(f"  → Clicking first button: {button_text}")
        myself_button.click()
        page.wait_for_load_state('networkidle')
    
    # Step 11: Age
    print("\n[STEP 11] Age: 30...")
    time.sleep(0.5)
    age_input = page.locator('input[type="number"]')
    if age_input.count() > 0:
        age_input.fill('30')
        print("  → Typed: 30")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 12: Sex
    print("\n[STEP 12] Sex: Male...")
    time.sleep(0.5)
    male_button = page.locator('button[name="answer"][value="male"], button:has-text("Male")').first
    if male_button.count() > 0:
        male_button.click()
        page.wait_for_load_state('networkidle')
        print("  → Selected: Male")
    
    # Step 13: Body map - Head
    print("\n[STEP 13] Body map: Head...")
    time.sleep(0.5)
    
    # Look for Head button or region
    head_button = page.locator('button:has-text("Head"), [data-region="head"]').first
    if head_button.count() > 0:
        head_button.click()
        print("  → Clicked: Head")
        time.sleep(0.3)
        
        continue_btn = page.locator('button:has-text("Continue"), button[type="submit"]')
        if continue_btn.count() > 0:
            continue_btn.click()
            page.wait_for_load_state('networkidle')
            print("  ✓ Body map submitted")
    
    # Step 14: Symptoms
    print("\n[STEP 14] Symptoms: 'my head hurts'...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        textarea.fill('my head hurts')
        print("  → Typed: my head hurts")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 15: PMH
    print("\n[STEP 15] PMH: 'none'...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        textarea.fill('none')
        print("  → Typed: none")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 16-22: Follow-up questions
    print("\n[STEPS 16-22] Follow-up questions...")
    
    question_count = 0
    found_context_tag = False
    found_severity_slider = False
    
    while question_count < 20:
        time.sleep(0.3)
        
        if '/results' in page.url:
            print(f"\n  ✓ Reached results after {question_count} questions")
            break
        
        try:
            # Check for context tag
            page_content = page.content()
            
            if 'About your headache' in page_content or 'about your headache' in page_content:
                if not found_context_tag:
                    print(f"\n  ✓ CONTEXT TAG FOUND: 'About your headache'")
                    found_context_tag = True
            
            # Get question text
            question_elem = page.locator('h1, h2, h3, .text-xl, .text-2xl').first
            if question_elem.count() > 0:
                question_text = question_elem.text_content().strip()
                print(f"\n  Q{question_count + 1}: {question_text[:60]}...")
            
            # Check for SEVERITY SLIDER with emojis
            emoji_buttons = page.locator('button:has-text("😊"), button:has-text("😐"), button:has-text("😣"), button:has-text("😱")')
            
            if emoji_buttons.count() > 0:
                if not found_severity_slider:
                    print(f"\n  ✓✓✓ SEVERITY SLIDER FOUND! ✓✓✓")
                    print(f"  Found {emoji_buttons.count()} emoji buttons")
                    
                    # List the emojis
                    for i in range(min(emoji_buttons.count(), 4)):
                        btn_text = emoji_buttons.nth(i).text_content().strip()
                        print(f"    Button {i+1}: {btn_text}")
                    
                    # Take screenshot of severity slider
                    page.screenshot(path='screenshots/severity_slider.png', full_page=True)
                    print(f"\n  📸 SEVERITY SLIDER screenshot saved!")
                    
                    found_severity_slider = True
                    
                    # Click "Mild" (first emoji)
                    print(f"\n  → Clicking 'Mild' (first emoji)...")
                    emoji_buttons.first.click()
                    page.wait_for_load_state('networkidle')
                    question_count += 1
                    continue
            
            # Regular question answering with low-risk answers
            if page.locator('button[name="answer"]').count() > 0:
                buttons = page.locator('button[name="answer"]').all()
                
                # Try to find low-risk options
                clicked = False
                for btn in buttons:
                    btn_text = btn.text_content().strip().lower()
                    if any(word in btn_text for word in ['no', 'slowly', 'all over', 'dull', 'aching', 'yes similar', 'gradually']):
                        btn.click()
                        print(f"    → {btn.text_content().strip()}")
                        clicked = True
                        break
                
                if not clicked:
                    # Default to "no" or first option
                    for btn in buttons:
                        if 'no' in btn.text_content().strip().lower():
                            btn.click()
                            print(f"    → {btn.text_content().strip()}")
                            clicked = True
                            break
                    
                    if not clicked:
                        buttons[0].click()
                        print(f"    → {buttons[0].text_content().strip()}")
            
            elif page.locator('textarea[name="answer"]').count() > 0:
                page.locator('textarea[name="answer"]').fill('mild')
                page.locator('button[type="submit"]').click()
                print(f"    → mild")
            
            page.wait_for_load_state('networkidle')
            question_count += 1
            
        except Exception as e:
            print(f"  Error: {e}")
            break
    
    # Final results
    print("\n[FINAL RESULTS] Analyzing results page...")
    time.sleep(0.5)
    
    page_content = page.content()
    
    # Check for personalization
    if 'Alex' in page_content:
        print("  ✓ Personalization: 'Alex' found on results page")
    else:
        print("  ✗ Personalization: 'Alex' NOT found")
    
    # Check for green/low-risk recommendation
    if 'Likely Okay' in page_content or "You're Okay" in page_content or 'green' in page_content.lower():
        print("  ✓ Low-risk/green recommendation found")
    elif 'Emergency' in page_content:
        print("  ⚠️  Emergency recommendation (expected low-risk)")
    
    # Take screenshot
    page.screenshot(path='screenshots/severity_slider_results.png', full_page=True)
    print("\n  📸 Final results screenshot saved: screenshots/severity_slider_results.png")
    
    return found_context_tag, found_severity_slider

def main():
    """Run both tests."""
    
    print("=" * 70)
    print("SPECIFIC FEATURES TEST")
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 900})
        page = context.new_page()
        
        try:
            # Test 1: Mental status flag
            mental_status_worked = test_mental_status_flag(page)
            
            time.sleep(2)
            
            # Test 2: Severity slider
            found_context, found_slider = test_severity_slider(page)
            
            # Summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            
            print("\n1. Mental Status Flag:")
            if mental_status_worked:
                print("   ✓ Redirected to emergency results page")
            else:
                print("   ✗ Did NOT redirect immediately")
            
            print("\n2. Context Tag ('About your headache'):")
            if found_context:
                print("   ✓ Found")
            else:
                print("   ✗ Not found")
            
            print("\n3. Severity Slider with Emojis:")
            if found_slider:
                print("   ✓ Found and screenshot captured")
            else:
                print("   ✗ Not found")
            
            print("\n" + "=" * 70)
            
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
