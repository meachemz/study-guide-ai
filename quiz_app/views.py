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
from weasyprint import HTML


# --- AI Model Configuration ---
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

# --- Helper function to parse AI plain text study guide ---
# (This is a basic example, you might need a more robust parser)
def parse_study_guide_text(text):
    core_topics = ""
    practice_questions = []

    try:
        # Find sections (adjust keywords based on your prompt)
        core_split = re.split(r'\nPractice Questions\n', text, maxsplit=1, flags=re.IGNORECASE)
        core_text_section = core_split[0]
        practice_text_section = core_split[1] if len(core_split) > 1 else ""

        # Extract core topics text
        core_topics = core_text_section.replace('Core Topics Explained\n', '', 1).strip()

        # Extract practice questions (this is complex and needs refinement)
        # Assuming format like: "1. Question text\nA) Opt1\nB) Opt2\nC) Opt3\nD) Opt4\nCorrect Answer: C"
        question_blocks = re.split(r'\n(?=\d+\.\s)', practice_text_section.strip()) # Split by lines starting with "Number."

        for block in question_blocks:
            if not block.strip(): continue
            lines = block.strip().split('\n')
            if len(lines) < 6: continue # Need at least question, 4 options, answer

            question_text = lines[0].split('.', 1)[1].strip() # Remove number like "1. "
            options = [opt[3:].strip() for opt in lines[1:5]] # Remove A) B) C) D)
            answer_line = lines[5]
            correct_answer_text = answer_line.replace('Correct Answer:', '').strip()

            practice_questions.append({
                'text': question_text,
                'options': options,
                'correct_answer_text': correct_answer_text
            })

    except Exception as e:
        print(f"Error parsing study guide text: {e}")
        # Fallback: return the raw text if parsing fails
        core_topics = text
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
            difficulty = data.get('difficulty')
            count = data.get('count')

            # --- Prompt Engineering: Ask the AI for structured JSON ---
            prompt = (
                f"Generate a quiz about {subject}: {subtopic} with a difficulty of {difficulty}. "
                f"Create exactly {count} multiple-choice questions. "
                "Respond with ONLY a single, raw JSON object. Do not include '```json' or any other text before or after the object. "
                "The JSON object should have a single key 'questions', which is an array of objects. "
                "Each question object must have three keys: "
                "1. 'text' (string): The question text. "
                "2. 'options' (array of 4 strings): The possible answers. "
                "3. 'correctIndex' (integer from 0 to 3): The index of the correct answer in the 'options' array."
            )
            
            ai_response = model.generate_content(prompt)
            # Clean up the AI response to ensure it's valid JSON
            cleaned_text = ai_response.text.strip().replace('```json', '').replace('```', '')
            quiz_content = json.loads(cleaned_text)

            # Create and save the quiz to the database
            quiz_title = f"{subject}: {subtopic} ({difficulty})"
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

def submit_quiz_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        quiz = Quiz.objects.get(access_code=data.get('access_code'))
        student_name = data.get('name')
        student_email = data.get('email')
        student_answers = data.get('answers', {})

        # 1. Save submission and calculate score (same as before)
        score = 0
        questions = list(quiz.questions.all())
        for i, question in enumerate(questions):
            submitted_answer_text = student_answers.get(str(i))
            # Compare submitted text with the correct option text
            if submitted_answer_text and submitted_answer_text == question.options[question.correct_index]:
                score += 1

        new_submission = Submission.objects.create(
            quiz=quiz,
            student_name=student_name,
            student_email=student_email,
            answers=student_answers,
            score=score
        )

        # 2. Find incorrect questions (same as before)
        wrong_questions = []
        for i, question in enumerate(questions):
            submitted_answer_text = student_answers.get(str(i))
            if submitted_answer_text != question.options[question.correct_index]:
                 wrong_questions.append(question)

        # 3. If wrong answers, generate guide using AI (same prompt)
        if wrong_questions:
            prompt_text = (
                f"A student needs a study guide for a '{quiz.title}' quiz. "
                f"They answered these questions incorrectly:\n\n"
            )
            for q in wrong_questions:
                prompt_text += f"- Question: {q.text}\n"
            prompt_text += (
                "\nPlease generate a study guide with two distinct sections:\n\n"
                "1. A single 'Core Topics Explained' section at the top that briefly summarizes the key concepts for all the incorrect questions combined.\n\n"
                "2. A 'Practice Questions' section below that contains one new, similar practice question for EACH of the incorrect questions. Each practice question should have four multiple-choice options (A, B, C, D) and you must clearly state the correct answer (e.g., 'Correct Answer: C').\n\n"
                "IMPORTANT: The entire response must be plain text only, using new lines for formatting. Do not use Markdown (no ##, *, etc.)."
            )

            ai_response = model.generate_content(prompt_text)
            study_guide_text = ai_response.text

            # --- NEW: Parse AI text and render HTML template ---
            core_topics, practice_questions_data = parse_study_guide_text(study_guide_text)

            context = {
                'quiz_title': quiz.title,
                'student_name': student_name,
                'core_topics_explained': core_topics,
                'practice_questions': practice_questions_data,
            }
            html_string = render_to_string('quiz_app/study_guide_template.html', context)

            # --- NEW: Generate PDF from HTML using WeasyPrint ---
            with tempfile.TemporaryDirectory() as tempdir:
                pdf_filename = os.path.join(tempdir, 'study_guide.pdf')
                HTML(string=html_string).write_pdf(pdf_filename)

                # --- Email the PDF (same as before) ---
                email = EmailMessage(
                    subject=f"Your Personalized Study Guide for '{quiz.title}'",
                    body=f"Hello {student_name},\n\nHere is your study guide based on the questions you missed. It includes explanations and new practice questions to help you prepare!",
                    from_email='study-guides@smartstudy.com', # Use a real sender email configured in settings.py
                    to=[student_email],
                )
                email.attach_file(pdf_filename)
                try:
                    email.send()
                    print(f"Study guide email sent successfully to {student_email}")
                    message = 'Submission saved and study guide sent!'
                except Exception as mail_error:
                    print(f"!!! EMAIL SENDING ERROR: {mail_error}")
                    # Decide if you should still return success or indicate email failure
                    message = 'Submission saved, but failed to send study guide email.'
                    # Optionally re-raise or handle differently

        else:
            # No wrong answers, no guide needed
            message = 'Submission saved! Great job!'

        return JsonResponse({'status': 'success', 'message': message})

    except Quiz.DoesNotExist:
         print(f"!!! SERVER ERROR: Quiz not found for access code {data.get('access_code')}")
         return JsonResponse({'error': 'Quiz not found'}, status=404)
    except Exception as e:
        print(f"!!! SUBMISSION/PDF ERROR: {type(e).__name__} - {e}")
        # Include traceback for debugging
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': 'An internal error occurred.'}, status=500) # Use 500 for server errors