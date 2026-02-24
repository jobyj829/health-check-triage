"""
Test two scenarios: high-risk (chest pain) and low-risk (headache) to verify percentages.
"""

from playwright.sync_api import sync_playwright
import time
import re

BASE_URL = "http://localhost:5001"

def extract_percentages_and_counts(page):
    """Extract risk percentages and any patient counts from the page."""
    
    page_content = page.content()
    
    # Look for the three risk percentages
    risk_data = {}
    
    risk_labels = [
        "Likelihood of needing immediate medical attention",
        "Likelihood of hospitalization", 
        "Likelihood of death"
    ]
    
    print("\n  📊 RISK PERCENTAGES:")
    for label in risk_labels:
        try:
            # Find the label
            label_elem = page.locator(f'text=/{label}/i').first
            if label_elem.count() > 0:
                # Get parent container
                parent = label_elem.locator('xpath=..')
                parent_text = parent.text_content()
                
                # Extract percentage
                matches = re.findall(r'(\d+\.?\d*)%', parent_text)
                if matches:
                    percentage = matches[0] + '%'
                    print(f"    ✓ {label}: {percentage}")
                    risk_data[label] = percentage
        except:
            pass
    
    # Look for ANY patient count numbers
    print("\n  🔍 CHECKING FOR PATIENT COUNTS:")
    
    # Common patterns for patient counts
    count_patterns = [
        r'(\d{1,3}(?:,\d{3})+)\s+(?:similar\s+)?patients',
        r'(\d{1,3}(?:,\d{3})+)\s+emergency\s+visits',
        r'Based\s+on\s+(?:data\s+from\s+)?(\d{1,3}(?:,\d{3})+)',
        r'(\d{1,3}(?:,\d{3})+)\s+(?:patients|visits|cases)',
    ]
    
    found_counts = []
    for pattern in count_patterns:
        matches = re.findall(pattern, page_content, re.IGNORECASE)
        found_counts.extend(matches)
    
    if found_counts:
        print(f"    ✗ FOUND patient counts: {found_counts}")
    else:
        print(f"    ✓ NO specific patient counts found")
    
    # Look for data source references
    print("\n  📚 DATA SOURCE REFERENCES:")
    
    source_keywords = [
        'published', 'literature', 'research', 'study', 'studies',
        'clinical data', 'medical literature', 'evidence'
    ]
    
    found_sources = []
    for keyword in source_keywords:
        if keyword in page_content.lower():
            # Find context around keyword
            pattern = rf'.{{0,50}}{keyword}.{{0,50}}'
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            if matches:
                found_sources.extend([m.strip() for m in matches[:2]])
    
    if found_sources:
        for source in found_sources[:3]:
            print(f"    - {source[:100]}")
    else:
        print(f"    - No specific source references found")
    
    return risk_data, found_counts, found_sources

