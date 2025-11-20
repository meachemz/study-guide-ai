from django.db import models
import random
import string
from django.core.exceptions import ValidationError 


def generate_access_code():
    """Generates a unique 5-character uppercase alphanumeric code."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if not Quiz.objects.filter(access_code=code).exists():
            return code

class Quiz(models.Model):
    title = models.CharField(max_length=200)
    class_name = models.CharField(max_length=100, blank=True, null=True)
    access_code = models.CharField(max_length=5, unique=True, default=generate_access_code)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.access_code})"

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()
    options = models.JSONField()
    correct_index = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.text

    # --- ADD THIS ENTIRE METHOD ---
    def clean(self):
        """
        This is the validation logic that stops bad data.
        It runs automatically in the Django Admin.
        """
        super().clean()  # Always call this first

        # Check 1: Are options a valid list?
        if not isinstance(self.options, list) or len(self.options) == 0:
            raise ValidationError(
                {'options': 'You must provide a list of at least one option.'}
            )

        # Check 2: Is the index valid for the options list?
        if self.correct_index is None:
            raise ValidationError(
                {'correct_index': 'You must provide a correct index.'}
            )
            
        num_options = len(self.options)
        if not (0 <= self.correct_index < num_options):
            raise ValidationError(
                {
                    'correct_index': f"Invalid index ({self.correct_index}). "
                                     f"It must be between 0 and {num_options - 1}."
                }
            )