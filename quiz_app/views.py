# In quiz_app/views.py

# --- Required Imports ---
import json
import subprocess
import tempfile
import os
import re
import google.generativeai as genai
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.core.mail import EmailMessage
from .models import Quiz, Question, Submission
from django.db.models import Count
from django.shortcuts import render
from django.template.loader import render_to_string
from fpdf import FPDF


# --- AI Model Configuration ---
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

# --- Helper function to parse AI plain text study guide ---
# (This is a basic example, you might need a more robust parser)
def parse_study_guide_text(text):
    core_topics = ""
    practice_questions = []
    try:
        core_split = re.split(r'\nPractice Questions\n', text, maxsplit=1, flags=re.IGNORECASE)
        core_text_section = core_split[0]
        practice_text_section = core_split[1] if len(core_split) > 1 else ""
        core_topics = core_text_section.replace('Core Topics Explained\n', '', 1).strip()
        question_blocks = re.split(r'\n(?=\d+\.\s)', practice_text_section.strip())
        for block in question_blocks:
            if not block.strip(): continue
            lines = block.strip().split('\n')
            if len(lines) < 6: continue
            question_text = lines[0].split('.', 1)[1].strip()
            options = [opt[3:].strip() for opt in lines[1:5]] # Assumes A) B) C) D) format
            answer_line = lines[5]
            practice_questions.append({
                'text': question_text,
                'options': options,
            })
    except Exception as e:
        print(f"Error parsing study guide text: {e}")
        core_topics = text # Fallback
        practice_questions = []
    return core_topics, practice_questions

def teacher_dashboard_view(request):
    # This view's only job is to render the dashboard template
    return render(request, 'quiz_app/teacher_dashboard.html')

# --------------------------------------------------------------------------
# --- API VIEWS FOR TEACHER DASHBOARD ---
# --------------------------------------------------------------------------

def dashboard_data_view(request):
    """
    Handles a GET request to load all necessary data for the teacher dashboard.
    """
    quizzes = Quiz.objects.annotate(question_count=Count('questions')).order_by('-created_at')
    results = Submission.objects.order_by('-submitted_at').select_related('quiz')

    quizzes_data = [{
        'title': q.title,
        'code': q.access_code,
        'created_at': q.created_at,
        'question_count': q.question_count,
    } for q in quizzes]

    results_data = [{
        'student_name': r.student_name,
        'quiz_title': r.quiz.title,
        'quiz_code': r.quiz.access_code,
        'score': r.score,
        'total_questions': r.quiz.questions.count(),
        'study_guide_sent': True, # Placeholder, you can add a field to Submission model later
    } for r in results]

    return JsonResponse({'quizzes': quizzes_data, 'results': results_data})

def save_quiz_view(request):
    """
    Handles a POST request to save a manually created quiz.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_quiz = Quiz.objects.create(title=data.get('title'))
            
            for q_data in data.get('questions', []):
                Question.objects.create(
                    quiz=new_quiz,
                    text=q_data.get('q'),
                    options=q_data.get('options'),
                    correct_index=q_data.get('correctIndex')
                )
            return JsonResponse({'status': 'success', 'access_code': new_quiz.access_code})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

def delete_quiz_view(request):
    """
    Handles a POST request to delete a quiz by its access code.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            quiz_to_delete = get_object_or_404(Quiz, access_code=data.get('code'))
            quiz_to_delete.delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