def test_high_risk_scenario(page):
    """Test 1: High-risk chest pain + breathing."""
    
    print("\n" + "=" * 70)
    print("TEST 1: HIGH-RISK SCENARIO (Chest Pain + Breathing)")
    print("=" * 70)
    
    # Step 1: Go to homepage
    print("\n[STEP 1] Visiting homepage...")
    page.goto(BASE_URL)
    page.wait_for_load_state('networkidle')
    print("✓ Homepage loaded")
    
    # Step 2: Accept disclaimer
    print("\n[STEP 2] Accepting disclaimer...")
    consent_checkbox = page.locator('input[type="checkbox"]#consent')
    consent_checkbox.check()
    start_button = page.locator('button[type="submit"]')
    start_button.click()
    page.wait_for_load_state('networkidle')
    print("✓ Started interview")
    
    # Step 3: Age and Sex
    print("\n[STEP 3] Entering demographics...")
    page.wait_for_selector('input[type="number"]', timeout=5000)
    age_input = page.locator('input[type="number"]')
    age_input.fill('55')
    page.locator('button[type="submit"]').click()
    page.wait_for_load_state('networkidle')
    print("  Age: 55")
    
    time.sleep(0.5)
    male_button = page.locator('button[name="answer"][value="male"]')
    male_button.click()
    page.wait_for_load_state('networkidle')
    print("  Sex: Male")
    print("✓ Demographics submitted")
    
    # Step 4: Symptoms
    print("\n[STEP 4] Entering symptoms...")
    time.sleep(0.5)
    textarea = page.locator('textarea[name="answer"]')
    if textarea.count() > 0:
        symptom_text = "I have chest pain and I'm having trouble breathing"
        textarea.fill(symptom_text)
        print(f"  Typed: '{symptom_text}'")
        
        time.sleep(0.3)
        submit_button = page.locator('button[type="submit"]')
        submit_button.click()
        page.wait_for_load_state('networkidle')
        print("✓ Symptoms submitted")
    
    # Step 5: Check if we're at results (red flag may trigger)
    print("\n[STEP 5] Checking page...")
    time.sleep(0.5)
    
    if '/results' in page.url:
        print("✓ Red flag triggered - went directly to results")
    else:
        print("  Continuing with interview...")
        # Answer any remaining questions
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
        if any(word in text.lower() for word in ['emergency', 'urgent', 'primary', 'call']):
            print(f"\n  📋 RECOMMENDATION: {text}")
            break
    
    # Extract data
    risk_data, patient_counts, sources = extract_percentages_and_counts(page)
    
    # Take screenshot
    page.screenshot(path='screenshots/test1_high_risk_results.png')
    print(f"\n  📸 Screenshot saved: screenshots/test1_high_risk_results.png")
    
    return risk_data, patient_counts, sources

def test_low_risk_scenario(page):
    """Test 2: Low-risk headache."""
    
    print("\n" + "=" * 70)
    print("TEST 2: LOW-RISK SCENARIO (Simple Headache)")
    print("=" * 70)
    
    # Step 7: Click Start Over
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
    
    # Step 9: Age and Sex
    print("\n[STEP 9] Entering demographics...")
    page.wait_for_selector('input[type="number"]', timeout=5000)
    age_input = page.locator('input[type="number"]')
    age_input.fill('25')
    page.locator('button[type="submit"]').click()
    page.wait_for_load_state('networkidle')
    print("  Age: 25")
    
    time.sleep(0.5)
    female_button = page.locator('button[name="answer"][value="female"]')
    female_button.click()
    page.wait_for_load_state('networkidle')
    print("  Sex: Female")
    print("✓ Demographics submitted")
    
    # Step 10: Symptoms
    print("\n[STEP 10] Entering symptoms...")
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
    print("\n[STEP 11] Entering PMH...")
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
    
    # Step 12: Answer follow-up questions with LOW RISK answers
    print("\n[STEP 12] Answering follow-up questions with LOW RISK answers...")
    
    low_risk_keywords = {
        'gradually': ['gradually', 'slowly', 'built up'],
        'worst': ['no'],
        'pain': ['3', '2', '1', 'mild', '1-3'],
        'side': ['all', 'both'],
        'feel': ['dull', 'aching', 'pressure'],
        'stiff': ['no'],
        'fever': ['no'],
        'vision': ['no'],
        'weakness': ['no'],
        'speaking': ['no'],
        'confused': ['no'],
        'nausea': ['no', 'feeling fine'],
        'before': ['yes', 'had headaches'],
        'injury': ['no'],
        'thinners': ['no', 'not sure']
    }
    
    question_count = 0
    max_questions = 20
    
    while question_count < max_questions:
        time.sleep(0.3)
        
        if '/results' in page.url:
            print(f"  Reached results after {question_count} questions")
            break
        
        try:
            question_elem = page.locator('.bg-gray-100.rounded-2xl').last
            question_text = question_elem.text_content().strip().lower()
            
            print(f"  Q{question_count + 1}: {question_text[:60]}...")
            
            # Check for different input types
            if page.locator('button[name="answer"]').count() > 0:
                # Single choice - find low risk option
                buttons = page.locator('button[name="answer"]').all()
                
                clicked = False
                # Try to match low risk keywords
                for keyword, options in low_risk_keywords.items():
                    if keyword in question_text:
                        for btn in buttons:
                            btn_text = btn.text_content().strip().lower()
                            if any(opt in btn_text for opt in options):
                                btn.click()
                                print(f"       → {btn.text_content().strip()}")
                                clicked = True
                                break
                        if clicked:
                            break
                
                if not clicked:
                    # Default to first option
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
    
    print(f"✓ Answered {question_count} follow-up questions")
    
    # Step 13: Analyze results
    print("\n[STEP 13] Analyzing results page...")
    time.sleep(0.5)
    
    # Get recommendation
    headings = page.locator('h1, h2, h3').all()
    for heading in headings:
        text = heading.text_content().strip()
        if any(word in text.lower() for word in ['emergency', 'urgent', 'primary', 'call', 'see']):
            print(f"\n  📋 RECOMMENDATION: {text}")
            break
    
    # Extract data
    risk_data, patient_counts, sources = extract_percentages_and_counts(page)
    
    # Take screenshot
    page.screenshot(path='screenshots/test2_low_risk_results.png')
    print(f"\n  📸 Screenshot saved: screenshots/test2_low_risk_results.png")
    
    return risk_data, patient_counts, sources

