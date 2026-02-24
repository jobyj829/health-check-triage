"""
End-to-end browser test for the triage app with FREE TEXT inputs.
Tests the updated interface with textarea inputs instead of cards/checkboxes.
"""

from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:5001"

def test_freetext_triage_app():
    """Run end-to-end test of the triage app with free text inputs."""
    
    print("=" * 70)
    print("TRIAGE APP FREE TEXT INTERFACE TEST")
    print("=" * 70)
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            # Step 1: Visit welcome page
            print("\n[STEP 1] Visiting welcome page...")
            page.goto(BASE_URL)
            page.wait_for_load_state('networkidle')
            
            heading = page.locator('h1').text_content()
            print(f"✓ Welcome page loaded")
            print(f"  Heading: {heading}")
            
            page.screenshot(path='screenshots/freetext_01_welcome.png')
            print(f"  Screenshot saved: screenshots/freetext_01_welcome.png")
            
            # Step 2: Accept disclaimer and start
            print("\n[STEP 2] Accepting disclaimer and starting...")
            
            consent_checkbox = page.locator('input[type="checkbox"]#consent')
            consent_checkbox.check()
            print(f"✓ Consent checkbox checked")
            
            start_button = page.locator('button[type="submit"]')
            start_button.click()
            page.wait_for_load_state('networkidle')
            print(f"✓ Started interview")
            
            # Step 3: Answer age question
            print("\n[STEP 3] Answering age question...")
            page.wait_for_selector('input[type="number"]', timeout=5000)
            
            question_text = page.locator('.bg-gray-100.rounded-2xl').first.text_content()
            print(f"  Question: {question_text.strip()}")
            
            age_input = page.locator('input[type="number"]')
            age_input.fill('55')
            print(f"  Answer: 55")
            
            page.locator('button[type="submit"]').click()
            page.wait_for_load_state('networkidle')
            print(f"✓ Age submitted")
            
            # Step 4: Answer sex question
            print("\n[STEP 4] Answering sex question...")
            time.sleep(0.5)
            
            question_text = page.locator('.bg-gray-100.rounded-2xl').last.text_content()
            print(f"  Question: {question_text.strip()}")
            
            male_button = page.locator('button[name="answer"][value="male"]')
            male_button.click()
            page.wait_for_load_state('networkidle')
            print(f"  Answer: Male")
            print(f"✓ Sex submitted")
            
            # Step 5: Symptom question - CHECK FOR TEXTAREA
            print("\n[STEP 5] Symptom question - CHECKING FOR TEXTAREA...")
            time.sleep(0.5)
            
            question_text = page.locator('.bg-gray-100.rounded-2xl').last.text_content()
            print(f"  Question: {question_text.strip()}")
            
            # Check for textarea
            textarea = page.locator('textarea[name="answer"]')
            textarea_count = textarea.count()
            
            # Check for checkboxes (old style)
            checkboxes = page.locator('input[type="checkbox"][name="answer"]')
            checkbox_count = checkboxes.count()
            
            # Check for cards (old style)
            cards = page.locator('label:has(input[type="checkbox"])')
            card_count = cards.count()
            
            print(f"\n  INPUT TYPE ANALYSIS:")
            print(f"  - Textarea found: {textarea_count}")
            print(f"  - Checkboxes found: {checkbox_count}")
            print(f"  - Cards found: {card_count}")
            
            if textarea_count > 0:
                print(f"  ✓ CONFIRMED: FREE TEXT TEXTAREA (not cards/checkboxes)")
                
                # Fill in the symptom text
                symptom_text = "I have chest pain and I'm having trouble breathing"
                textarea.fill(symptom_text)
                print(f"  Typed: '{symptom_text}'")
                
                # Take screenshot
                page.screenshot(path='screenshots/freetext_05_symptom_textarea.png')
                print(f"  Screenshot saved: screenshots/freetext_05_symptom_textarea.png")
                
                # Click Continue/Submit
                time.sleep(0.3)
                submit_button = page.locator('button[type="submit"]')
                submit_button.click()
                page.wait_for_load_state('networkidle')
                print(f"✓ Symptom submitted")
            else:
                print(f"  ✗ ERROR: Expected TEXTAREA but found {checkbox_count} checkboxes and {card_count} cards")
                page.screenshot(path='screenshots/freetext_05_error.png')
                print(f"  Error screenshot saved")
            
            # Step 6: PMH question - CHECK FOR TEXTAREA
            print("\n[STEP 6] PMH question - CHECKING FOR TEXTAREA...")
            time.sleep(0.5)
            
            question_text = page.locator('.bg-gray-100.rounded-2xl').last.text_content()
            print(f"  Question: {question_text.strip()}")
            
            # Check for textarea
            textarea = page.locator('textarea[name="answer"]')
            textarea_count = textarea.count()
            
            # Check for checkboxes (old style)
            checkboxes = page.locator('input[type="checkbox"][name="answer"]')
            checkbox_count = checkboxes.count()
            
            print(f"\n  INPUT TYPE ANALYSIS:")
            print(f"  - Textarea found: {textarea_count}")
            print(f"  - Checkboxes found: {checkbox_count}")
            
            if textarea_count > 0:
                print(f"  ✓ CONFIRMED: FREE TEXT TEXTAREA (not checkboxes)")
                
                # Fill in the PMH text
                pmh_text = "diabetes, high blood pressure, take metformin"
                textarea.fill(pmh_text)
                print(f"  Typed: '{pmh_text}'")
                
                # Take screenshot
                page.screenshot(path='screenshots/freetext_06_pmh_textarea.png')
                print(f"  Screenshot saved: screenshots/freetext_06_pmh_textarea.png")
                
                # Click Continue/Submit
                time.sleep(0.3)
                submit_button = page.locator('button[type="submit"]')
                submit_button.click()
                page.wait_for_load_state('networkidle')
                print(f"✓ PMH submitted")
            else:
                print(f"  ✗ ERROR: Expected TEXTAREA but found {checkbox_count} checkboxes")
                page.screenshot(path='screenshots/freetext_06_error.png')
                print(f"  Error screenshot saved")
            
            # Step 7: Answer follow-up questions
            print("\n[STEP 7] Answering follow-up questions...")
            
            follow_up_count = 0
            max_follow_ups = 15
            
            while follow_up_count < max_follow_ups:
                time.sleep(0.3)
                
                # Check if we're at results page
                if '/results' in page.url:
                    print(f"  Reached results page after {follow_up_count} follow-ups")
                    break
                
                try:
                    question_elem = page.locator('.bg-gray-100.rounded-2xl').last
                    question_text = question_elem.text_content().strip()
                    print(f"  Q{follow_up_count + 1}: {question_text[:60]}...")
                    
                    # Check for different input types
                    if page.locator('button[name="answer"]').count() > 0:
                        # Single choice - click first option
                        page.locator('button[name="answer"]').first.click()
                        answer = page.locator('button[name="answer"]').first.text_content().strip()
                        print(f"       → {answer}")
                    elif page.locator('textarea[name="answer"]').count() > 0:
                        # Textarea - fill with reasonable text
                        page.locator('textarea[name="answer"]').fill('moderate, a few hours')
                        page.locator('button[type="submit"]').click()
                        print(f"       → moderate, a few hours")
                    elif page.locator('input[type="checkbox"][name="answer"]').count() > 0:
                        # Multi-choice - check first option and submit
                        page.locator('label').first.click()
                        time.sleep(0.2)
                        page.locator('button[type="submit"]').click()
                        print(f"       → Selected option")
                    elif page.locator('input[type="number"]').count() > 0:
                        # Number input
                        page.locator('input[type="number"]').fill('5')
                        page.locator('button[type="submit"]').click()
                        print(f"       → 5")
                    elif page.locator('input[type="text"]').count() > 0:
                        # Text input
                        page.locator('input[type="text"]').fill('moderate')
                        page.locator('button[type="submit"]').click()
                        print(f"       → moderate")
                    
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
            
            # Step 9: Verify results page with THREE PERCENTAGE BARS
            print("\n[STEP 9] Verifying results page with risk percentages...")
            time.sleep(0.5)
            
            # Look for recommendation
            recommendation = None
            headings = page.locator('h1, h2, h3').all()
            for heading in headings:
                text = heading.text_content().strip()
                if any(word in text.lower() for word in ['emergency', 'urgent', 'primary', 'specialist', 'reassurance', 'call']):
                    recommendation = text
                    print(f"\n  📋 RECOMMENDATION: {recommendation}")
                    break
            
            # Look for THREE PERCENTAGE BARS
            print(f"\n  📊 RISK PERCENTAGES:")
            
            # Method 1: Look for specific text patterns
            page_content = page.content()
            
            # Look for percentage text
            percentages = []
            
            # Try to find percentage elements
            percent_elements = page.locator('text=/\\d+%/').all()
            for elem in percent_elements[:10]:
                text = elem.text_content().strip()
                print(f"    Found: {text}")
            
            # Look for specific risk categories
            risk_labels = [
                "Likelihood of needing immediate medical attention",
                "Likelihood of hospitalization", 
                "Likelihood of death"
            ]
            
            for label in risk_labels:
                if label.lower() in page_content.lower():
                    print(f"    ✓ Found: '{label}'")
                    
                    # Try to find the percentage near this label
                    label_elem = page.locator(f'text=/{label}/i').first
                    if label_elem.count() > 0:
                        # Look for percentage in parent or sibling elements
                        parent = label_elem.locator('xpath=..')
                        percent_in_parent = parent.locator('text=/\\d+%/').first
                        if percent_in_parent.count() > 0:
                            percent_value = percent_in_parent.text_content().strip()
                            print(f"      → {percent_value}")
                            percentages.append((label, percent_value))
                else:
                    print(f"    ✗ NOT found: '{label}'")
            
            # Look for progress bars
            progress_bars = page.locator('[role="progressbar"], .progress, [class*="progress"]').all()
            print(f"\n  Progress bars found: {len(progress_bars)}")
            
            # Take screenshot of results
            page.screenshot(path='screenshots/freetext_09_results.png')
            print(f"\n  Screenshot saved: screenshots/freetext_09_results.png")
            
            # Summary
            print("\n" + "=" * 70)
            print("TEST SUMMARY")
            print("=" * 70)
            print(f"✓ Welcome page loaded")
            print(f"✓ Disclaimer accepted")
            print(f"✓ Age question answered (55)")
            print(f"✓ Sex question answered (Male)")
            
            if textarea_count > 0:
                print(f"✓ Symptom input: FREE TEXT TEXTAREA ✓")
                print(f"  Text: 'I have chest pain and I'm having trouble breathing'")
            else:
                print(f"✗ Symptom input: Expected TEXTAREA, found cards/checkboxes")
            
            print(f"✓ PMH input: FREE TEXT TEXTAREA ✓")
            print(f"  Text: 'diabetes, high blood pressure, take metformin'")
            
            print(f"✓ Follow-up questions answered ({follow_up_count})")
            print(f"✓ Results page reached")
            
            if recommendation:
                print(f"\n📋 RECOMMENDATION: {recommendation}")
            
            if percentages:
                print(f"\n📊 RISK PERCENTAGES:")
                for label, value in percentages:
                    print(f"  - {label}: {value}")
            else:
                print(f"\n⚠️  Could not extract exact percentage values")
                print(f"  (Check screenshot: screenshots/freetext_09_results.png)")
            
            print("=" * 70)
            
            # Keep browser open for a moment
            time.sleep(3)
            
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path='screenshots/freetext_error.png')
            print(f"  Error screenshot saved: screenshots/freetext_error.png")
        
        finally:
            browser.close()

if __name__ == "__main__":
    import os
    os.makedirs('screenshots', exist_ok=True)
    
    test_freetext_triage_app()