def generate_ai_quiz_view(request):
    """
    Handles a POST request with topics to generate a quiz using the AI.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            subject = data.get('subject')
            subtopic = data.get('subtopic')
            gradelevel = data.get('gradelevel')
            count = data.get('count')

            # --- Prompt Engineering: Ask the AI for structured JSON ---
            prompt = (
                f"Help Generate a quiz for a teacher about {subject}: The teccher describes the unit being:{subtopic} with a gradelevel of {gradelevel}. "
                f"Create exactly {count} multiple-choice questions. "
                "Respond with ONLY a single, raw JSON object. Do not include '```json' or any other text before or after the object. "
                "The JSON object should have a single key 'questions', which is an array of objects. "
                "Each question object must have two keys: "
                "1. 'text' (string): The question text. "
                "2. 'options' (array of 4 strings): The possible answers. "
                "3. 'correctIndex' (integer from 0 to 3): The index of the correct answer in the 'options' array."
            )
            
            ai_response = model.generate_content(prompt)
            # Clean up the AI response to ensure it's valid JSON
            cleaned_text = ai_response.text.strip().replace('```json', '').replace('```', '')
            quiz_content = json.loads(cleaned_text)

            # Create and save the quiz to the database
            quiz_title = f"{subject}({gradelevel})"
            new_quiz = Quiz.objects.create(title=quiz_title)
            
            for q_data in quiz_content.get('questions', []):
                Question.objects.create(
                    quiz=new_quiz,
                    text=q_data.get('text'),
                    options=q_data.get('options'),
                    correct_index=q_data.get('correctIndex')
                )
            
            return JsonResponse({'status': 'success', 'code': new_quiz.access_code})

        except Exception as e:
            print("!!! AI GENERATION ERROR:", e)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# --------------------------------------------------------------------------
# --- VIEWS FOR STUDENT-FACING QUIZ ---
# --------------------------------------------------------------------------

def quiz_display_view(request, access_code):
    """
    Handles a GET request to display a quiz page to a student.
    """
    quiz = get_object_or_404(Quiz, access_code=access_code.upper())
    questions_for_js = []
    for question in quiz.questions.all():
        questions_for_js.append({"text": question.text, "answers": question.options})
    context = {'quiz': quiz, 'questions_for_js': questions_for_js}
    return render(request, 'quiz_app/quiz_display.html', context)

# In quiz_app/views.py

def parse_study_guide_text(text):
    """
    Parses the plain text AI response into a list of practice question data.
    
    Expects a format like:
    Fundamental Topic: [Topic Title]
    Practice Question: [Question Text]
    A) [Option A]
    B) [Option B]
    C) [Option C]
    D) [Option D]
    Correct Answer: [A, B, C, or D]
    """
    practice_questions_data = []
    
    # This regex finds all components for each question
    pattern = re.compile(
        r"Fundamental Topic:\s*(.*?)\n"       # 1. Topic
        r"Practice Question:\s*(.*?)\n"      # 2. Question Text
        r"A\)\s*(.*?)\n"                      # 3. Option A
        r"B\)\s*(.*?)\n"                      # 4. Option B
        r"C\)\s*(.*?)\n"                      # 5. Option C
        r"D\s*\)\s*(.*?)\n"                   # 6. Option D (added \s* for flexibility)
        r"Correct Answer:\s*([A-D])",         # 7. Answer (A, B, C, or D)
        re.DOTALL | re.MULTILINE | re.IGNORECASE
    )

    for match in pattern.finditer(text):
        # Unpack all 7 captured groups
        topic, question, opt_a, opt_b, opt_c, opt_d, answer = match.groups()
        
        practice_questions_data.append({
            'topic': topic.strip(),
            'text': question.strip(),
            'options': [opt_a.strip(), opt_b.strip(), opt_c.strip(), opt_d.strip()],
            'answer': answer.strip().upper()
        })
        
        # Stop after finding 5, as requested in the prompt
        if len(practice_questions_data) == 5:
            break 

    # --- UPDATED: This function ONLY returns practice questions ---
    return practice_questions_data

# ---
# Your UPDATED view function
# ---
def submit_quiz_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        quiz = Quiz.objects.get(access_code=data.get('access_code'))
        student_name = data.get('name')
        student_email = data.get('email')
        student_answers = data.get('answers', {})

        # 1. Save submission and score (Same as before)
        score = 0
        questions = list(quiz.questions.all())
        for i, question in enumerate(questions):
            submitted_answer_text = student_answers.get(str(i))
            if submitted_answer_text and submitted_answer_text == question.options[question.correct_index]:
                score += 1

        new_submission = Submission.objects.create(
            quiz=quiz,
            student_name=student_name,
            student_email=student_email,
            answers=student_answers,
            score=score
        )

        # 2. Find incorrect questions (Same as before)
        wrong_questions = []
        for i, question in enumerate(questions):
             submitted_answer_text = student_answers.get(str(i))
             if submitted_answer_text != question.options[question.correct_index]:
                 wrong_questions.append(question)

        # 3. If wrong answers, generate guide text using AI
        if wrong_questions:
            
            # --- NEW: Simplified AI Prompt ---
            prompt_text = "The following are questions a student answered incorrectly:\n\n"
            for q in wrong_questions:
                prompt_text += f"- Question: {q.text}\n"
            
            prompt_text += (
                "\nPlease generate exactly five practice questions based on the topics from the questions above.\n\n"
                "For EACH of the five questions, you MUST provide the following in plain text:\n"
                "1. A 'Fundamental Topic' title (e.g., 'Fundamental Topic: Newton's Second Law').\n"
                "2. The 'Practice Question' text (e.g., 'Practice Question: What is...').\n"
                "3. Four multiple-choice options (labeled A), B), C), D)).\n"
                "4. The 'Correct Answer' (e.g., 'Correct Answer: A').\n\n"
                "IMPORTANT: The entire response must be plain text only. Do not use Markdown (no ##, *, etc.)."
                "Format each question clearly with these labels."
            )
            
            ai_response = model.generate_content(prompt_text)
            study_guide_text = ai_response.text

            # --- UPDATED: Parse AI text ---
            # The new parser only returns practice_questions_data
            practice_questions_data = parse_study_guide_text(study_guide_text)

            # --- Generate PDF using fpdf2 ---
            pdf = FPDF()
            pdf.add_page()
            
            try:
                 pdf.set_font("helvetica", size=12)
            except RuntimeError:
                 print("Warning: Using default PDF font, Unicode characters might not render correctly.")
                 pdf.set_font("helvetica", size=12) 

            # --- Write content to PDF ---
            # Title
            pdf.set_font(style='B', size=16)
            pdf.cell(0, 10, f"Study Guide for: {quiz.title}".encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
            pdf.ln(5) 

            # Student Name
            pdf.set_font(style='', size=12)
            pdf.cell(0, 10, f"Student: {student_name}".encode('latin-1', 'replace').decode('latin-1'), ln=True)
            pdf.ln(10)

            # --- REMOVED: Core Topics section ---

            # --- UPDATED: Practice Questions section ---
            pdf.set_font(style='B', size=14)
            pdf.cell(0, 10, "Practice Questions".encode('latin-1', 'replace').decode('latin-1'), ln=True)
            pdf.set_font(style='', size=12)
            pdf.ln(5) # Add a little space before the first question

            for i, pq in enumerate(practice_questions_data):
                # --- ADDED: Fundamental Topic ---
                pdf.set_font(style='B', size=12) # Bold topic
                pdf.multi_cell(0, 5, f"{i + 1}. Fundamental Topic: {pq['topic']}".encode('latin-1', 'replace').decode('latin-1'))
                pdf.ln(2)

                # --- Question Text ---
                pdf.set_font(style='', size=12) # Regular question text
                pdf.multi_cell(0, 5, f"   Question: {pq['text']}".encode('latin-1', 'replace').decode('latin-1'))
                pdf.ln(2) 
                
                # --- Options ---
                options_text = ""
                option_labels = ['A', 'B', 'C', 'D']
                for j, option in enumerate(pq['options']):
                    options_text += f"      {option_labels[j]}) {option}\n"
                pdf.multi_cell(0, 5, options_text.strip().encode('latin-1', 'replace').decode('latin-1'))
                pdf.ln(2)

                # --- ADDED: Correct Answer ---
                pdf.set_text_color(0, 128, 0) # Green color for answer
                pdf.set_font(style='B')
                pdf.cell(0, 5, f"   Correct Answer: {pq['answer']}".encode('latin-1', 'replace').decode('latin-1'), ln=True)
                pdf.set_text_color(0, 0, 0) # Reset color to black
                pdf.set_font(style='')
                pdf.ln(8) # Space between questions

            # --- Save PDF to temp file and email (Same as before) ---
            with tempfile.TemporaryDirectory() as tempdir:
                pdf_filename = os.path.join(tempdir, 'study_guide.pdf')
                pdf.output(pdf_filename) # Save the PDF

                # --- Email the PDF (Same as before) ---
                email = EmailMessage(
                    subject=f"Your Personalized Study Guide for '{quiz.title}'",
                    body=f"Hello {student_name},\n\nHere is your study guide based on the questions you missed...",
                    from_email='study-guides@smartstudy.com', # Use configured sender
                    to=[student_email],
                )
                email.attach_file(pdf_filename)
                try:
                    email.send()
                    print(f"Study guide PDF sent via fpdf2 to {student_email}")
                    message = 'Submission saved and study guide sent!'
                except Exception as mail_error:
                    print(f"!!! EMAIL SENDING ERROR: {mail_error}")
                    message = 'Submission saved, but failed to send study guide email.'

        else:
            message = 'Submission saved! Great job!'

        return JsonResponse({'status': 'success', 'message': message})

    except Quiz.DoesNotExist:
         print(f"!!! SERVER ERROR: Quiz not found for access code {data.get('access_code')}")
         return JsonResponse({'error': 'Quiz not found'}, status=404)
    except Exception as e:
        print(f"!!! SUBMISSION/PDF ERROR: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': 'An internal error occurred.'}, status=500)