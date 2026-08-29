from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from unfold.views import UnfoldModelAdminViewMixin

from .forms import (
    QuestionCreateForm, ChoiceFormSet, MatchingPairFormSet,
    ArrangeItemFormSet, BlankFormSet
)
from .models import CourseQuestion, Lesson, CourseTest
from .services import QuestionCreateService


class CreateQuestionView(UnfoldModelAdminViewMixin, FormView):
    """
    Unfold Custom Page - Yangi savol yaratish.
    Sidebar va header avtomatik saqlanadi.
    """
    title = "Yangi savol yaratish"
    permission_required = ("courses.add_coursequestion",)
    template_name = "admin/courses/question/create.html"
    form_class = QuestionCreateForm
    success_url = reverse_lazy("admin:courses_coursequestion_changelist")

    def get_form(self, form_class=None):
        """Formaga queryset'larni sozlash"""
        form = super().get_form(form_class)
        request = self.request

        # Foydalanuvchiga tegishli lesson va testlarni filtrlash
        if not request.user.is_superuser:
            form.fields['lesson'].queryset = Lesson.objects.filter(
                owner=request.user
            ).select_related('modul__course')
            form.fields['test'].queryset = CourseTest.objects.filter(
                owner=request.user
            ).select_related('modul__course')
        else:
            form.fields['lesson'].queryset = Lesson.objects.all().select_related('modul__course')
            form.fields['test'].queryset = CourseTest.objects.all().select_related('modul__course')

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context['choice_formset'] = ChoiceFormSet(self.request.POST, prefix='choices')
            context['matching_formset'] = MatchingPairFormSet(self.request.POST, prefix='matching')
            context['arrange_formset'] = ArrangeItemFormSet(self.request.POST, prefix='arrange')
            context['blank_formset'] = BlankFormSet(self.request.POST, prefix='blanks')
        else:
            context['choice_formset'] = ChoiceFormSet(prefix='choices')
            context['matching_formset'] = MatchingPairFormSet(prefix='matching')
            context['arrange_formset'] = ArrangeItemFormSet(prefix='arrange')
            context['blank_formset'] = BlankFormSet(prefix='blanks')

        # Unfold breadcrumb va title
        context['title'] = self.title
        context['subtitle'] = "Yangi test savolini yaratish"

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        question_type = form.cleaned_data['question_type']

        # Turga qarab tegishli formsetni tekshirish
        formsets = {
            'MULTIPLE_CHOICE': ('choice_formset', context['choice_formset']),
            'MATCHING': ('matching_formset', context['matching_formset']),
            'ARRANGE_WORDS': ('arrange_formset', context['arrange_formset']),
            'FILL_BLANKS': ('blank_formset', context['blank_formset']),
        }

        target_name, target_formset = formsets.get(question_type, (None, None))

        if target_formset and not target_formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        try:
            service = QuestionCreateService()

            # Turga qarab ma'lumotlarni olish
            kwargs = {
                'user': self.request.user,
                'form_data': form.cleaned_data,
            }

            if question_type == 'MULTIPLE_CHOICE':
                kwargs['choice_data'] = target_formset.cleaned_data
            elif question_type == 'MATCHING':
                kwargs['matching_data'] = target_formset.cleaned_data
            elif question_type == 'ARRANGE_WORDS':
                kwargs['arrange_data'] = target_formset.cleaned_data
            elif question_type == 'FILL_BLANKS':
                kwargs['blank_data'] = target_formset.cleaned_data

            question = service.create(**kwargs)

            messages.success(
                self.request,
                f"✅ Savol #{question.id} muvaffaqiyatli yaratildi! ({question.get_question_type_display()})",
            )
            return redirect('admin:courses_coursequestion_change', question.id)

        except Exception as e:
            messages.error(self.request, f"❌ Xatolik: {str(e)}")
            return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        messages.warning(self.request, "Formada xatoliklar bor. Iltimos, tekshiring.")
        return super().form_invalid(form)