"""
Test a low-acuity scenario to see different recommendation.
Patient with minor symptoms that don't require urgent care.
"""

import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "http://localhost:5001"

def run_low_acuity_scenario():
    """
    Run a low-acuity patient scenario:
    - 30 year old female
    - Mild headache
    - No concerning medical history
    """
    session = requests.Session()
    
    print("=" * 70)
    print("LOW ACUITY PATIENT SCENARIO TEST")
    print("=" * 70)
    print("\nPatient: 30-year-old female with mild headache")
    print("History: No significant medical conditions\n")
    
    # Start
    session.get(f"{BASE_URL}/")
    session.post(f"{BASE_URL}/start", data={'consent': 'on'})
    
    question_count = 0
    
    # Answer questions until we reach results
    for _ in range(20):
        response = session.get(f"{BASE_URL}/interview")
        if '/results' in response.url:
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        form = soup.find('form', {'action': '/answer'})
        if not form:
            break
            
        qid = form.find('input', {'name': 'question_id'}).get('value')
        qtype = form.find('input', {'name': 'question_type'}).get('value')
        qtext = form.find('input', {'name': 'question_text'}).get('value')
        
        print(f"Q{question_count + 1}: {qtext}")
        
        # Provide low-acuity answers
        if qid == 'age':
            answer = '30'
            print(f"   → {answer}")
        elif qid == 'sex':
            answer = 'F'
            print(f"   → Female")
        elif qid == 'symptoms':
            answer = ['headache']
            print(f"   → Headache")
        elif qid == 'pmh':
            answer = ['none']
            print(f"   → None")
        elif 'severity' in qid.lower():
            answer = 'mild'
            print(f"   → Mild")
        elif 'sudden' in qid.lower() or 'worst' in qid.lower():
            answer = 'no'
            print(f"   → No")
        elif 'duration' in qid.lower():
            answer = 'hours'
            print(f"   → Hours")
        else:
            answer = 'no'
            print(f"   → No")
        
        form_data = {
            'question_id': qid,
            'question_type': qtype,
            'question_text': qtext,
            'answer': answer
        }
        
        response = session.post(f"{BASE_URL}/answer", data=form_data, allow_redirects=True)
        question_count += 1
        
        if '/results' in response.url:
            break
    
    # Get results
    response = session.get(f"{BASE_URL}/results")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    # Extract recommendation
    print("\n📋 RECOMMENDATION:")
    print("-" * 70)
    
    headings = soup.find_all(['h1', 'h2', 'h3'])
    for h in headings:
        text = h.get_text(strip=True)
        if any(word in text.lower() for word in ['emergency', 'urgent', 'primary', 'recommendation', 'should', 'call', 'visit']):
            print(f"  {text}")
    
    # Extract key recommendation text
    main_content = soup.find('main') or soup.find('body')
    if main_content:
        # Look for the main recommendation card/section
        cards = main_content.find_all(['div'], class_=re.compile(r'bg-|card|recommendation'))
        for card in cards[:3]:
            text = card.get_text(strip=True)
            if len(text) > 50 and len(text) < 500:
                if any(word in text.lower() for word in ['emergency', 'urgent', 'primary', 'call']):
                    print(f"\n  {text}")
                    break
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    run_low_acuity_scenario()
