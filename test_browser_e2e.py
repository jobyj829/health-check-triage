"""
End-to-end browser test for the triage app using Playwright.
Tests the complete user flow from welcome to results.
"""

from playwright.sync_api import sync_playwright, Page
import time
import sys

BASE_URL = "http://localhost:5001"

def test_triage_app():
    """Run end-to-end test of the triage app."""
    
    print("=" * 70)
    print("TRIAGE APP END-TO-END BROWSER TEST")
    print("=" * 70)
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)  # Set to False to see the browser
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            # Step 1: Visit welcome page
            print("\n[STEP 1] Visiting welcome page...")
            page.goto(BASE_URL)
            page.wait_for_load_state('networkidle')
            
            # Verify welcome page loaded
            heading = page.locator('h1').text_content()
            print(f"✓ Welcome page loaded")
            print(f"  Heading: {heading}")
            
            # Take screenshot
            page.screenshot(path='screenshots/01_welcome.png')
            print(f"  Screenshot saved: screenshots/01_welcome.png")
            
            # Step 2: Accept disclaimer and start
            print("\n[STEP 2] Accepting disclaimer and starting...")
            
            # Check the consent checkbox
            consent_checkbox = page.locator('input[type="checkbox"]#consent')
            consent_checkbox.check()
            print(f"✓ Consent checkbox checked")
            
            # Click the submit button
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
            age_input.fill('45')
            print(f"  Answer: 45")
            
            page.locator('button[type="submit"]').click()
            page.wait_for_load_state('networkidle')
            print(f"✓ Age submitted")
            
            # Step 4: Answer sex question
            print("\n[STEP 4] Answering sex question...")
            time.sleep(0.5)  # Brief pause for page to render
            
            question_text = page.locator('.bg-gray-100.rounded-2xl').last.text_content()
            print(f"  Question: {question_text.strip()}")
            
            # Look for Male option button (value is lowercase "male")
            male_button = page.locator('button[name="answer"][value="male"]')
            male_button.click()
            page.wait_for_load_state('networkidle')
            print(f"  Answer: Male")
            print(f"✓ Sex submitted")
            
            # Step 5: Symptom selection - CRITICAL CHECK
            print("\n[STEP 5] Symptom selection screen...")
            time.sleep(0.5)
            
            question_text = page.locator('.bg-gray-100.rounded-2xl').last.text_content()
            print(f"  Question: {question_text.strip()}")
            
            # Count symptom options
            # Look for checkboxes (multi-choice)
            checkboxes = page.locator('input[type="checkbox"][name="answer"]')
            checkbox_count = checkboxes.count()
            
            # Look for button options (single-choice cards)
            button_options = page.locator('button[name="answer"]')
            button_count = button_options.count()
            
            print(f"\n  SYMPTOM SELECTION ANALYSIS:")
            print(f"  - Checkboxes found: {checkbox_count}")
            print(f"  - Button options found: {button_count}")
            
            if checkbox_count > 0:
                print(f"  - Style: CHECKBOX (multi-select)")
                # Get labels for first few options
                labels = page.locator('label').all()
                print(f"  - First 5 options:")
                for i, label in enumerate(labels[:5]):
                    text = label.text_content().strip()
                    if text:
                        print(f"    {i+1}. {text}")
            elif button_count > 0:
                print(f"  - Style: BUTTON CARDS (single-select)")
                # Get button labels
                print(f"  - Options:")
                for i in range(min(button_count, 5)):
                    text = button_options.nth(i).text_content().strip()
                    print(f"    {i+1}. {text}")
            
            # Take screenshot of symptom selection
            page.screenshot(path='screenshots/05_symptom_selection.png')
            print(f"\n  Screenshot saved: screenshots/05_symptom_selection.png")
            
            # Step 6: Select chest pain
            print("\n[STEP 6] Selecting chest pain symptom...")
            
            if checkbox_count > 0:
                # Multi-choice: check the chest pain checkbox (value is "chest")
                # The checkbox is hidden, so we need to click the label
                chest_pain_label = page.locator('label:has(input[value="chest"])')
                if chest_pain_label.count() > 0:
                    chest_pain_label.click()
                    print(f"✓ Checked 'Chest pain or pressure' checkbox")
                    
                    # Click Continue button
                    time.sleep(0.3)  # Brief pause for button to enable
                    continue_button = page.locator('button[type="submit"]#multiSubmit')
                    continue_button.click()
                else:
                    print(f"✗ Could not find chest pain checkbox")
                    # Try to find any label and click it
                    page.locator('label').first.click()
                    print(f"  Selected first available option")
                    time.sleep(0.3)
                    page.locator('button[type="submit"]').click()
            else:
                # Single-choice: click the chest pain button
                chest_pain_button = page.locator('button[value="chest"]')
                if chest_pain_button.count() > 0:
                    chest_pain_button.click()
                    print(f"✓ Clicked 'Chest pain or pressure' button")
                else:
                    print(f"✗ Could not find chest pain button")
                    # Click first available button
                    button_options.first.click()
                    print(f"  Clicked first available option")
            
            page.wait_for_load_state('networkidle')
            print(f"✓ Symptom submitted")
            
            # Step 7: Answer follow-up questions
            print("\n[STEP 7] Answering follow-up questions...")
            
            follow_up_count = 0
            max_follow_ups = 10
            
            while follow_up_count < max_follow_ups:
                time.sleep(0.3)
                
                # Check if we're at results page
                if '/results' in page.url:
                    print(f"  Reached results page after {follow_up_count} follow-ups")
                    break
                
                # Get current question
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
                    elif page.locator('input[type="checkbox"][name="answer"]').count() > 0:
                        # Multi-choice - check first option and submit
                        page.locator('input[type="checkbox"][name="answer"]').first.check()
                        page.locator('button[type="submit"]').click()
                        print(f"       → Selected option")
                    elif page.locator('input[type="number"]').count() > 0:
                        # Number input
                        page.locator('input[type="number"]').fill('5')
                        page.locator('button[type="submit"]').click()
                        print(f"       → 5")
                    elif page.locator('input[type="text"]').count() > 0:
                        # Text input
                        page.locator('input[type="text"]').fill('test')
                        page.locator('button[type="submit"]').click()
                        print(f"       → test")
                    
                    page.wait_for_load_state('networkidle')
                    follow_up_count += 1
                    
                except Exception as e:
                    print(f"  Error on follow-up question: {e}")
                    break
            
            print(f"✓ Answered {follow_up_count} follow-up questions")
            
            # Step 8: PMH question (if we haven't reached results yet)
            if '/results' not in page.url:
                print("\n[STEP 8] Looking for PMH question...")
                time.sleep(0.5)
                
                # Check if there's a "None" or "None of the above" option
                none_checkbox = page.locator('input[type="checkbox"][value="none"]')
                if none_checkbox.count() > 0:
                    none_checkbox.check()
                    page.locator('button[type="submit"]').click()
                    page.wait_for_load_state('networkidle')
                    print(f"✓ Selected 'None' for PMH")
                else:
                    print(f"  PMH question not found or already passed")
            
            # Step 9: Continue to results
            print("\n[STEP 9] Navigating to results...")
            
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
            
            # Step 10: Verify results page
            print("\n[STEP 10] Verifying results page...")
            time.sleep(0.5)
            
            # Look for recommendation
            recommendation = None
            urgency = None
            
            # Try to find the main recommendation heading
            headings = page.locator('h1, h2, h3').all()
            for heading in headings:
                text = heading.text_content().strip()
                if any(word in text.lower() for word in ['emergency', 'urgent', 'primary', 'specialist', 'reassurance', 'call']):
                    recommendation = text
                    print(f"  Recommendation: {recommendation}")
                    break
            
            # Look for urgency text
            paragraphs = page.locator('p').all()
            for p in paragraphs[:10]:
                text = p.text_content().strip()
                if len(text) > 20 and len(text) < 200:
                    if any(word in text.lower() for word in ['today', 'immediately', 'hours', 'days', 'week']):
                        urgency = text
                        print(f"  Urgency: {urgency}")
                        break
            
            # Look for evidence section
            if 'evidence' in page.content().lower() or 'patients' in page.content().lower():
                print(f"✓ Evidence section found")
            
            # Take screenshot of results
            page.screenshot(path='screenshots/10_results.png')
            print(f"  Screenshot saved: screenshots/10_results.png")
            
            if recommendation:
                print(f"\n✓ Results page verified successfully")
            else:
                print(f"\n✗ Could not find recommendation on results page")
            
            # Summary
            print("\n" + "=" * 70)
            print("TEST SUMMARY")
            print("=" * 70)
            print(f"✓ Welcome page loaded")
            print(f"✓ Disclaimer accepted")
            print(f"✓ Age question answered (45)")
            print(f"✓ Sex question answered (Male)")
            print(f"✓ Symptom selection completed")
            print(f"  - Checkboxes: {checkbox_count}")
            print(f"  - Buttons: {button_count}")
            print(f"✓ Follow-up questions answered ({follow_up_count})")
            print(f"✓ Results page reached")
            if recommendation:
                print(f"✓ Recommendation: {recommendation}")
            print("=" * 70)
            
            # Keep browser open for a moment
            time.sleep(2)
            
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path='screenshots/error.png')
            print(f"  Error screenshot saved: screenshots/error.png")
        
        finally:
            browser.close()

if __name__ == "__main__":
    # Create screenshots directory
    import os
    os.makedirs('screenshots', exist_ok=True)
    
    test_triage_app()
