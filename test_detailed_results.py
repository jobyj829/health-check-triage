"""
Detailed test to capture and display results page content.
"""

import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "http://localhost:5001"

def run_scenario_and_get_results():
    """Run the same patient scenario and extract detailed results."""
    session = requests.Session()
    
    # Start
    session.get(f"{BASE_URL}/")
    session.post(f"{BASE_URL}/start", data={'consent': 'on'})
    
    # Answer questions
    answers = [
        {'question_id': 'age', 'question_type': 'number', 'question_text': 'Age', 'answer': '55'},
        {'question_id': 'sex', 'question_type': 'choice', 'question_text': 'Sex', 'answer': 'M'},
    ]
    
    # Get first question and answer it
    response = session.get(f"{BASE_URL}/interview")
    soup = BeautifulSoup(response.text, 'html.parser')
    form = soup.find('form', {'action': '/answer'})
    
    # Age
    qid = form.find('input', {'name': 'question_id'}).get('value')
    qtype = form.find('input', {'name': 'question_type'}).get('value')
    qtext = form.find('input', {'name': 'question_text'}).get('value')
    session.post(f"{BASE_URL}/answer", data={
        'question_id': qid, 'question_type': qtype, 'question_text': qtext, 'answer': '55'
    })
    
    # Sex
    response = session.get(f"{BASE_URL}/interview")
    soup = BeautifulSoup(response.text, 'html.parser')
    form = soup.find('form', {'action': '/answer'})
    qid = form.find('input', {'name': 'question_id'}).get('value')
    qtype = form.find('input', {'name': 'question_type'}).get('value')
    qtext = form.find('input', {'name': 'question_text'}).get('value')
    session.post(f"{BASE_URL}/answer", data={
        'question_id': qid, 'question_type': qtype, 'question_text': qtext, 'answer': 'M'
    })
    
    # Symptoms
    response = session.get(f"{BASE_URL}/interview")
    soup = BeautifulSoup(response.text, 'html.parser')
    form = soup.find('form', {'action': '/answer'})
    qid = form.find('input', {'name': 'question_id'}).get('value')
    qtype = form.find('input', {'name': 'question_type'}).get('value')
    qtext = form.find('input', {'name': 'question_text'}).get('value')
    session.post(f"{BASE_URL}/answer", data={
        'question_id': qid, 'question_type': qtype, 'question_text': qtext, 
        'answer': ['chest_pain', 'sob'],
        'answer_label': ['Chest Pain', 'Trouble Breathing']
    })
    
    # PMH
    response = session.get(f"{BASE_URL}/interview")
    soup = BeautifulSoup(response.text, 'html.parser')
    form = soup.find('form', {'action': '/answer'})
    qid = form.find('input', {'name': 'question_id'}).get('value')
    qtype = form.find('input', {'name': 'question_type'}).get('value')
    qtext = form.find('input', {'name': 'question_text'}).get('value')
    session.post(f"{BASE_URL}/answer", data={
        'question_id': qid, 'question_type': qtype, 'question_text': qtext,
        'answer': ['diabetes', 'hypertension'],
        'answer_label': ['Diabetes', 'High Blood Pressure']
    })
    
    # Answer remaining questions with defaults
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
        
        # Provide answers that suggest serious condition
        if 'quality' in qid.lower():
            answer = 'pressure'
        elif 'radiation' in qid.lower():
            answer = 'yes'
        elif 'severity' in qid.lower():
            answer = 'severe'
        else:
            answer = 'yes'
            
        response = session.post(f"{BASE_URL}/answer", data={
            'question_id': qid, 'question_type': qtype, 'question_text': qtext, 'answer': answer
        }, allow_redirects=True)
        
        if '/results' in response.url:
            break
    
    # Get results page
    response = session.get(f"{BASE_URL}/results")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("=" * 70)
    print("RESULTS PAGE CONTENT")
    print("=" * 70)
    
    # Extract recommendation
    print("\n📋 RECOMMENDATION:")
    print("-" * 70)
    
    # Look for main recommendation heading
    headings = soup.find_all(['h1', 'h2', 'h3'])
    for h in headings:
        text = h.get_text(strip=True)
        if any(word in text.lower() for word in ['emergency', 'urgent', 'primary', 'recommendation', 'should']):
            print(f"  {text}")
    
    # Look for recommendation text
    recommendation_section = soup.find(string=re.compile(r'(Emergency|Urgent|Primary Care|Call 911)'))
    if recommendation_section:
        parent = recommendation_section.find_parent()
        if parent:
            print(f"\n  {parent.get_text(strip=True)[:500]}")
    
    # Extract evidence
    print("\n\n📊 EVIDENCE:")
    print("-" * 70)
    
    # Look for evidence section
    evidence_text = soup.find(string=re.compile(r'(evidence|similar patients|data shows)', re.I))
    if evidence_text:
        parent = evidence_text.find_parent()
        while parent and parent.name not in ['div', 'section']:
            parent = parent.find_parent()
        if parent:
            print(f"  {parent.get_text(strip=True)[:800]}")
    
    # Look for statistics or numbers
    print("\n\n📈 STATISTICS:")
    print("-" * 70)
    numbers = soup.find_all(string=re.compile(r'\d+%|\d+\s*patients|\d+\s*out of'))
    for num in numbers[:5]:
        context = num.find_parent()
        if context:
            print(f"  • {context.get_text(strip=True)}")
    
    # Check UI elements
    print("\n\n🎨 UI ELEMENTS:")
    print("-" * 70)
    
    # Check for icons/badges
    if soup.find('svg'):
        print("  ✓ SVG icons present")
    
    # Check for buttons
    buttons = soup.find_all(['button', 'a'], class_=re.compile(r'btn|button'))
    if buttons:
        print(f"  ✓ Found {len(buttons)} interactive buttons/links")
    
    # Check for styling classes
    if soup.find(class_=re.compile(r'bg-|text-|border-')):
        print("  ✓ Tailwind CSS classes detected")
    
    # Check for restart link
    restart = soup.find('a', href=re.compile(r'/(restart|$)'))
    if restart:
        print(f"  ✓ Restart link found: '{restart.get_text(strip=True)}'")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    run_scenario_and_get_results()
