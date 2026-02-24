"""
Focused test for severity slider and context tags with low-risk headache.
"""

from playwright.sync_api import sync_playwright
import time

BASE_URL = "http://localhost:5001"

def test_low_risk_headache_with_slider():
    """Test low-risk headache to verify severity slider and context tags."""
    
    print("=" * 70)
    print("FOCUSED TEST: SEVERITY SLIDER + CONTEXT TAGS")
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 900})
        page = context.new_page()
        
        try:
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
            
            get_started = page.locator('button:has-text("Get Started"), button[type="submit"]')
            get_started.first.click()
            page.wait_for_load_state('networkidle')
            print("✓ Clicked Get Started")
            
            # Step 3: Name
            print("\n[STEP 3] Name: Alex...")
            time.sleep(0.5)
            name_input = page.locator('input[type="text"], input[name="answer"]').first
            if name_input.count() > 0:
                name_input.fill('Alex')
                print("  → Typed: Alex")
                page.locator('button[type="submit"]').click()
                page.wait_for_load_state('networkidle')
            
            # Step 4: Answering for - FIRST option
            print("\n[STEP 4] Answering for: FIRST option (myself)...")
            time.sleep(0.5)
            first_button = page.locator('button').first
            button_text = first_button.text_content().strip()
            print(f"  → Clicking: {button_text}")
            first_button.click()
            page.wait_for_load_state('networkidle')
            
            # Step 5: Age
            print("\n[STEP 5] Age: 25...")
            time.sleep(0.5)
            age_input = page.locator('input[type="number"]')
            if age_input.count() > 0:
                age_input.fill('25')
                print("  → Typed: 25")
                page.locator('button[type="submit"]').click()
                page.wait_for_load_state('networkidle')
            
            # Step 6: Sex - Female
            print("\n[STEP 6] Sex: Female...")
            time.sleep(0.5)
            female_button = page.locator('button[name="answer"][value="female"], button:has-text("Female")').first
            if female_button.count() > 0:
                female_button.click()
                page.wait_for_load_state('networkidle')
                print("  → Selected: Female")
            
            # Step 7: Body map - HEAD
            print("\n[STEP 7] Body map: HEAD...")
            time.sleep(0.5)
            
            # Look for Head button or SVG region
            head_button = page.locator('button:has-text("Head"), [data-region="head"], #head').first
            if head_button.count() > 0:
                head_button.click()
                print("  → Clicked: Head")
                time.sleep(0.3)
                
                continue_btn = page.locator('button:has-text("Continue"), button[type="submit"]')
                if continue_btn.count() > 0:
                    continue_btn.click()
                    page.wait_for_load_state('networkidle')
                    print("  ✓ Body map submitted")
            
            # Step 8: Symptoms - "I have a mild headache"
            print("\n[STEP 8] Symptoms: 'I have a mild headache'...")
            time.sleep(0.5)
            textarea = page.locator('textarea[name="answer"]')
            if textarea.count() > 0:
                textarea.fill('I have a mild headache')
                print("  → Typed: I have a mild headache")
                page.locator('button[type="submit"]').click()
                page.wait_for_load_state('networkidle')
            
            # Step 9: PMH - "none"
            print("\n[STEP 9] PMH: 'none'...")
            time.sleep(0.5)
            textarea = page.locator('textarea[name="answer"]')
            if textarea.count() > 0:
                textarea.fill('none')
                print("  → Typed: none")
                page.locator('button[type="submit"]').click()
                page.wait_for_load_state('networkidle')
            
            # Step 10: Follow-up questions
            print("\n[STEP 10] Follow-up questions...")
            
            context_tag_found = False
            severity_slider_found = False
            question_count = 0
            
            # Specific answer mapping for low-risk headache
            answer_map = {
                'onset': 'slowly',
                'worst': 'no',
                'severity': 'mild',  # This should trigger the emoji slider
                'where': 'all',
                'feel': 'dull',
                'stiff': 'no',
                'fever': 'no',
                'vision': 'no',
                'weakness': 'no',
                'speaking': 'no',
                'confused': 'no',
                'nausea': 'no',
                'before': 'yes',
                'injury': 'no',
                'thinners': 'no'
            }
            
            while question_count < 20:
                time.sleep(0.5)
                
                if '/results' in page.url:
                    print(f"\n  ✓ Reached results after {question_count} questions")
                    break
                
                try:
                    # Check for context tag
                    page_content = page.content()
                    
                    if not context_tag_found:
                        if 'About your headache' in page_content or 'about your headache' in page_content:
                            print(f"\n  ✓✓✓ CONTEXT TAG FOUND: 'About your headache' ✓✓✓")
                            context_tag_found = True
                    
                    # Get question text
                    question_elem = page.locator('h1, h2, h3, .text-xl, .text-2xl').first
                    if question_elem.count() > 0:
                        question_text = question_elem.text_content().strip()
                        print(f"\n  Q{question_count + 1}: {question_text[:70]}...")
                    
                    # Check for SEVERITY SLIDER with emojis
                    emoji_mild = page.locator('button:has-text("😊")')
                    emoji_moderate = page.locator('button:has-text("😐")')
                    emoji_severe = page.locator('button:has-text("😣")')
                    emoji_worst = page.locator('button:has-text("😱")')
                    
                    total_emojis = emoji_mild.count() + emoji_moderate.count() + emoji_severe.count() + emoji_worst.count()
                    
                    if total_emojis >= 4:
                        if not severity_slider_found:
                            print(f"\n  ✓✓✓ SEVERITY SLIDER FOUND! ✓✓✓")
                            print(f"  Found emoji buttons:")
                            
                            if emoji_mild.count() > 0:
                                print(f"    - 😊 Mild: {emoji_mild.first.text_content().strip()}")
                            if emoji_moderate.count() > 0:
                                print(f"    - 😐 Moderate: {emoji_moderate.first.text_content().strip()}")
                            if emoji_severe.count() > 0:
                                print(f"    - 😣 Severe: {emoji_severe.first.text_content().strip()}")
                            if emoji_worst.count() > 0:
                                print(f"    - 😱 Worst: {emoji_worst.first.text_content().strip()}")
                            
                            # Check for gradient bar
                            gradient = page.locator('.gradient, [class*="gradient"], [style*="gradient"]')
                            if gradient.count() > 0:
                                print(f"  ✓ Color gradient bar detected")
                            
                            # Take screenshot
                            page.screenshot(path='screenshots/severity_slider_screen.png', full_page=True)
                            print(f"\n  📸 SEVERITY SLIDER SCREENSHOT SAVED!")
                            
                            severity_slider_found = True
                            
                            # Click "Mild" (first emoji)
                            print(f"\n  → Clicking 😊 Mild...")
                            emoji_mild.first.click()
                            page.wait_for_load_state('networkidle')
                            question_count += 1
                            continue
                    
                    # Regular question answering
                    if page.locator('button[name="answer"]').count() > 0:
                        buttons = page.locator('button[name="answer"]').all()
                        
                        # Try to find appropriate low-risk answer
                        clicked = False
                        question_lower = question_text.lower() if 'question_text' in locals() else ''
                        
                        for keyword, answer_keyword in answer_map.items():
                            if keyword in question_lower:
                                for btn in buttons:
                                    btn_text = btn.text_content().strip().lower()
                                    if answer_keyword in btn_text:
                                        btn.click()
                                        print(f"    → {btn.text_content().strip()}")
                                        clicked = True
                                        break
                                if clicked:
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
            
            # Step 11: Analyze results
            print("\n[STEP 11] Analyzing results page...")
            time.sleep(0.5)
            
            page_content = page.content()
            
            # Check for personalization
            if 'Alex' in page_content:
                print("  ✓ Personalization: 'Alex' found")
            else:
                print("  ✗ Personalization: 'Alex' NOT found")
            
            # Check for recommendation
            recommendation = None
            recommendation_color = None
            
            if 'Likely Okay' in page_content or "You're Okay" in page_content:
                recommendation = "You're Likely Okay"
                recommendation_color = "GREEN"
                print(f"  ✓ Recommendation: {recommendation} ({recommendation_color})")
            elif 'Emergency' in page_content:
                recommendation = "Go to the Emergency Department"
                recommendation_color = "RED"
                print(f"  ⚠️  Recommendation: {recommendation} ({recommendation_color})")
            elif 'Urgent Care' in page_content:
                recommendation = "Visit Urgent Care"
                recommendation_color = "ORANGE"
                print(f"  ✓ Recommendation: {recommendation} ({recommendation_color})")
            
            # Extract risk percentages
            print("\n  📊 Risk Percentages:")
            import re
            percentages = re.findall(r'(\d+\.?\d*)%', page_content)
            
            # Look for the 4 specific risk categories
            risk_labels = [
                "something serious",
                "immediate medical attention",
                "hospitalization",
                "death"
            ]
            
            for label in risk_labels:
                if label in page_content.lower():
                    # Find percentage near this label
                    print(f"    - {label.title()}: Found")
            
            if percentages:
                print(f"    Percentages found: {percentages[:4]}")
            
            # Check for escalation section
            if 'If This Happens' in page_content or 'Get Help Right Away' in page_content:
                print("\n  ✓ 'If This Happens, Get Help Right Away' section found")
                
                # Check if headache-specific
                if 'headache' in page_content.lower():
                    print("  ✓ Escalation statements appear to be headache-specific")
            
            # Take final screenshot
            page.screenshot(path='screenshots/severity_slider_final_results.png', full_page=True)
            print("\n  📸 FINAL RESULTS SCREENSHOT SAVED!")
            
            # Summary
            print("\n" + "=" * 70)
            print("TEST SUMMARY")
            print("=" * 70)
            
            print(f"\n1. Context Tag ('About your headache'):")
            if context_tag_found:
                print(f"   ✓ YES - Found on follow-up questions")
            else:
                print(f"   ✗ NO - Not found")
            
            print(f"\n2. Severity Slider (4 emojis + gradient):")
            if severity_slider_found:
                print(f"   ✓ YES - Found with 😊😐😣😱 emojis")
                print(f"   Screenshot: severity_slider_screen.png")
            else:
                print(f"   ✗ NO - Not found")
            
            print(f"\n3. Final Recommendation:")
            if recommendation:
                print(f"   {recommendation_color}: {recommendation}")
            else:
                print(f"   Unknown")
            
            print(f"\n4. Personalization ('Alex'):")
            print(f"   {'✓ Found' if 'Alex' in page_content else '✗ Not found'}")
            
            print(f"\n5. Risk Percentages:")
            if percentages:
                print(f"   Found: {percentages[:4]}")
            else:
                print(f"   Not extracted")
            
            print(f"\n6. Escalation Statements:")
            if 'If This Happens' in page_content:
                print(f"   ✓ Section present")
                if 'headache' in page_content.lower():
                    print(f"   ✓ Headache-specific content detected")
            else:
                print(f"   ✗ Section not found")
            
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
    
    test_low_risk_headache_with_slider()
