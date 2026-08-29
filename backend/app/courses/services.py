from django.db import transaction
from django.core.exceptions import ValidationError

from .models import (
    CourseQuestion, CourseChoice, MatchingPair,
    ArrangeItem, Blank, BlankAnswer
)


class QuestionCreateService:
    """Savol yaratish uchun service layer"""

    @transaction.atomic
    def create(self, *, user, form_data, choice_data=None, matching_data=None,
               arrange_data=None, blank_data=None):
        """
        Barcha savol turlarini yaratish.

        Args:
            user: Yaratuvchi foydalanuvchi
            form_data: tozalangan QuestionCreateForm ma'lumotlari
            choice_data: ChoiceFormSet tozalangan ma'lumotlari (MULTIPLE_CHOICE)
            matching_data: MatchingPairFormSet tozalangan ma'lumotlari (MATCHING)
            arrange_data: ArrangeItemFormSet tozalangan ma'lumotlari (ARRANGE_WORDS)
            blank_data: BlankFormSet tozalangan ma'lumotlari (FILL_BLANKS)
        """
        question_type = form_data['question_type']

        # 1. Asosiy savolni yaratish
        question = CourseQuestion.objects.create(
            text=form_data['text'],
            question_type=question_type,
            difficulty=form_data['difficulty'],
            xp=form_data['xp'],
            explanation=form_data.get('explanation', ''),
            lesson=form_data.get('lesson'),
            test=form_data.get('test'),
            owner=user,
        )

        # 2. Turga qarab bolalarni yaratish
        if question_type == 'MULTIPLE_CHOICE':
            self._create_choices(question, choice_data)
        elif question_type == 'MATCHING':
            self._create_matching_pairs(question, matching_data)
        elif question_type == 'ARRANGE_WORDS':
            self._create_arrange_items(question, arrange_data)
        elif question_type == 'FILL_BLANKS':
            self._create_blanks(question, blank_data)

        return question

    def _create_choices(self, question, choice_data):
        """Multiple Choice variantlarini yaratish"""
        if not choice_data:
            raise ValidationError("Kamida 2 ta variant kiriting.")

        valid_choices = [c for c in choice_data if c.get('text', '').strip() and not c.get('DELETE', False)]

        if len(valid_choices) < 2:
            raise ValidationError("Kamida 2 ta to'liq variant bo'lishi kerak.")

        correct_count = sum(1 for c in valid_choices if c.get('is_correct'))
        if correct_count == 0:
            raise ValidationError("Kamida 1 ta to'g'ri javob belgilang.")

        for i, choice in enumerate(valid_choices):
            CourseChoice.objects.create(
                question=question,
                text=choice['text'].strip(),
                is_correct=choice.get('is_correct', False),
                owner=question.owner,
            )

    def _create_matching_pairs(self, question, matching_data):
        """Matching juftliklarini yaratish"""
        if not matching_data:
            raise ValidationError("Kamida 2 ta juftlik kiriting.")

        valid_pairs = [p for p in matching_data 
                       if p.get('left', '').strip() and p.get('right', '').strip() 
                       and not p.get('DELETE', False)]

        if len(valid_pairs) < 2:
            raise ValidationError("Kamida 2 ta to'liq juftlik bo'lishi kerak.")

        for i, pair in enumerate(valid_pairs):
            MatchingPair.objects.create(
                question=question,
                left=pair['left'].strip(),
                right=pair['right'].strip(),
                order=i + 1,
            )

    def _create_arrange_items(self, question, arrange_data):
        """Arrange Words elementlarini yaratish"""
        if not arrange_data:
            raise ValidationError("Kamida 2 ta so'z kiriting.")

        valid_items = [item for item in arrange_data 
                       if item.get('text', '').strip() 
                       and not item.get('DELETE', False)]

        if len(valid_items) < 2:
            raise ValidationError("Kamida 2 ta so'z bo'lishi kerak.")

        positions = [item.get('correct_position') for item in valid_items]
        if None in positions or any(p < 1 for p in positions):
            raise ValidationError("Barcha so'zlarga to'g'ri pozitsiya belgilang.")

        if len(set(positions)) != len(positions):
            raise ValidationError("Pozitsiyalar takrorlanmas bo'lishi kerak.")

        for item in valid_items:
            ArrangeItem.objects.create(
                question=question,
                text=item['text'].strip(),
                correct_position=item['correct_position'],
            )

    def _create_blanks(self, question, blank_data):
        """Fill Blanks bo'sh joylarini yaratish"""
        if not blank_data:
            raise ValidationError("Kamida 1 ta bo'sh joy kiriting.")

        valid_blanks = [b for b in blank_data 
                        if b.get('answers', '').strip() 
                        and not b.get('DELETE', False)]

        if not valid_blanks:
            raise ValidationError("Kamida 1 ta bo'sh joy bo'lishi kerak.")

        for blank_item in valid_blanks:
            blank = Blank.objects.create(
                question=question,
                position=blank_item.get('position', 1),
                case_sensitive=blank_item.get('case_sensitive', False),
            )

            # Vergul bilan ajratilgan javoblarni yaratish
            answers = [a.strip() for a in blank_item['answers'].split(',') if a.strip()]
            if not answers:
                raise ValidationError(f"Bo'sh joy #{blank.position} uchun kamida 1 ta javob kiriting.")

            for ans in answers:
                BlankAnswer.objects.create(
                    blank=blank,
                    answer=ans,
                )