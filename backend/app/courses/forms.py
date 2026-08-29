from django import forms
from django.core.exceptions import ValidationError
from django.forms import formset_factory, inlineformset_factory

from .models import (
    CourseQuestion, CourseChoice, MatchingPair,
    ArrangeItem, Blank, BlankAnswer
)


class QuestionCreateForm(forms.ModelForm):
    """Asosiy savol formasi"""

    QUESTION_TYPE_CHOICES = [
        ('MULTIPLE_CHOICE', '🔘 Multiple Choice'),
        ('MATCHING', '🔗 Matching'),
        ('ARRANGE_WORDS', '🔤 Arrange Words'),
        ('FILL_BLANKS', '◻️ Fill in the Blanks'),
    ]

    DIFFICULTY_CHOICES = [
        ('easy', '🟢 Easy'),
        ('medium', '🟡 Medium'),
        ('hard', '🔴 Hard'),
    ]

    question_type = forms.ChoiceField(
        choices=QUESTION_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-full',
            'id': 'id_question_type',
            'onchange': 'toggleQuestionTypeFields()',
        }),
        label="Savol turi",
    )

    difficulty = forms.ChoiceField(
        choices=DIFFICULTY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-full',
        }),
        label="Qiyinchilik",
        initial='medium',
    )

    text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-full',
            'rows': 4,
            'placeholder': 'Savol matnini kiriting...',
        }),
        label="Savol matni",
    )

    explanation = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-full',
            'rows': 3,
            'placeholder': 'Tushuntirish (ixtiyoriy)...',
        }),
        label="Tushuntirish",
    )

    xp = forms.IntegerField(
        initial=10,
        widget=forms.NumberInput(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-full',
            'min': 0,
        }),
        label="XP (Tajriba ochkosi)",
    )

    lesson = forms.ModelChoiceField(
        queryset=None,  # view'da set qilinadi
        required=False,
        widget=forms.Select(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-full',
        }),
        label="Darslik (Lesson)",
        empty_label="--- Tanlang ---",
    )

    test = forms.ModelChoiceField(
        queryset=None,  # view'da set qilinadi
        required=False,
        widget=forms.Select(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-full',
        }),
        label="Test",
        empty_label="--- Tanlang ---",
    )

    class Meta:
        model = CourseQuestion
        fields = ['text', 'question_type', 'difficulty', 'xp', 'explanation', 'lesson', 'test']

    def clean(self):
        cleaned_data = super().clean()
        lesson = cleaned_data.get('lesson')
        test = cleaned_data.get('test')

        if lesson and test:
            raise ValidationError("Savol faqat Lesson YOKI Testga tegishli bo'lishi kerak. Ikkisiga birdan emas!")
        if not lesson and not test:
            raise ValidationError("Kamida bitta Lesson yoki Test tanlang.")

        return cleaned_data


# --- Formsetlar uchun yordamchi formalar ---

class ChoiceForm(forms.Form):
    text = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-full',
            'placeholder': 'Variant matni...',
        }),
        label=False,
    )
    is_correct = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-blue-600 rounded focus:ring-blue-500',
        }),
        label=False,
    )


class MatchingPairForm(forms.Form):
    left = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-full',
            'placeholder': 'Chap tomon...',
        }),
        label=False,
    )
    right = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-full',
            'placeholder': 'O\'ng tomon...',
        }),
        label=False,
    )
    order = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(),
    )


class ArrangeItemForm(forms.Form):
    text = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-full',
            'placeholder': "So'z...",
        }),
        label=False,
    )
    correct_position = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-24',
            'min': 1,
            'placeholder': 'Pozitsiya',
        }),
        label=False,
    )


class BlankForm(forms.Form):
    position = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-24',
            'min': 1,
            'placeholder': 'Pozitsiya',
        }),
        label=False,
    )
    case_sensitive = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-blue-600 rounded',
        }),
        label=False,
    )
    answers = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'border border-gray-300 rounded px-3 py-2 w-full',
            'placeholder': 'Javoblarni vergul bilan ajrating: apple, Apple, APPLE',
        }),
        label=False,
        help_text="Bir nechta to'g'ri javob bo'lsa vergul bilan ajrating",
    )


# Formset factory'lar
ChoiceFormSet = formset_factory(ChoiceForm, extra=4, can_delete=True, min_num=2, max_num=10)
MatchingPairFormSet = formset_factory(MatchingPairForm, extra=3, can_delete=True, min_num=2, max_num=10)
ArrangeItemFormSet = formset_factory(ArrangeItemForm, extra=4, can_delete=True, min_num=2, max_num=15)
BlankFormSet = formset_factory(BlankForm, extra=2, can_delete=True, min_num=1, max_num=10)