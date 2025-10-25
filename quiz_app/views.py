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


# --- AI Model Configuration ---
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

# --- Helper function for LaTeX ---
def escape_latex(text):
    conv = { '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}', '\\': r'\textbackslash{}'}
    regex = re.compile('|'.join(re.escape(str(key)) for key in conv.keys()))
    return regex.sub(lambda match: conv[match.group()], text)

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
    """
    Handles a POST request when a student submits their answers.
    Automatically generates and emails a PDF study guide if any answers are incorrect.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        quiz = Quiz.objects.get(access_code=data.get('access_code'))
        
        # 1. Save submission and calculate score
        student_answers = data.get('answers', {})
        score = 0
        questions = list(quiz.questions.all())
        for i, question in enumerate(questions):
            submitted_answer = student_answers.get(str(i))
            if submitted_answer and submitted_answer == question.options[question.correct_index]:
                score += 1
        
        new_submission = Submission.objects.create(
            quiz=quiz,
            student_name=data.get('name'),
            student_email=data.get('email'),
            answers=student_answers,
            score=score
        )

        # 2. Find incorrect questions to create a study guide
        wrong_questions = []
        for i, question in enumerate(questions):
            if student_answers.get(str(i)) != question.options[question.correct_index]:
                wrong_questions.append(question)
        
        # 3. If there were wrong answers, generate and email the guide
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
                "2. A 'Practice Questions' section below that contains one new, similar practice question for EACH of the incorrect questions. Each practice question should have four multiple-choice options (A, B, C, D) and you must clearly state the correct answer.\n\n"
                "IMPORTANT: The entire response must be plain text only, using new lines for formatting. Do not use Markdown (no ##, *, etc.)."
            )
            
            ai_response = model.generate_content(prompt_text)
            
            study_guide_text = ai_response.text
            escaped_text = escape_latex(study_guide_text)
            final_latex_body = escaped_text.replace('\n', '\\par ')

            latex_source = f"""
            \\documentclass{{article}}
            \\usepackage[utf8]{{inputenc}}
            \\title{{Your Personalized Study Guide for: {escape_latex(quiz.title)}}}
            \\author{{{escape_latex(new_submission.student_name)}}}
            \\begin{{document}}
            \\maketitle
            {final_latex_body}
            \\end{{document}}
            """
            
            with tempfile.TemporaryDirectory() as tempdir:
                tex_filename = os.path.join(tempdir, 'guide.tex')
                with open(tex_filename, 'w', encoding='utf-8') as f:
                    f.write(latex_source)
                
                subprocess.run(['pdflatex', '-output-directory', tempdir, tex_filename], check=True, capture_output=True)
                pdf_filename = os.path.join(tempdir, 'guide.pdf')

                email = EmailMessage(
                    subject=f"Your Personalized Study Guide for '{quiz.title}'",
                    body=f"Hello {new_submission.student_name},\n\nHere is your study guide based on the questions you missed. It includes explanations and new practice questions to help you prepare!",
                    from_email='study-guides@smartstudy.com',
                    to=[new_submission.student_email],
                )
                email.attach_file(pdf_filename)
                email.send()
        
        return JsonResponse({'status': 'success', 'message': 'Submission saved and guide sent!'})
        
    except Exception as e:
        print("!!! SERVER ERROR:", e)
        return JsonResponse({'error': str(e)}, status=400)