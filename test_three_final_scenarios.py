"""
Test three scenarios with new features:
- 5 "answering for" options
- Zip code question
- "Show This to the Triage Nurse" card
- Nearby Emergency Departments
- Parent/child flow
"""

from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:5001"

def test_scenario_1_chest_pain_with_zip(page):
    """Test 1: High-risk chest pain with zip code."""
    
    print("\n" + "=" * 70)
    print("TEST 1: HIGH-RISK CHEST PAIN WITH ZIP CODE")
    print("=" * 70)
    
    # Steps 1-2: Homepage and disclaimer
    print("\n[STEPS 1-2] Homepage and disclaimer...")
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    
    consent_checkbox = page.locator('input[type="checkbox"]#consent')
    consent_checkbox.check()
    time.sleep(0.3)
    
    get_started = page.locator('button:has-text("Get Started"), button[type="submit"]')
    get_started.first.click()
    page.wait_for_load_state('networkidle')
    print("✓ Started")
    
    # Step 3: Name
    print("\n[STEP 3] Name: John...")
    time.sleep(0.5)
    name_input = page.locator('input[type="text"], input[name="answer"]').first
    if name_input.count() > 0:
        name_input.fill('John')
        print("  → Typed: John")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 4: Answering for - verify 5 options
    print("\n[STEP 4] Checking 'Who is this health check for?' options...")
    time.sleep(0.5)
    
    # Get all button options
    all_buttons = page.locator('button[name="answer"], button[type="button"]').all()
    
    print(f"  Found {len(all_buttons)} options:")
    for i, btn in enumerate(all_buttons[:6]):
        text = btn.text_content().strip()
        print(f"    {i+1}. {text[:70]}")
    
    if len(all_buttons) >= 5:
        print("  ✓ 5 or more options found")
    else:
        print(f"  ⚠️  Only {len(all_buttons)} options found (expected 5)")
    
    # Click FIRST option (myself)
    if len(all_buttons) > 0:
        first_btn = all_buttons[0]
        print(f"\n  → Clicking first option: {first_btn.text_content().strip()[:50]}")
        first_btn.click()
        page.wait_for_load_state('networkidle')
    
    # Step 5: Age and Sex
    print("\n[STEP 5] Age: 55, Sex: Male...")
    time.sleep(0.5)
    
    age_input = page.locator('input[type="number"]')
    if age_input.count() > 0:
        age_input.fill('55')
        print("  → Age: 55")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    time.sleep(0.5)
    male_button = page.locator('button[name="answer"][value="male"], button:has-text("Male")').first
    if male_button.count() > 0:
        male_button.click()
        page.wait_for_load_state('networkidle')
        print("  → Sex: Male")
    
    # Step 6: Body map - Chest
    print("\n[STEP 6] Body map: Chest...")
    time.sleep(0.5)
    
    chest_button = page.locator('button:has-text("Chest")').first
    if chest_button.count() > 0:
        chest_button.click()
        print("  → Clicked: Chest")
        time.sleep(0.3)
        
        continue_btn = page.locator('button:has-text("Continue"), button[type="submit"]')
        if continue_btn.count() > 0:
            continue_btn.click()
            page.wait_for_load_state('networkidle')
    
    # Step 7: Symptoms
    print("\n[STEP 7] Symptoms: 'sharp chest pain'...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        textarea.fill('sharp chest pain')
        print("  → Typed: sharp chest pain")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 8: PMH
    print("\n[STEP 8] PMH: 'diabetes, high blood pressure'...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        textarea.fill('diabetes, high blood pressure')
        print("  → Typed: diabetes, high blood pressure")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 9: ZIP CODE QUESTION
    print("\n[STEP 9] Looking for ZIP CODE question...")
    time.sleep(0.5)
    
    # Check if we're on zip code question
    page_content = page.content()
    
    if 'zip' in page_content.lower() or 'postal' in page_content.lower():
        print("  ✓ ZIP CODE question found")
        
        # Check for "Skip this step" option
        skip_button = page.locator('button:has-text("Skip"), a:has-text("Skip")')
        if skip_button.count() > 0:
            print("  ✓ 'Skip this step' option found")
        
        # Enter zip code
        zip_input = page.locator('input[type="text"], input[name="answer"]')
        if zip_input.count() > 0:
            zip_input.fill('10001')
            print("  → Typed: 10001")
            page.locator('button[type="submit"]').click()
            page.wait_for_load_state('networkidle')
    else:
        print("  ⚠️  ZIP CODE question not found")
    
    # Step 10: Follow-up questions with concerning answers
    print("\n[STEP 10] Answering follow-ups with concerning answers...")
    
    question_count = 0
    max_questions = 20
    
    while question_count < max_questions:
        time.sleep(0.3)
        
        if '/results' in page.url:
            print(f"  ✓ Reached results after {question_count} questions")
            break
        
        try:
            if page.locator('button[name="answer"]').count() > 0:
                buttons = page.locator('button[name="answer"]').all()
                
                # Try to find concerning answers
                clicked = False
                for btn in buttons:
                    btn_text = btn.text_content().strip().lower()
                    if any(word in btn_text for word in ['pressure', 'yes', 'severe', 'sudden', 'left arm', 'worse']):
                        btn.click()
                        clicked = True
                        break
                
                if not clicked:
                    buttons[0].click()
            
            page.wait_for_load_state('networkidle')
            question_count += 1
            
        except:
            break
    
    # Step 11: Analyze results page
    print("\n[STEP 11] Analyzing results page...")
    time.sleep(0.5)
    
    page_content = page.content()
    
    # Check for personalization
    if 'John' in page_content:
        print("  ✓ Personalization: 'John' found")
    
    # Check for "Show This to the Triage Nurse" card
    if 'Show This to the Triage Nurse' in page_content or 'triage nurse' in page_content.lower():
        print("  ✓ 'Show This to the Triage Nurse' card found")
    else:
        print("  ⚠️  Triage nurse card not found")
    
    # Check for "Nearby Emergency Departments"
    if 'Nearby Emergency' in page_content or 'nearby' in page_content.lower():
        print("  ✓ 'Nearby Emergency Departments' section found")
    else:
        print("  ⚠️  Nearby facilities section not found")
    
    # Check for Google Maps link
    if 'Google Maps' in page_content or 'maps.google' in page_content:
        print("  ✓ Google Maps link found")
    else:
        print("  ⚠️  Google Maps link not found")
    
    # Check for escalation section
    if 'If This Happens' in page_content:
        print("  ✓ Escalation section found")
    
    # Take screenshot
    page.screenshot(path='screenshots/final_test1_chest_pain_results.png', full_page=True)
    print("\n  📸 Screenshot saved: final_test1_chest_pain_results.png")

def test_scenario_2_confused_person(page):
    """Test 2: Mental status - confused person."""
    
    print("\n" + "=" * 70)
    print("TEST 2: MENTAL STATUS - CONFUSED PERSON")
    print("=" * 70)
    
    # Step 12: Start Over
    print("\n[STEP 12] Starting over...")
    start_over = page.locator('a:has-text("Start Over"), a[href="/restart"], a[href="/"]').first
    if start_over.count() > 0:
        start_over.click()
        page.wait_for_load_state('networkidle')
        print("✓ Returned to homepage")
    
    # Accept disclaimer
    print("\n[STEP 13] Accepting disclaimer...")
    consent_checkbox = page.locator('input[type="checkbox"]#consent')
    consent_checkbox.check()
    time.sleep(0.3)
    get_started = page.locator('button:has-text("Get Started"), button[type="submit"]')
    get_started.first.click()
    page.wait_for_load_state('networkidle')
    
    # Name
    print("\n[STEP 14] Name: Maria...")
    time.sleep(0.5)
    name_input = page.locator('input[type="text"], input[name="answer"]').first
    if name_input.count() > 0:
        name_input.fill('Maria')
        print("  → Typed: Maria")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 15: Click confused option
    print("\n[STEP 15] Clicking 'confused, disoriented, or not making sense'...")
    time.sleep(0.5)
    
    # Find the confused option (should be 3rd or 4th)
    all_buttons = page.locator('button[name="answer"], button[type="button"]').all()
    
    confused_clicked = False
    for btn in all_buttons:
        btn_text = btn.text_content().strip().lower()
        if 'confused' in btn_text or 'disoriented' in btn_text or 'not making sense' in btn_text:
            print(f"  → Clicking: {btn.text_content().strip()[:50]}")
            btn.click()
            page.wait_for_load_state('networkidle')
            confused_clicked = True
            break
    
    if not confused_clicked:
        print("  ⚠️  Could not find confused option")
    
    # Step 16: Check for immediate redirect
    print("\n[STEP 16] Checking for redirect...")
    time.sleep(0.5)
    
    if '/results' in page.url:
        print("  ✓ IMMEDIATELY redirected to results")
        
        page_content = page.content()
        
        # Check for red flag about confusion/altered mental status
        if 'Confusion' in page_content or 'Altered Mental Status' in page_content:
            print("  ✓ Red flag about 'Confusion / Altered Mental Status' found")
        
        # Check for stroke/infection mention
        if 'stroke' in page_content.lower() or 'infection' in page_content.lower():
            print("  ✓ Message mentions stroke/infection")
        
        # Take screenshot
        page.screenshot(path='screenshots/final_test2_confused_results.png', full_page=True)
        print("\n  📸 Screenshot saved: final_test2_confused_results.png")
    else:
        print("  ✗ Did NOT immediately redirect")

def test_scenario_3_parent_child_low_risk(page):
    """Test 3: Parent filling out for child with low-risk."""
    
    print("\n" + "=" * 70)
    print("TEST 3: PARENT/CHILD - LOW-RISK HEADACHE")
    print("=" * 70)
    
    # Step 18: Start Over
    print("\n[STEP 18] Starting over...")
    start_over = page.locator('a:has-text("Start Over"), a[href="/restart"], a[href="/"]').first
    if start_over.count() > 0:
        start_over.click()
        page.wait_for_load_state('networkidle')
        print("✓ Returned to homepage")
    
    # Accept disclaimer
    print("\n[STEP 19] Accepting disclaimer...")
    consent_checkbox = page.locator('input[type="checkbox"]#consent')
    consent_checkbox.check()
    time.sleep(0.3)
    get_started = page.locator('button:has-text("Get Started"), button[type="submit"]')
    get_started.first.click()
    page.wait_for_load_state('networkidle')
    
    # Name
    print("\n[STEP 20] Name: Emma...")
    time.sleep(0.5)
    name_input = page.locator('input[type="text"], input[name="answer"]').first
    if name_input.count() > 0:
        name_input.fill('Emma')
        print("  → Typed: Emma")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 21: Click parent/guardian option
    print("\n[STEP 21] Clicking 'parent or guardian' option...")
    time.sleep(0.5)
    
    all_buttons = page.locator('button[name="answer"], button[type="button"]').all()
    
    parent_clicked = False
    for btn in all_buttons:
        btn_text = btn.text_content().strip().lower()
        if 'parent' in btn_text or 'guardian' in btn_text or 'child' in btn_text:
            print(f"  → Clicking: {btn.text_content().strip()[:50]}")
            btn.click()
            page.wait_for_load_state('networkidle')
            parent_clicked = True
            break
    
    if not parent_clicked:
        print("  ⚠️  Could not find parent/guardian option")
    
    # Step 22: Age and Sex
    print("\n[STEP 22] Age: 8, Sex: Female...")
    time.sleep(0.5)
    
    age_input = page.locator('input[type="number"]')
    if age_input.count() > 0:
        age_input.fill('8')
        print("  → Age: 8")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    time.sleep(0.5)
    female_button = page.locator('button[name="answer"][value="female"], button:has-text("Female")').first
    if female_button.count() > 0:
        female_button.click()
        page.wait_for_load_state('networkidle')
        print("  → Sex: Female")
    
    # Step 23: Body map - Head
    print("\n[STEP 23] Body map: Head...")
    time.sleep(0.5)
    
    head_button = page.locator('button:has-text("Head")').first
    if head_button.count() > 0:
        head_button.click()
        print("  → Clicked: Head")
        time.sleep(0.3)
        
        continue_btn = page.locator('button:has-text("Continue"), button[type="submit"]')
        if continue_btn.count() > 0:
            continue_btn.click()
            page.wait_for_load_state('networkidle')
    
    # Step 24: Symptoms
    print("\n[STEP 24] Symptoms: 'headache after school'...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        textarea.fill('headache after school')
        print("  → Typed: headache after school")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 25: PMH
    print("\n[STEP 25] PMH: 'none'...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        textarea.fill('none')
        print("  → Typed: none")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 26: Zip code
    print("\n[STEP 26] Zip code: '90210'...")
    time.sleep(0.5)
    
    zip_input = page.locator('input[type="text"], input[name="answer"]')
    if zip_input.count() > 0:
        zip_input.fill('90210')
        print("  → Typed: 90210")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 27: Follow-ups with LOW-RISK answers
    print("\n[STEP 27] Answering follow-ups with LOW-RISK answers...")
    
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
                emoji_mild.first.click()
                page.wait_for_load_state('networkidle')
                question_count += 1
                continue
            
            if page.locator('button[name="answer"]').count() > 0:
                buttons = page.locator('button[name="answer"]').all()
                
                # Try to find low-risk answers
                clicked = False
                for btn in buttons:
                    btn_text = btn.text_content().strip().lower()
                    if any(word in btn_text for word in ['no', 'slowly', 'mild', 'all over', 'dull', 'yes similar']):
                        btn.click()
                        clicked = True
                        break
                
                if not clicked:
                    # Default to "no"
                    for btn in buttons:
                        if 'no' in btn.text_content().strip().lower():
                            btn.click()
                            clicked = True
                            break
                    
                    if not clicked:
                        buttons[0].click()
            
            page.wait_for_load_state('networkidle')
            question_count += 1
            
        except:
            break
    
    # Step 28: Analyze results
    print("\n[STEP 28] Analyzing results page...")
    time.sleep(0.5)
    
    page_content = page.content()
    
    # Check for low-risk recommendation
    if 'Likely Okay' in page_content or "You're Okay" in page_content:
        print("  ✓ Low-risk recommendation found")
    elif 'Emergency' in page_content:
        print("  ⚠️  Emergency recommendation (expected low-risk)")
    
    # Check for "When in doubt" message
    if 'when in doubt' in page_content.lower() or 'conservative' in page_content.lower():
        print("  ✓ 'When in doubt' conservative message found")
    else:
        print("  ⚠️  Conservative message not found")
    
    # Take screenshot
    page.screenshot(path='screenshots/final_test3_child_results.png', full_page=True)
    print("\n  📸 Screenshot saved: final_test3_child_results.png")

def main():
    """Run all three tests."""
    
    print("=" * 70)
    print("THREE FINAL SCENARIOS TEST")
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 900})
        page = context.new_page()
        
        try:
            # Test 1
            test_scenario_1_chest_pain_with_zip(page)
            
            time.sleep(2)
            
            # Test 2
            test_scenario_2_confused_person(page)
            
            time.sleep(2)
            
            # Test 3
            test_scenario_3_parent_child_low_risk(page)
            
            print("\n" + "=" * 70)
            print("ALL TESTS COMPLETE")
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
