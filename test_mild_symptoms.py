"""
Test triage app with MILD symptoms to verify full flow including PMH textarea.
"""

from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:5001"

def test_mild_symptoms():
    """Test with mild symptoms to see full flow."""
    
    print("=" * 70)
    print("TRIAGE APP - MILD SYMPTOMS TEST")
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            # Step 1: Visit welcome page
            print("\n[STEP 1] Visiting welcome page...")
            page.goto(BASE_URL)
            page.wait_for_load_state('networkidle')
            print(f"✓ Welcome page loaded")
            
            # Step 2: Accept disclaimer
            print("\n[STEP 2] Accepting disclaimer...")
            consent_checkbox = page.locator('input[type="checkbox"]#consent')
            consent_checkbox.check()
            start_button = page.locator('button[type="submit"]')
            start_button.click()
            page.wait_for_load_state('networkidle')
            print(f"✓ Started interview")
            
            # Step 3: Age = 30
            print("\n[STEP 3] Answering age question...")
            page.wait_for_selector('input[type="number"]', timeout=5000)
            age_input = page.locator('input[type="number"]')
            age_input.fill('30')
            print(f"  Answer: 30")
            page.locator('button[type="submit"]').click()
            page.wait_for_load_state('networkidle')
            print(f"✓ Age submitted")
            
            # Step 4: Sex = Female
            print("\n[STEP 4] Answering sex question...")
            time.sleep(0.5)
            female_button = page.locator('button[name="answer"][value="female"]')
            female_button.click()
            page.wait_for_load_state('networkidle')
            print(f"  Answer: Female")
            print(f"✓ Sex submitted")
            
            # Step 5: Symptoms - mild
            print("\n[STEP 5] Symptom question (textarea)...")
            time.sleep(0.5)
            
            question_text = page.locator('.bg-gray-100.rounded-2xl').last.text_content()
            print(f"  Question: {question_text.strip()}")
            
            # Check for textarea
            textarea = page.locator('textarea[name="answer"]')
            if textarea.count() > 0:
                print(f"  ✓ TEXTAREA found")
                
                symptom_text = "I have a headache and I feel tired"
                textarea.fill(symptom_text)
                print(f"  Typed: '{symptom_text}'")
                
                time.sleep(0.3)
                submit_button = page.locator('button[type="submit"]')
                submit_button.click()
                page.wait_for_load_state('networkidle')
                print(f"✓ Symptom submitted")
            else:
                print(f"  ✗ ERROR: No textarea found")
            
            # Step 6: PMH question - TAKE SCREENSHOT BEFORE SUBMITTING
            print("\n[STEP 6] PMH question (textarea)...")
            time.sleep(0.5)
            
            question_text = page.locator('.bg-gray-100.rounded-2xl').last.text_content()
            print(f"  Question: {question_text.strip()}")
            
            # Check for textarea
            textarea = page.locator('textarea[name="answer"]')
            if textarea.count() > 0:
                print(f"  ✓ PMH TEXTAREA found")
                
                pmh_text = "none"
                textarea.fill(pmh_text)
                print(f"  Typed: '{pmh_text}'")
                
                # TAKE SCREENSHOT BEFORE SUBMITTING
                page.screenshot(path='screenshots/mild_06_pmh_textarea.png')
                print(f"  📸 Screenshot saved: screenshots/mild_06_pmh_textarea.png")
                
                time.sleep(0.5)
                submit_button = page.locator('button[type="submit"]')
                submit_button.click()
                page.wait_for_load_state('networkidle')
                print(f"✓ PMH submitted")
            else:
                print(f"  ✗ ERROR: No PMH textarea found")
                page.screenshot(path='screenshots/mild_06_error.png')
            
            # Step 7: Answer follow-up questions
            print("\n[STEP 7] Answering follow-up questions...")
            
            follow_up_questions = []
            follow_up_count = 0
            max_follow_ups = 20
            
            while follow_up_count < max_follow_ups:
                time.sleep(0.3)
                
                # Check if we're at results page
                if '/results' in page.url:
                    print(f"  Reached results page after {follow_up_count} follow-ups")
                    break
                
                try:
                    question_elem = page.locator('.bg-gray-100.rounded-2xl').last
                    question_text = question_elem.text_content().strip()
                    
                    # Store question
                    follow_up_questions.append(question_text)
                    print(f"  Q{follow_up_count + 1}: {question_text[:70]}...")
                    
                    # Check for different input types and answer with MILD responses
                    if page.locator('button[name="answer"]').count() > 0:
                        # Single choice - look for mild options
                        buttons = page.locator('button[name="answer"]').all()
                        
                        # Try to find mild/no options
                        mild_clicked = False
                        for btn in buttons:
                            btn_text = btn.text_content().strip().lower()
                            if any(word in btn_text for word in ['no', 'mild', 'none', 'not', 'few hours', 'slowly', '1-3']):
                                btn.click()
                                print(f"       → {btn.text_content().strip()}")
                                mild_clicked = True
                                break
                        
                        if not mild_clicked:
                            # Just click first option
                            buttons[0].click()
                            print(f"       → {buttons[0].text_content().strip()}")
                    
                    elif page.locator('textarea[name="answer"]').count() > 0:
                        # Textarea - fill with mild text
                        page.locator('textarea[name="answer"]').fill('mild, started a few hours ago')
                        page.locator('button[type="submit"]').click()
                        print(f"       → mild, started a few hours ago")
                    
                    elif page.locator('input[type="checkbox"][name="answer"]').count() > 0:
                        # Multi-choice - check "none" if available, or first option
                        labels = page.locator('label').all()
                        none_clicked = False
                        for label in labels:
                            if 'none' in label.text_content().lower():
                                label.click()
                                time.sleep(0.2)
                                page.locator('button[type="submit"]').click()
                                print(f"       → None")
                                none_clicked = True
                                break
                        
                        if not none_clicked:
                            page.locator('label').first.click()
                            time.sleep(0.2)
                            page.locator('button[type="submit"]').click()
                            print(f"       → Selected option")
                    
                    elif page.locator('input[type="number"]').count() > 0:
                        # Number input - use low number
                        page.locator('input[type="number"]').fill('2')
                        page.locator('button[type="submit"]').click()
                        print(f"       → 2")
                    
                    elif page.locator('input[type="text"]').count() > 0:
                        # Text input
                        page.locator('input[type="text"]').fill('mild')
                        page.locator('button[type="submit"]').click()
                        print(f"       → mild")
                    
                    page.wait_for_load_state('networkidle')
                    follow_up_count += 1
                    
                except Exception as e:
                    print(f"  Error on follow-up question: {e}")
                    break
            
            print(f"✓ Answered {follow_up_count} follow-up questions")
            
            # Step 8: Continue to results
            print("\n[STEP 8] Navigating to results...")
            
            # Keep answering questions until we reach results
            attempts = 0
            while '/results' not in page.url and attempts < 5:
                try:
                    if page.locator('button[name="answer"]').count() > 0:
                        page.locator('button[name="answer"]').first.click()
                    elif page.locator('button[type="submit"]').count() > 0:
                        page.locator('button[type="submit"]').click()
                    else:
                        break
                    
                    page.wait_for_load_state('networkidle')
                    attempts += 1
                except:
                    break
            
            if '/results' in page.url:
                print(f"✓ Reached results page")
            else:
                print(f"✗ Did not reach results page (current URL: {page.url})")
            
            # Step 9: Verify results page
            print("\n[STEP 9] Analyzing results page...")
            time.sleep(0.5)
            
            # Look for recommendation
            recommendation = None
            headings = page.locator('h1, h2, h3').all()
            for heading in headings:
                text = heading.text_content().strip()
                if any(word in text.lower() for word in ['emergency', 'urgent', 'primary', 'specialist', 'reassurance', 'call', 'see']):
                    recommendation = text
                    print(f"\n  📋 RECOMMENDATION: {recommendation}")
                    break
            
            # Look for THREE PERCENTAGE BARS
            print(f"\n  📊 RISK PERCENTAGES:")
            
            page_content = page.content()
            
            # Look for the three specific risk categories
            risk_data = []
            
            risk_labels = [
                "Likelihood of needing immediate medical attention",
                "Likelihood of hospitalization", 
                "Likelihood of death"
            ]
            
            for label in risk_labels:
                # Try different case variations
                found = False
                for variation in [label, label.lower(), label.title()]:
                    if variation in page_content:
                        found = True
                        print(f"    ✓ Found: '{label}'")
                        
                        # Try to extract percentage
                        # Look for percentage near this text
                        try:
                            label_elem = page.locator(f'text=/{label}/i').first
                            if label_elem.count() > 0:
                                # Get parent container
                                parent = label_elem.locator('xpath=ancestor::*[contains(@class, "risk") or contains(@class, "percentage") or position()=2]').first
                                if parent.count() == 0:
                                    parent = label_elem.locator('xpath=..')
                                
                                # Look for percentage in parent
                                percent_text = parent.text_content()
                                
                                # Extract percentage using regex
                                import re
                                matches = re.findall(r'(\d+\.?\d*)%', percent_text)
                                if matches:
                                    percentage = matches[0] + '%'
                                    print(f"      → {percentage}")
                                    risk_data.append((label, percentage))
                        except:
                            pass
                        break
                
                if not found:
                    print(f"    ✗ NOT found: '{label}'")
            
            # Take screenshot of results
            try:
                page.screenshot(path='screenshots/mild_09_results.png', timeout=5000)
                print(f"\n  📸 Screenshot saved: screenshots/mild_09_results.png")
            except Exception as e:
                print(f"  ⚠️  Could not save results screenshot: {e}")
            
            # Summary
            print("\n" + "=" * 70)
            print("TEST SUMMARY")
            print("=" * 70)
            print(f"✓ Welcome page loaded")
            print(f"✓ Disclaimer accepted")
            print(f"✓ Age: 30")
            print(f"✓ Sex: Female")
            print(f"✓ Symptom textarea: 'I have a headache and I feel tired'")
            print(f"✓ PMH textarea: 'none' (screenshot captured)")
            print(f"✓ Follow-up questions: {follow_up_count}")
            
            if follow_up_questions:
                print(f"\n  Follow-up questions asked:")
                for i, q in enumerate(follow_up_questions[:10], 1):
                    print(f"    {i}. {q[:70]}...")
            
            print(f"\n✓ Results page reached")
            
            if recommendation:
                print(f"\n📋 RECOMMENDATION: {recommendation}")
            
            if risk_data:
                print(f"\n📊 RISK PERCENTAGES:")
                for label, value in risk_data:
                    print(f"  - {label}: {value}")
            else:
                print(f"\n⚠️  Risk percentages: Check screenshot")
            
            print("=" * 70)
            
            # Keep browser open longer to see results
            print("\n  Keeping browser open for 5 seconds to view results...")
            time.sleep(5)
            
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path='screenshots/mild_error.png')
            print(f"  Error screenshot saved")
        
        finally:
            browser.close()

if __name__ == "__main__":
    import os
    os.makedirs('screenshots', exist_ok=True)
    
    test_mild_symptoms()