def main():
    """Run both tests."""
    
    print("=" * 70)
    print("TRIAGE APP - TWO SCENARIO COMPARISON TEST")
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            # Test 1: High risk
            risk1, counts1, sources1 = test_high_risk_scenario(page)
            
            time.sleep(2)
            
            # Test 2: Low risk
            risk2, counts2, sources2 = test_low_risk_scenario(page)
            
            # Final comparison
            print("\n" + "=" * 70)
            print("FINAL COMPARISON")
            print("=" * 70)
            
            print("\n📊 TEST 1 (High-Risk: Chest Pain + Breathing):")
            for label, value in risk1.items():
                print(f"  - {label}: {value}")
            
            print("\n📊 TEST 2 (Low-Risk: Simple Headache):")
            for label, value in risk2.items():
                print(f"  - {label}: {value}")
            
            print("\n🔍 PATIENT COUNTS:")
            if counts1 or counts2:
                print(f"  ✗ FOUND patient counts:")
                if counts1:
                    print(f"    Test 1: {counts1}")
                if counts2:
                    print(f"    Test 2: {counts2}")
            else:
                print(f"  ✓ NO specific patient counts found in either test")
            
            print("\n✓ LOGICAL CONSISTENCY CHECK:")
            # Check if percentages make sense
            try:
                if risk1 and risk2:
                    # Extract numeric values
                    def get_value(risk_dict, label):
                        val_str = risk_dict.get(label, '0%').replace('%', '')
                        return float(val_str)
                    
                    # Test 1 checks
                    t1_immediate = get_value(risk1, "Likelihood of needing immediate medical attention")
                    t1_hosp = get_value(risk1, "Likelihood of hospitalization")
                    t1_death = get_value(risk1, "Likelihood of death")
                    
                    # Test 2 checks
                    t2_immediate = get_value(risk2, "Likelihood of needing immediate medical attention")
                    t2_hosp = get_value(risk2, "Likelihood of hospitalization")
                    t2_death = get_value(risk2, "Likelihood of death")
                    
                    print(f"  Test 1: Immediate ({t1_immediate}%) >= Hospitalization ({t1_hosp}%): {t1_immediate >= t1_hosp}")
                    print(f"  Test 2: Immediate ({t2_immediate}%) >= Hospitalization ({t2_hosp}%): {t2_immediate >= t2_hosp}")
                    print(f"  Test 1 > Test 2 (high risk > low risk): {t1_immediate > t2_immediate}")
            except:
                print(f"  Could not parse percentages for comparison")
            
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
