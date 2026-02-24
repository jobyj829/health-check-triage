"""
Test new features: 4 percentage bars, reassurance text, and tailored watch-for signs.
"""

from playwright.sync_api import sync_playwright
import time
import re

BASE_URL = "http://localhost:5001"

def extract_results_data(page):
    """Extract all key data from results page."""
    
    page_content = page.content()
    
    # 1. Extract "What This Means for You" reassurance text
    print("\n  📝 'What This Means for You' Section:")
    reassurance_text = None
    
    # Look for this specific section
    try:
        section_elem = page.locator('text=/What This Means for You/i').first
        if section_elem.count() > 0:
            # Get parent container
            parent = section_elem.locator('xpath=ancestor::div[contains(@class, "bg-") or position()=2]').first
            if parent.count() > 0:
                reassurance_text = parent.text_content()
                # Clean up and extract just the paragraph
                lines = [l.strip() for l in reassurance_text.split('\n') if l.strip()]
                # Find the actual reassurance paragraph (not the heading)
                for line in lines:
                    if len(line) > 50 and 'What This Means' not in line:
                        print(f"    {line[:200]}...")
                        reassurance_text = line
                        break
    except Exception as e:
        print(f"    Could not extract reassurance text: {e}")
    
    # 2. Extract FOUR percentage bars
    print("\n  📊 Risk Percentages (looking for FOUR bars):")
    
    risk_labels = [
        "Likelihood that something serious is happening",
        "Likelihood of needing immediate medical attention",
        "Likelihood of hospitalization", 
        "Likelihood of death"
    ]
    
    risk_data = {}
    for label in risk_labels:
        try:
            label_elem = page.locator(f'text=/{label}/i').first
            if label_elem.count() > 0:
                parent = label_elem.locator('xpath=..')
                parent_text = parent.text_content()
                
                # Extract percentage
                matches = re.findall(r'(\d+\.?\d*)%', parent_text)
                if matches:
                    percentage = matches[0] + '%'
                    print(f"    ✓ {label}: {percentage}")
                    risk_data[label] = percentage
            else:
                print(f"    ✗ NOT found: {label}")
        except:
            pass
    
    # 3. Extract "Watch Out For These Signs" section
    print("\n  ⚠️  'Watch Out For These Signs' Section:")
    watch_signs = []
    
    try:
        section_elem = page.locator('text=/Watch Out For These Signs/i, text=/Watch For These Signs/i').first
        if section_elem.count() > 0:
            # Get parent container
            parent = section_elem.locator('xpath=ancestor::div[contains(@class, "bg-") or position()=3]').first
            if parent.count() > 0:
                # Find all list items
                list_items = parent.locator('li, p').all()
                for item in list_items[:8]:
                    text = item.text_content().strip()
                    if len(text) > 10 and 'Watch' not in text:
                        watch_signs.append(text)
                        print(f"    • {text[:80]}")
    except Exception as e:
        print(f"    Could not extract watch signs: {e}")
    
    return reassurance_text, risk_data, watch_signs

