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

# --- AI Model Configuration ---
# This uses the key we loaded in settings.py
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- Helper function to make text safe for LaTeX ---
def escape_latex(text):
    conv = {
        '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', 
        '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', 
        '^': r'\textasciicircum{}', '\\': r'\textbackslash{}'
    }
    regex = re.compile('|'.join(re.escape(str(key)) for key in conv.keys()))
    return regex.sub(lambda match: conv[match.group()], text)

# --- View for Teachers to Save a New Quiz ---
def save_quiz_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_quiz = Quiz.objects.create(
                title=data.get('title'),
                class_name=data.get('class_name')
            )
            questions_data = data.get('questions', [])
            for q_data in questions_data:
                Question.objects.create(
                    quiz=new_quiz,
                    text=q_data.get('q'),
                    options=q_data.get('options'),
                    correct_index=q_data.get('correctIndex')
                )
            return JsonResponse({'status': 'success', 'access_code': new_quiz.access_code})
        except Exception as e:
            print("!!! SAVE QUIZ ERROR:", e)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# --- View for Students to See a Quiz ---
def quiz_display_view(request, access_code):
    quiz = get_object_or_404(Quiz, access_code=access_code.upper())
    questions_for_js = []
    for question in quiz.questions.all():
        questions_for_js.append({
            "text": question.text,
            "answers": question.options,
        })
    context = {
        'quiz': quiz,
        'questions_for_js': questions_for_js,
    }
    return render(request, 'quiz_app/quiz_display.html', context)

# --- View to Handle Submission and Automatic Email ---
def submit_quiz_view(request):
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
                f"A student needs help with a '{quiz.title}' quiz. "
                f"They answered these questions incorrectly:\n\n"
    
            )
            for q in wrong_questions:
                prompt_text += f"- Question: {q.text}\n"
            prompt_text += (
                "\nPlease generate a simple, friendly study guide explaining "
                "the key concepts for these questions."
                "Do Not over-explain"
                "Make sure the explaination is well formated, and questions are seperated"
                "NOTE: Add at least three four questions"
                "Make sure your not hinting that you are an AI MODEL so limit greetings and outros, just study guide"
                "IMPORTANT: The entire response must be plain text only, with no Markdown formatting (no ##, *, or lists) or anything thats not plain text"
            )

            ai_response = model.generate_content(prompt_text)
            latex_source = f"""
            \\documentclass{{article}}
            \\title{{Your Personalized Study Guide for: {escape_latex(quiz.title)}}}
            \\author{{{escape_latex(new_submission.student_name)}}}
            \\begin{{document}}
            \\maketitle
            {escape_latex(ai_response.text)}
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
                    body=f"Hello {new_submission.student_name},\n\nHere is your study guide based on the questions you missed. Keep up the great work!",
                    from_email='study-guides@smartstudy.com',
                    to=[new_submission.student_email],
                )
                email.attach_file(pdf_filename)
                email.send()
        
        return JsonResponse({'status': 'success', 'message': 'Submission saved and guide sent!'})
        
    except Exception as e:
        print("!!! SERVER ERROR:", e)
        return JsonResponse({'error': str(e)}, status=400)