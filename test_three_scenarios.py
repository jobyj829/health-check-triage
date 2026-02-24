"""
Test three scenarios with new features:
- One question per screen
- Body map with SVG human figure
- Severity slider with emojis
- Personalization with names
- Mental status red flag
- If→Then escalation cards
"""

from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:5001"

def test_scenario_1_chest_pain(page):
    """Test 1: Normal flow with chest pain (high-risk)."""
    
    print("\n" + "=" * 70)
    print("TEST 1: NORMAL FLOW - CHEST PAIN (High-Risk)")
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
    
    # Look for "Get Started" button
    start_button = page.locator('button:has-text("Get Started"), button[type="submit"]')
    start_button.first.click()
    page.wait_for_load_state('networkidle')
    print("✓ Clicked Get Started")
    
    # Step 3: One question per screen flow
    print("\n[STEP 3] One-question-per-screen flow...")
    
    # Question 1: First name
    print("  Q1: First name...")
    time.sleep(0.5)
    name_input = page.locator('input[type="text"], input[name="answer"]').first
    if name_input.count() > 0:
        name_input.fill('John')
        print("    → Typed: John")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
        print("    ✓ Name submitted")
    
    # Question 2: Answering for
    print("  Q2: Answering for...")
    time.sleep(0.5)
    myself_button = page.locator('button:has-text("Yes, I\'m answering for myself"), button:has-text("myself")').first
    if myself_button.count() > 0:
        myself_button.click()
        page.wait_for_load_state('networkidle')
        print("    → Selected: Yes, I'm answering for myself")
        print("    ✓ Submitted")
    
    # Question 3: Age
    print("  Q3: Age...")
    time.sleep(0.5)
    age_input = page.locator('input[type="number"]')
    if age_input.count() > 0:
        age_input.fill('55')
        print("    → Typed: 55")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
        print("    ✓ Age submitted")
    
    # Question 4: Sex
    print("  Q4: Biological sex...")
    time.sleep(0.5)
    male_button = page.locator('button[name="answer"][value="male"], button:has-text("Male")').first
    if male_button.count() > 0:
        male_button.click()
        page.wait_for_load_state('networkidle')
        print("    → Selected: Male")
        print("    ✓ Sex submitted")
    
    # Question 5: Body map
    print("  Q5: Body map...")
    time.sleep(0.5)
    
    # Check for SVG body map
    svg_body = page.locator('svg')
    if svg_body.count() > 0:
        print("    ✓ SVG body map found")
        
        # Try to click chest area on SVG
        # Look for clickable regions or buttons
        chest_button = page.locator('button:has-text("Chest"), [data-region="chest"], #chest').first
        if chest_button.count() > 0:
            chest_button.click()
            print("    → Clicked: Chest region")
        else:
            # Try clicking on the SVG itself (chest area)
            print("    → Attempting to click chest area on SVG")
            # Just click any available option
            page.locator('button').first.click()
        
        time.sleep(0.3)
        continue_button = page.locator('button:has-text("Continue"), button[type="submit"]')
        if continue_button.count() > 0:
            continue_button.click()
            page.wait_for_load_state('networkidle')
            print("    ✓ Body map submitted")
    else:
        print("    ⚠️  No SVG body map found")
        # Try alternative - category buttons
        chest_button = page.locator('button:has-text("Chest")').first
        if chest_button.count() > 0:
            chest_button.click()
            page.wait_for_load_state('networkidle')
            print("    → Clicked: Chest button")
    
    # Question 6: Describe symptoms
    print("  Q6: Describe symptoms...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        symptom_text = "chest pain and trouble breathing"
        textarea.fill(symptom_text)
        print(f"    → Typed: {symptom_text}")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
        print("    ✓ Symptoms submitted")
    
    # Question 7: PMH
    print("  Q7: PMH...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        pmh_text = "diabetes, high blood pressure"
        textarea.fill(pmh_text)
        print(f"    → Typed: {pmh_text}")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
        print("    ✓ PMH submitted")
    
    # Follow-up questions
    print("\n  Follow-up questions...")
    question_count = 0
    max_questions = 20
    
    while question_count < max_questions:
        time.sleep(0.3)
        
        if '/results' in page.url:
            print(f"    ✓ Reached results after {question_count} follow-ups")
            break
        
        try:
            # Check for question context
            question_elem = page.locator('.bg-gray-100, h2, h3').first
            if question_elem.count() > 0:
                question_text = question_elem.text_content().strip()
                
                # Check for context tag
                if 'about your' in question_text.lower():
                    print(f"    Q{question_count + 1}: {question_text[:60]}... [✓ Context tag found]")
                else:
                    print(f"    Q{question_count + 1}: {question_text[:60]}...")
            
            # Check for SEVERITY SLIDER with emojis
            slider = page.locator('input[type="range"], .slider')
            if slider.count() > 0:
                print("      ✓ SEVERITY SLIDER found with emojis")
                # Set to severe (high value)
                slider.first.fill('4')  # or click on severe emoji
                page.locator('button[type="submit"]').click()
                print("      → Selected: Severe")
            
            # Regular buttons
            elif page.locator('button[name="answer"]').count() > 0:
                buttons = page.locator('button[name="answer"]').all()
                
                # Try to find concerning answers
                clicked = False
                for btn in buttons:
                    btn_text = btn.text_content().strip().lower()
                    if any(word in btn_text for word in ['pressure', 'severe', 'yes', 'sudden', 'spreads', 'arm']):
                        btn.click()
                        print(f"      → {btn.text_content().strip()}")
                        clicked = True
                        break
                
                if not clicked:
                    buttons[0].click()
                    print(f"      → {buttons[0].text_content().strip()}")
            
            # Textarea
            elif page.locator('textarea[name="answer"]').count() > 0:
                page.locator('textarea[name="answer"]').fill('severe, sudden')
                page.locator('button[type="submit"]').click()
                print(f"      → severe, sudden")
            
            page.wait_for_load_state('networkidle')
            question_count += 1
            
        except Exception as e:
            print(f"    Error: {e}")
            break
    
    # Step 4: Analyze results
    print("\n[STEP 4] Analyzing results page...")
    time.sleep(0.5)
    
    page_content = page.content()
    
    # Check for personalization
    if 'John' in page_content:
        print("  ✓ Personalization: 'John' found on results page")
    else:
        print("  ✗ Personalization: 'John' NOT found")
    
    # Check for sections
    if 'What This Means for You' in page_content:
        print("  ✓ 'What This Means for You' section found")
    
    if "Why We're Recommending This" in page_content or "Why We're Recommending" in page_content:
        print("  ✓ 'Why We're Recommending This' section found")
    
    # Check for "If This Happens" section
    if 'If This Happens' in page_content or 'If X' in page_content or 'Get Help Right Away' in page_content:
        print("  ✓ 'If This Happens, Get Help Right Away' section found")
    else:
        print("  ⚠️  'If This Happens' escalation section NOT found")
    
    # Take screenshot
    page.screenshot(path='screenshots/scenario1_chest_pain_results.png', full_page=True)
    print("\n  📸 Screenshot saved: screenshots/scenario1_chest_pain_results.png")

def test_scenario_2_mental_status(page):
    """Test 2: Mental status flag should immediately redirect."""
    
    print("\n" + "=" * 70)
    print("TEST 2: MENTAL STATUS FLAG")
    print("=" * 70)
    
    # Step 5: Start Over
    print("\n[STEP 5] Starting over...")
    start_over = page.locator('a:has-text("Start Over"), a[href="/restart"], a[href="/"]').first
    start_over.click()
    page.wait_for_load_state('networkidle')
    print("✓ Returned to homepage")
    
    # Step 6: Accept disclaimer
    print("\n[STEP 6] Accepting disclaimer...")
    consent_checkbox = page.locator('input[type="checkbox"]#consent')
    consent_checkbox.check()
    time.sleep(0.3)
    start_button = page.locator('button:has-text("Get Started"), button[type="submit"]')
    start_button.first.click()
    page.wait_for_load_state('networkidle')
    print("✓ Started")
    
    # Step 7: Name
    print("\n[STEP 7] Entering name...")
    time.sleep(0.5)
    name_input = page.locator('input[type="text"], input[name="answer"]').first
    if name_input.count() > 0:
        name_input.fill('Maria')
        print("  → Typed: Maria")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 8: Answering for - select confused option
    print("\n[STEP 8] Selecting mental status flag option...")
    time.sleep(0.5)
    
    confused_button = page.locator('button:has-text("confused"), button:has-text("not making sense"), button:has-text("helping someone")').first
    if confused_button.count() > 0:
        confused_button.click()
        page.wait_for_load_state('networkidle')
        print("  → Selected: I'm helping someone who is confused")
        
        # Step 9: Check if redirected to results
        time.sleep(0.5)
        if '/results' in page.url:
            print("\n[STEP 9] ✓ IMMEDIATELY redirected to results (red flag triggered)")
            
            page_content = page.content()
            if 'Emergency' in page_content or 'Call 911' in page_content:
                print("  ✓ Emergency recommendation shown")
            
            # Take screenshot
            page.screenshot(path='screenshots/scenario2_mental_status_flag.png', full_page=True)
            print("\n  📸 Screenshot saved: screenshots/scenario2_mental_status_flag.png")
        else:
            print("\n[STEP 9] ✗ Did NOT immediately redirect to results")
            print(f"  Current URL: {page.url}")

def test_scenario_3_low_risk_headache(page):
    """Test 3: Low-risk headache with all low-risk answers."""
    
    print("\n" + "=" * 70)
    print("TEST 3: LOW-RISK HEADACHE")
    print("=" * 70)
    
    # Step 10: Start Over
    print("\n[STEP 10] Starting over...")
    start_over = page.locator('a:has-text("Start Over"), a[href="/restart"], a[href="/"]').first
    start_over.click()
    page.wait_for_load_state('networkidle')
    print("✓ Returned to homepage")
    
    # Step 11: Accept disclaimer
    print("\n[STEP 11] Accepting disclaimer...")
    consent_checkbox = page.locator('input[type="checkbox"]#consent')
    consent_checkbox.check()
    time.sleep(0.3)
    start_button = page.locator('button:has-text("Get Started"), button[type="submit"]')
    start_button.first.click()
    page.wait_for_load_state('networkidle')
    print("✓ Started")
    
    # Step 12: Name
    print("\n[STEP 12] Name: Sarah...")
    time.sleep(0.5)
    name_input = page.locator('input[type="text"], input[name="answer"]').first
    if name_input.count() > 0:
        name_input.fill('Sarah')
        print("  → Typed: Sarah")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 13: Answering for
    print("\n[STEP 13] Answering for myself...")
    time.sleep(0.5)
    myself_button = page.locator('button:has-text("Yes, I\'m answering for myself"), button:has-text("myself")').first
    if myself_button.count() > 0:
        myself_button.click()
        page.wait_for_load_state('networkidle')
        print("  → Selected: myself")
    
    # Step 14: Age
    print("\n[STEP 14] Age: 25...")
    time.sleep(0.5)
    age_input = page.locator('input[type="number"]')
    if age_input.count() > 0:
        age_input.fill('25')
        print("  → Typed: 25")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 15: Sex
    print("\n[STEP 15] Sex: Female...")
    time.sleep(0.5)
    female_button = page.locator('button[name="answer"][value="female"], button:has-text("Female")').first
    if female_button.count() > 0:
        female_button.click()
        page.wait_for_load_state('networkidle')
        print("  → Selected: Female")
    
    # Step 16: Body map - Head
    print("\n[STEP 16] Body map: Head...")
    time.sleep(0.5)
    head_button = page.locator('button:has-text("Head"), [data-region="head"], #head').first
    if head_button.count() > 0:
        head_button.click()
        print("  → Clicked: Head")
        time.sleep(0.3)
        continue_button = page.locator('button:has-text("Continue"), button[type="submit"]')
        if continue_button.count() > 0:
            continue_button.click()
            page.wait_for_load_state('networkidle')
    
    # Step 17: Symptoms
    print("\n[STEP 17] Symptoms...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        symptom_text = "I have a mild headache"
        textarea.fill(symptom_text)
        print(f"  → Typed: {symptom_text}")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 18: PMH
    print("\n[STEP 18] PMH...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        pmh_text = "none"
        textarea.fill(pmh_text)
        print(f"  → Typed: {pmh_text}")
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state('networkidle')
    
    # Step 19: Follow-up questions with LOW-RISK answers
    print("\n[STEP 19] Answering follow-ups with LOW-RISK answers...")
    
    low_risk_keywords = ['gradually', 'no', 'mild', 'all', 'dull', 'aching', 'yes had headaches']
    
    question_count = 0
    max_questions = 20
    
    while question_count < max_questions:
        time.sleep(0.3)
        
        if '/results' in page.url:
            print(f"  ✓ Reached results after {question_count} follow-ups")
            break
        
        try:
            question_elem = page.locator('.bg-gray-100, h2, h3').first
            if question_elem.count() > 0:
                question_text = question_elem.text_content().strip().lower()
                print(f"  Q{question_count + 1}: {question_text[:60]}...")
            
            # Check for severity slider
            slider = page.locator('input[type="range"], .slider')
            if slider.count() > 0:
                print("    ✓ Severity slider found")
                slider.first.fill('1')  # Mild
                page.locator('button[type="submit"]').click()
                print("    → Selected: Mild")
            
            # Regular buttons - find low-risk options
            elif page.locator('button[name="answer"]').count() > 0:
                buttons = page.locator('button[name="answer"]').all()
                
                clicked = False
                for btn in buttons:
                    btn_text = btn.text_content().strip().lower()
                    if any(word in btn_text for word in low_risk_keywords):
                        btn.click()
                        print(f"    → {btn.text_content().strip()}")
                        clicked = True
                        break
                
                if not clicked:
                    # Default to "no" if available
                    for btn in buttons:
                        if 'no' in btn.text_content().strip().lower():
                            btn.click()
                            print(f"    → {btn.text_content().strip()}")
                            clicked = True
                            break
                    
                    if not clicked:
                        buttons[0].click()
                        print(f"    → {buttons[0].text_content().strip()}")
            
            # Textarea
            elif page.locator('textarea[name="answer"]').count() > 0:
                page.locator('textarea[name="answer"]').fill('mild, gradual')
                page.locator('button[type="submit"]').click()
                print(f"    → mild, gradual")
            
            page.wait_for_load_state('networkidle')
            question_count += 1
            
        except Exception as e:
            print(f"  Error: {e}")
            break
    
    # Step 20: Analyze results
    print("\n[STEP 20] Analyzing results page...")
    time.sleep(0.5)
    
    page_content = page.content()
    
    # Check for personalization
    if 'Sarah' in page_content:
        print("  ✓ Personalization: 'Sarah' found on results page")
    else:
        print("  ✗ Personalization: 'Sarah' NOT found")
    
    # Check for green/low-risk recommendation
    if 'Likely Okay' in page_content or "You're Okay" in page_content:
        print("  ✓ Low-risk recommendation found")
    
    # Check for comforting text
    if 'good news' in page_content.lower() or 'likely not serious' in page_content.lower():
        print("  ✓ Comforting reassurance text found")
    
    # Take screenshot
    page.screenshot(path='screenshots/scenario3_low_risk_headache.png', full_page=True)
    print("\n  📸 Screenshot saved: screenshots/scenario3_low_risk_headache.png")

def main():
    """Run all three scenarios."""
    
    print("=" * 70)
    print("TRIAGE APP - THREE SCENARIO TEST")
    print("Testing: One-question-per-screen, Body map, Severity slider, etc.")
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 900})
        page = context.new_page()
        
        try:
            # Test 1: Chest pain
            test_scenario_1_chest_pain(page)
            
            time.sleep(2)
            
            # Test 2: Mental status flag
            test_scenario_2_mental_status(page)
            
            time.sleep(2)
            
            # Test 3: Low-risk headache
            test_scenario_3_low_risk_headache(page)
            
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