def test_high_risk_chest_pain(page):
    """Test 1: High-risk chest pain."""
    
    print("\n" + "=" * 70)
    print("TEST 1: HIGH-RISK (Chest Pain + Shortness of Breath)")
    print("=" * 70)
    
    # Steps 1-2: Homepage and disclaimer
    print("\n[STEPS 1-2] Homepage and disclaimer...")
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    
    consent_checkbox = page.locator('input[type="checkbox"]#consent')
    consent_checkbox.check()
    start_button = page.locator('button[type="submit"]')
    start_button.click()
    page.wait_for_load_state('networkidle')
    print("✓ Started interview")
    
    # Step 3: Demographics
    print("\n[STEP 3] Demographics...")
    page.wait_for_selector('input[type="number"]', timeout=5000)
    age_input = page.locator('input[type="number"]')
    age_input.fill('60')
    page.locator('button[type="submit"]').click()
    page.wait_for_load_state('networkidle')
    print("  Age: 60")
    
    time.sleep(0.5)
    male_button = page.locator('button[name="answer"][value="male"]')
    male_button.click()
    page.wait_for_load_state('networkidle')
    print("  Sex: Male")
    print("✓ Demographics submitted")
    
    # Step 4: Symptoms
    print("\n[STEP 4] Symptoms...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        symptom_text = "my chest hurts and I feel short of breath"
        textarea.fill(symptom_text)
        print(f"  Typed: '{symptom_text}'")
        
        time.sleep(0.3)
        submit_button = page.locator('button[type="submit"]')
        submit_button.click()
        page.wait_for_load_state('networkidle')
        print("✓ Symptoms submitted")
    
    # Step 5: Continue to results
    print("\n[STEP 5] Continuing to results...")
    time.sleep(0.5)
    
    if '/results' in page.url:
        print("✓ Red flag triggered - went directly to results")
    else:
        print("  Answering any remaining questions...")
        attempts = 0
        while '/results' not in page.url and attempts < 5:
            try:
                if page.locator('button[name="answer"]').count() > 0:
                    page.locator('button[name="answer"]').first.click()
                elif page.locator('textarea[name="answer"]').count() > 0:
                    page.locator('textarea[name="answer"]').fill('none')
                    page.locator('button[type="submit"]').click()
                elif page.locator('button[type="submit"]').count() > 0:
                    page.locator('button[type="submit"]').click()
                else:
                    break
                
                page.wait_for_load_state('networkidle')
                attempts += 1
            except:
                break
        
        print("✓ Reached results page")
    
    # Step 6: Analyze results
    print("\n[STEP 6] Analyzing results page...")
    time.sleep(0.5)
    
    # Get recommendation
    headings = page.locator('h1, h2, h3').all()
    for heading in headings:
        text = heading.text_content().strip()
        if any(word in text.lower() for word in ['emergency', 'urgent', 'primary', 'okay', 'call']):
            print(f"\n  📋 RECOMMENDATION: {text}")
            break
    
    # Extract all data
    reassurance, risks, watch_signs = extract_results_data(page)
    
    # Take screenshot
    page.screenshot(path='screenshots/new_test1_high_risk.png', full_page=True)
    print(f"\n  📸 Full page screenshot saved: screenshots/new_test1_high_risk.png")
    
    return reassurance, risks, watch_signs

def test_low_risk_headache(page):
    """Test 2: Low-risk headache with all low-risk answers."""
    
    print("\n" + "=" * 70)
    print("TEST 2: LOW-RISK (Simple Headache)")
    print("=" * 70)
    
    # Step 7: Start Over
    print("\n[STEP 7] Starting over...")
    start_over = page.locator('a[href="/restart"], a[href="/"]').first
    start_over.click()
    page.wait_for_load_state('networkidle')
    print("✓ Returned to homepage")
    
    # Step 8: Accept disclaimer
    print("\n[STEP 8] Accepting disclaimer...")
    consent_checkbox = page.locator('input[type="checkbox"]#consent')
    consent_checkbox.check()
    start_button = page.locator('button[type="submit"]')
    start_button.click()
    page.wait_for_load_state('networkidle')
    print("✓ Started interview")
    
    # Step 9: Demographics
    print("\n[STEP 9] Demographics...")
    page.wait_for_selector('input[type="number"]', timeout=5000)
    age_input = page.locator('input[type="number"]')
    age_input.fill('28')
    page.locator('button[type="submit"]').click()
    page.wait_for_load_state('networkidle')
    print("  Age: 28")
    
    time.sleep(0.5)
    female_button = page.locator('button[name="answer"][value="female"]')
    female_button.click()
    page.wait_for_load_state('networkidle')
    print("  Sex: Female")
    print("✓ Demographics submitted")
    
    # Step 10: Symptoms
    print("\n[STEP 10] Symptoms...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        symptom_text = "I have a headache"
        textarea.fill(symptom_text)
        print(f"  Typed: '{symptom_text}'")
        
        time.sleep(0.3)
        submit_button = page.locator('button[type="submit"]')
        submit_button.click()
        page.wait_for_load_state('networkidle')
        print("✓ Symptoms submitted")
    
    # Step 11: PMH
    print("\n[STEP 11] PMH...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        pmh_text = "none"
        textarea.fill(pmh_text)
        print(f"  Typed: '{pmh_text}'")
        
        time.sleep(0.3)
        submit_button = page.locator('button[type="submit"]')
        submit_button.click()
        page.wait_for_load_state('networkidle')
        print("✓ PMH submitted")
    
    # Step 12: Answer ALL follow-up questions with LOW RISK answers
    print("\n[STEP 12] Answering follow-up questions with LOW RISK answers...")
    
    # Mapping of question keywords to low-risk answers
    low_risk_map = {
        'gradually': ['gradually', 'slowly', 'built up slowly'],
        'worst': ['no'],
        '0 = no pain': ['3', '2', '1'],
        'where': ['all', 'both', 'all over'],
        'feel like': ['dull', 'aching', 'pressure'],
        'stiff': ['no'],
        'fever': ['no'],
        'vision': ['no'],
        'weakness': ['no'],
        'speaking': ['no'],
        'confused': ['no'],
        'nausea': ['no'],
        'before': ['yes'],
        'injury': ['no'],
        'thinners': ['no']
    }
    
    question_count = 0
    max_questions = 20
    
    while question_count < max_questions:
        time.sleep(0.3)
        
        if '/results' in page.url:
            print(f"  ✓ Reached results after {question_count} questions")
            break
        
        try:
            question_elem = page.locator('.bg-gray-100.rounded-2xl').last
            question_text = question_elem.text_content().strip().lower()
            
            print(f"  Q{question_count + 1}: {question_text[:60]}...")
            
            # Single choice buttons
            if page.locator('button[name="answer"]').count() > 0:
                buttons = page.locator('button[name="answer"]').all()
                
                clicked = False
                # Try to match low risk answers
                for keyword, low_risk_options in low_risk_map.items():
                    if keyword in question_text:
                        for btn in buttons:
                            btn_text = btn.text_content().strip().lower()
                            if any(opt in btn_text for opt in low_risk_options):
                                btn.click()
                                print(f"       → {btn.text_content().strip()}")
                                clicked = True
                                break
                        if clicked:
                            break
                
                if not clicked:
                    # Default: try to find "no" or first option
                    for btn in buttons:
                        if 'no' in btn.text_content().strip().lower():
                            btn.click()
                            print(f"       → {btn.text_content().strip()}")
                            clicked = True
                            break
                    
                    if not clicked:
                        buttons[0].click()
                        print(f"       → {buttons[0].text_content().strip()}")
            
            elif page.locator('textarea[name="answer"]').count() > 0:
                page.locator('textarea[name="answer"]').fill('mild, gradual')
                page.locator('button[type="submit"]').click()
                print(f"       → mild, gradual")
            
            elif page.locator('input[type="number"]').count() > 0:
                page.locator('input[type="number"]').fill('3')
                page.locator('button[type="submit"]').click()
                print(f"       → 3")
            
            page.wait_for_load_state('networkidle')
            question_count += 1
            
        except Exception as e:
            print(f"  Error: {e}")
            break
    
    print(f"✓ Answered {question_count} follow-up questions with low-risk answers")
    
    # Step 13: Analyze results
    print("\n[STEP 13] Analyzing results page...")
    time.sleep(0.5)
    
    # Get recommendation
    headings = page.locator('h1, h2, h3').all()
    for heading in headings:
        text = heading.text_content().strip()
        if any(word in text.lower() for word in ['emergency', 'urgent', 'primary', 'okay', 'call', 'see', 'likely']):
            print(f"\n  📋 RECOMMENDATION: {text}")
            break
    
    # Extract all data
    reassurance, risks, watch_signs = extract_results_data(page)
    
    # Take screenshot
    page.screenshot(path='screenshots/new_test2_low_risk.png', full_page=True)
    print(f"\n  📸 Full page screenshot saved: screenshots/new_test2_low_risk.png")
    
    return reassurance, risks, watch_signs

def main():
    """Run both tests."""
    
    print("=" * 70)
    print("TRIAGE APP - NEW FEATURES TEST")
    print("Testing: 4 percentage bars, reassurance text, tailored watch signs")
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 900})
        page = context.new_page()
        
        try:
            # Test 1: High risk
            reassurance1, risks1, watch1 = test_high_risk_chest_pain(page)
            
            time.sleep(2)
            
            # Test 2: Low risk
            reassurance2, risks2, watch2 = test_low_risk_headache(page)
            
            # Final summary
            print("\n" + "=" * 70)
            print("FINAL SUMMARY")
            print("=" * 70)
            
            print("\n📝 TEST 1 - 'What This Means for You' (High-Risk):")
            if reassurance1:
                print(f"  {reassurance1[:300]}")
            else:
                print("  ⚠️  Not found")
            
            print("\n📝 TEST 2 - 'What This Means for You' (Low-Risk):")
            if reassurance2:
                print(f"  {reassurance2[:300]}")
            else:
                print("  ⚠️  Not found")
            
            print("\n📊 TEST 1 - Risk Percentages (High-Risk):")
            if risks1:
                for label, value in risks1.items():
                    print(f"  - {label}: {value}")
                print(f"  Total bars found: {len(risks1)}")
            
            print("\n📊 TEST 2 - Risk Percentages (Low-Risk):")
            if risks2:
                for label, value in risks2.items():
                    print(f"  - {label}: {value}")
                print(f"  Total bars found: {len(risks2)}")
            
            print("\n⚠️  TEST 1 - Watch-For Signs (Chest Pain):")
            if watch1:
                print(f"  Found {len(watch1)} signs:")
                for sign in watch1[:5]:
                    print(f"    • {sign[:80]}")
            
            print("\n⚠️  TEST 2 - Watch-For Signs (Headache):")
            if watch2:
                print(f"  Found {len(watch2)} signs:")
                for sign in watch2[:5]:
                    print(f"    • {sign[:80]}")
            
            print("\n✓ TAILORED CONTENT CHECK:")
            if watch1 and watch2:
                # Check if they're different (tailored)
                if watch1 != watch2:
                    print("  ✓ Watch-for signs are DIFFERENT (tailored to symptom)")
                else:
                    print("  ✗ Watch-for signs are the SAME (not tailored)")
            
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
