"""
Test script for the triage app.
Simulates a complete patient scenario through the web interface.
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional

BASE_URL = "http://localhost:5001"

class TriageAppTester:
    """
    Automated tester for the triage application.
    Simulates a user walking through the interview flow.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.issues = []
        self.successes = []
        
    def log_success(self, message: str):
        """Record a successful test step."""
        print(f"✓ {message}")
        self.successes.append(message)
        
    def log_issue(self, message: str):
        """Record a test issue or failure."""
        print(f"✗ {message}")
        self.issues.append(message)
        
    def test_welcome_page(self) -> bool:
        """Test the welcome page loads correctly."""
        print("\n=== Testing Welcome Page ===")
        try:
            response = self.session.get(f"{BASE_URL}/")
            
            if response.status_code != 200:
                self.log_issue(f"Welcome page returned status {response.status_code}")
                return False
            
            self.log_success(f"Welcome page loaded (status {response.status_code})")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for key elements
            if soup.find('h1', string=re.compile(r'Should I Go to the ER')):
                self.log_success("Found main heading")
            else:
                self.log_issue("Main heading not found")
                
            if soup.find('input', {'type': 'checkbox', 'id': 'consent'}):
                self.log_success("Found consent checkbox")
            else:
                self.log_issue("Consent checkbox not found")
                
            if soup.find('form', {'action': '/start'}):
                self.log_success("Found start form")
            else:
                self.log_issue("Start form not found")
                
            # Check for warning notice
            if 'medical emergency' in response.text.lower():
                self.log_success("Found emergency warning text")
            else:
                self.log_issue("Emergency warning text not found")
                
            return True
            
        except Exception as e:
            self.log_issue(f"Error loading welcome page: {e}")
            return False
    
    def start_interview(self) -> bool:
        """Accept consent and start the interview."""
        print("\n=== Starting Interview ===")
        try:
            response = self.session.post(
                f"{BASE_URL}/start",
                data={'consent': 'on'},
                allow_redirects=True
            )
            
            if response.status_code != 200:
                self.log_issue(f"Start returned status {response.status_code}")
                return False
                
            if '/interview' not in response.url:
                self.log_issue(f"Did not redirect to interview page (got {response.url})")
                return False
                
            self.log_success("Started interview successfully")
            return True
            
        except Exception as e:
            self.log_issue(f"Error starting interview: {e}")
            return False
    
    def answer_question(self, question_data: Dict) -> Optional[str]:
        """
        Answer a question and return the next question ID.
        question_data should contain 'answer' and may contain 'answer_label'.
        """
        try:
            # Get current interview page to extract question details
            response = self.session.get(f"{BASE_URL}/interview")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract question ID and type from form
            form = soup.find('form', {'action': '/answer'})
            if not form:
                self.log_issue("Could not find answer form")
                return None
                
            qid_input = form.find('input', {'name': 'question_id'})
            qtype_input = form.find('input', {'name': 'question_type'})
            qtext_input = form.find('input', {'name': 'question_text'})
            
            if not all([qid_input, qtype_input, qtext_input]):
                self.log_issue("Missing question metadata in form")
                return None
                
            qid = qid_input.get('value')
            qtype = qtype_input.get('value')
            qtext = qtext_input.get('value')
            
            # Prepare form data
            form_data = {
                'question_id': qid,
                'question_type': qtype,
                'question_text': qtext,
            }
            
            # Add answer based on question type
            if qtype == 'multi_choice':
                # For multi-choice, answer should be a list
                answers = question_data.get('answer', [])
                if not isinstance(answers, list):
                    answers = [answers]
                form_data['answer'] = answers
                
                # Add labels if provided
                labels = question_data.get('answer_label', [])
                if labels:
                    if not isinstance(labels, list):
                        labels = [labels]
                    form_data['answer_label'] = labels
            else:
                form_data['answer'] = question_data.get('answer', '')
            
            # Submit answer
            response = self.session.post(
                f"{BASE_URL}/answer",
                data=form_data,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                self.log_issue(f"Answer submission returned status {response.status_code}")
                return None
                
            self.log_success(f"Answered question '{qid}': {question_data.get('answer')}")
            
            # Check if we're at results or another question
            if '/results' in response.url:
                return 'RESULTS'
            elif '/interview' in response.url:
                return 'CONTINUE'
            else:
                self.log_issue(f"Unexpected redirect after answer: {response.url}")
                return None
                
        except Exception as e:
            self.log_issue(f"Error answering question: {e}")
            return None
    
    def get_current_question(self) -> Optional[Dict]:
        """Extract current question details from interview page."""
        try:
            response = self.session.get(f"{BASE_URL}/interview")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            form = soup.find('form', {'action': '/answer'})
            if not form:
                return None
                
            qid_input = form.find('input', {'name': 'question_id'})
            qtype_input = form.find('input', {'name': 'question_type'})
            qtext_input = form.find('input', {'name': 'question_text'})
            
            if not all([qid_input, qtype_input, qtext_input]):
                return None
                
            return {
                'id': qid_input.get('value'),
                'type': qtype_input.get('value'),
                'text': qtext_input.get('value'),
            }
            
        except Exception as e:
            self.log_issue(f"Error getting current question: {e}")
            return None
    
    def run_patient_scenario(self):
        """
        Run a complete patient scenario:
        - 55 year old male
        - Chest pain and trouble breathing
        - Diabetes and high blood pressure
        - Pressure/squeezing chest pain with radiation
        """
        print("\n=== Running Patient Scenario ===")
        print("Patient: 55-year-old male with chest pain and trouble breathing")
        print("History: Diabetes, High Blood Pressure\n")
        
        # Answer age
        q = self.get_current_question()
        if q and q['id'] == 'age':
            print(f"Question: {q['text']}")
            result = self.answer_question({'answer': '55'})
            if not result:
                return False
        
        # Answer sex
        q = self.get_current_question()
        if q and q['id'] == 'sex':
            print(f"Question: {q['text']}")
            result = self.answer_question({'answer': 'M', 'answer_label': 'Male'})
            if not result:
                return False
        
        # Answer symptoms
        q = self.get_current_question()
        if q and q['id'] == 'symptoms':
            print(f"Question: {q['text']}")
            result = self.answer_question({
                'answer': ['chest_pain', 'sob'],
                'answer_label': ['Chest Pain', 'Trouble Breathing']
            })
            if not result:
                return False
        
        # Answer medical history
        q = self.get_current_question()
        if q and q['id'] == 'pmh':
            print(f"Question: {q['text']}")
            result = self.answer_question({
                'answer': ['diabetes', 'hypertension'],
                'answer_label': ['Diabetes', 'High Blood Pressure']
            })
            if not result:
                return False
        
        # Continue answering follow-up questions until we reach results
        max_questions = 20
        question_count = 4
        
        while question_count < max_questions:
            q = self.get_current_question()
            if not q:
                break
                
            print(f"Question: {q['text']}")
            
            # Provide reasonable answers based on question ID patterns
            if 'quality' in q['id'].lower() or 'pain_type' in q['id'].lower():
                result = self.answer_question({
                    'answer': 'pressure',
                    'answer_label': 'Pressure or squeezing'
                })
            elif 'radiation' in q['id'].lower() or 'radiate' in q['text'].lower():
                result = self.answer_question({
                    'answer': 'yes',
                    'answer_label': 'Yes'
                })
            elif 'severity' in q['id'].lower():
                result = self.answer_question({
                    'answer': 'severe',
                    'answer_label': 'Severe (7-10)'
                })
            elif 'duration' in q['id'].lower():
                result = self.answer_question({
                    'answer': 'hours',
                    'answer_label': 'Hours'
                })
            else:
                # Default to first option for other questions
                result = self.answer_question({'answer': 'yes', 'answer_label': 'Yes'})
            
            if result == 'RESULTS':
                self.log_success("Reached results page")
                break
            elif result == 'CONTINUE':
                question_count += 1
                continue
            else:
                self.log_issue("Failed to process question")
                return False
        
        return True
    
    def test_results_page(self) -> bool:
        """Test the results page displays correctly."""
        print("\n=== Testing Results Page ===")
        try:
            response = self.session.get(f"{BASE_URL}/results")
            
            if response.status_code != 200:
                self.log_issue(f"Results page returned status {response.status_code}")
                return False
            
            self.log_success(f"Results page loaded (status {response.status_code})")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for recommendation
            if soup.find(string=re.compile(r'(Emergency|Urgent|Primary|Call)')):
                self.log_success("Found care recommendation")
            else:
                self.log_issue("Care recommendation not found")
            
            # Check for evidence section
            if 'evidence' in response.text.lower() or 'similar patients' in response.text.lower():
                self.log_success("Found evidence section")
            else:
                self.log_issue("Evidence section not found")
            
            # Check for restart option
            if soup.find('a', {'href': '/restart'}) or soup.find('a', {'href': '/'}):
                self.log_success("Found restart/start over link")
            else:
                self.log_issue("Restart link not found")
            
            return True
            
        except Exception as e:
            self.log_issue(f"Error testing results page: {e}")
            return False
    
    def run_full_test(self):
        """Run the complete test suite."""
        print("=" * 60)
        print("TRIAGE APP AUTOMATED TEST")
        print("=" * 60)
        
        # Test welcome page
        if not self.test_welcome_page():
            print("\n❌ Welcome page test failed. Stopping.")
            return
        
        # Start interview
        if not self.start_interview():
            print("\n❌ Failed to start interview. Stopping.")
            return
        
        # Run patient scenario
        if not self.run_patient_scenario():
            print("\n❌ Patient scenario failed. Stopping.")
            return
        
        # Test results page
        self.test_results_page()
        
        # Print summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"✓ Successes: {len(self.successes)}")
        print(f"✗ Issues: {len(self.issues)}")
        
        if self.issues:
            print("\nIssues found:")
            for issue in self.issues:
                print(f"  - {issue}")
        else:
            print("\n🎉 All tests passed!")
        
        print("=" * 60)


if __name__ == "__main__":
    tester = TriageAppTester()
    tester.run_full_test()
