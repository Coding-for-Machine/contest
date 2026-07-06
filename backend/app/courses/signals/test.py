# ── 4. TEST ───────────────────────────────────────────────────────────────────

@receiver(post_save, sender='quizs.Test')
def on_test_save(sender, instance, created, **kwargs):
    """modul_id None bo'lishi mumkin (mustaqil test) → tekshiriladi"""
    if not instance.modul_id:
        return
    try:
        course_id = _course_id_by_modul_id(instance.modul_id)
        if not course_id:
            return

        if created:
            Course.objects.filter(id=course_id).update(
                total_test_count=F('total_test_count') + 1
            )

        slug = _slug_by_course_id(course_id)
        if slug:
            invalidate_static(slug)
    except Exception as e:
        logger.error(f"on_test_save: {e}")


@receiver(pre_delete, sender='quizs.Test')
def on_test_delete(sender, instance, **kwargs):
    if not instance.modul_id:
        return
    try:
        course_id = _course_id_by_modul_id(instance.modul_id)
        if not course_id:
            return

        Course.objects.filter(id=course_id, total_test_count__gt=0).update(
            total_test_count=F('total_test_count') - 1
        )

        slug = _slug_by_course_id(course_id)
        if slug:
            invalidate_static(slug)
    except Exception as e:
        logger.warning(f"on_test_delete: {e}")