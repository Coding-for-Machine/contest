# Contest Platform — Complete Technical Architecture & Implementation Guide

> **Production-Grade Django Bolt + DRF REST API Design**
> 
> Real database models, signals, serializers, and API design patterns with examples

---

## 📊 Database Layer — Complete Schema

### User Authentication & Profile

```python
# baseuser/models.py
class BaseUser(models.Model):
    """Student users (OTP-based, no registration)"""
    
    # Primary Key
    telegram_id      : BigInteger (unique, db_index)
    
    # Identity
    username         : CharField[150] (unique, nullable)
    phone            : CharField[20] (nullable)
    full_name        : CharField[255] (nullable)
    
    # Status
    is_active        : Boolean (default=True)
    last_login       : DateTime (nullable)
    
    # Timestamps
    created_at       : DateTime (auto_now_add)
    updated_at       : DateTime (auto_now)
    
    # Signals:
    # - post_save: Create UserStats if first submission
    # - pre_delete: Archive user data to history table
    
    db_table: 'users'
    
class Profile(models.Model):
    """Extended profile for both students and admin users"""
    
    django_user      : OneToOneField → User (nullable)
    student_user     : OneToOneField → BaseUser (nullable)
    avatar           : ImageField (upload_to='avatars/')
    bio              : TextField (max_length=500, nullable)
    website          : URLField (nullable)
    
    db_table: 'user_profiles'
```

### Problem Management System

```python
# problems/models.py

class Category(models.Model):
    """Problem grouping"""
    name             : CharField[250] (unique)
    slug             : SlugField[500] (unique)
    owner            : ForeignKey → User
    
    # Example categories:
    # "Algorithms", "Data Structures", "Dynamic Programming", 
    # "Graph Theory", "Number Theory"

class Tags(models.Model):
    """Problem tags for filtering"""
    name             : CharField[50] (unique)  # 'arrays', 'greedy', 'bfs', etc.
    owner            : ForeignKey → User

class Language(models.Model):
    """Supported programming languages (Piston)"""
    name             : CharField[250] (unique)  # 'python', 'javascript', 'cpp'
    version          : CharField[50]            # '3.10.0', '14.20.0'

class Problem(models.Model):
    """Core problem entity"""
    
    # Identity
    title            : CharField[200]
    slug             : SlugField[250] (unique)
    description      : MDTextField              # Markdown problem statement
    
    # Categorization & Filtering
    category         : ForeignKey → Category (nullable)
    tags             : ManyToMany → Tags
    difficulty       : Choice['easy', 'medium', 'hard']
    
    # Constraints
    time_limit       : Integer (default=2000, milliseconds)
    memory_limit     : Integer (default=256, MB)
    language         : ManyToMany → Language   # Allowed languages
    
    # Rewards
    xp               : PositiveInteger (10-100)
    likes_count      : PositiveInteger (read-only, auto-calc)
    dislikes_count   : PositiveInteger (read-only, auto-calc)
    
    # Relations
    lesson           : ForeignKey → Lesson (nullable)
    contest          : ForeignKey → Contest (nullable)
    solution_video   : ForeignKey → Video (nullable)
    
    # Status
    is_active        : Boolean (db_index)
    owner            : ForeignKey → User (admin creator)
    
    # Signals:
    # - pre_save: Generate slug from title
    # - pre_save: Auto-set xp based on difficulty
    # - post_save: Update contest problem_count
    # - post_delete: Cleanup submissions
    
    indexes:
        Index(['is_active', 'difficulty'])
        Index(['slug'])
        Index(['category'])

class Function(models.Model):
    """Code template for each language"""
    
    problem          : ForeignKey → Problem
    language         : ForeignKey → Language
    function         : TextField              # Starter boilerplate
    owner            : ForeignKey → User
    
    unique_together: ['problem', 'language']
    
    # Example (Python):
    # def twoSum(nums: List[int], target: int) -> List[int]:
    #     pass

class TestCase(models.Model):
    """Hidden test cases for validation"""
    
    problem          : ForeignKey → Problem
    
    # Test Data
    input_txt        : TextField
    output_txt       : TextField
    explanation      : TextField (nullable)
    
    # Visibility
    is_sample        : Boolean (default=False)  # Show in problem statement?
    order            : PositiveInteger
    owner            : ForeignKey → User
    
    indexes:
        Index(['problem', 'order'])
        Index(['is_sample'])

class ExecutionTestCase(models.Model):
    """Code wrapper for Piston execution"""
    
    problem          : ForeignKey → Problem
    language         : ForeignKey → Language
    
    top_code         : TextField (nullable)    # Imports, setup
    bottom_code      : TextField              # Driver, test harness
    owner            : ForeignKey → User
    
    unique_together: ['problem', 'language']
    
    # Usage:
    # full_code = top_code + user_code + bottom_code
    # Send to Piston API

class Hint(models.Model):
    problem          : ForeignKey → Problem
    text             : MDTextField
    owner            : ForeignKey → User

class Challenge(models.Model):
    """Follow-up problem constraints"""
    problem          : ForeignKey → Problem
    text             : MDTextField
    owner            : ForeignKey → User

class Like(models.Model):
    """Problem ratings by users"""
    
    problem          : ForeignKey → Problem
    user             : ForeignKey → BaseUser
    like_or_dislike  : Boolean (default=True)  # True=like, False=dislike
    
    unique_together: ['problem', 'user']
    
    # Signals:
    # - post_save: Update problem.likes_count / dislikes_count
    # - post_delete: Decrement counts
```

### Code Submission & Execution

```python
# submissions/models.py

class Submission(models.Model):
    """User code submission with execution results"""
    
    class VerdictChoices(models.TextChoices):
        ACCEPTED = "AC", "Accepted"
        WRONG_ANSWER = "WA", "Wrong Answer"
        RUNTIME_ERROR = "RE", "Runtime Error"
        TIME_LIMIT_EXCEEDED = "TLE", "Time Limit Exceeded"
        MEMORY_LIMIT_EXCEEDED = "MLE", "Memory Limit Exceeded"
        COMPILE_ERROR = "CE", "Compile Error"
    
    # Relations
    user             : ForeignKey → BaseUser
    problem          : ForeignKey → Problem
    language         : ForeignKey → Language
    
    # Code
    code             : TextField
    
    # Execution Results
    status           : Boolean (True=AC, False=WA/RE/TLE/MLE/CE)
    verdict          : Choice (one of VerdictChoices)
    
    # Performance Metrics
    passed_test_count : PositiveInteger
    total_test_count : PositiveInteger
    execution_time   : PositiveInteger (nullable, milliseconds)
    execution_memory : PositiveInteger (nullable, KB)
    
    # Detailed Results
    test_results     : JSONField
    # Format: [
    #   {
    #     'idx': 1,
    #     'ok': true,
    #     'stdout': '...',
    #     'stderr': null,
    #     'runtime': 45,
    #     'memory': 32
    #   },
    #   ...
    # ]
    
    # Timestamps
    submitted_at     : DateTime (auto_now_add, db_index)
    
    # Signals:
    # - post_save: Award XP if status=True (first AC only)
    # - post_save: Update problem submission count
    # - post_save: Update leaderboard ranking
    
    indexes:
        Index(['user', 'problem'])
        Index(['problem', 'status'])
        Index(['-submitted_at'])
        
    ordering: ['-submitted_at']
```

### Quiz/Test System

```python
# quizs/models.py

class Test(models.Model):
    """Test/Quiz collection"""
    
    title            : CharField[255]
    slug             : SlugField (unique)
    description      : MDTextField (nullable)
    
    # Timing
    duration_minutes : PositiveInteger (default=60)
    start_time       : DateTime
    end_time         : DateTime
    
    # Questions
    question_count   : PositiveInteger (auto-updated)
    random_questions_count : PositiveInteger  # 0=all, else random N
    
    # Grading
    min_pass_percentage : PositiveInteger (0-100, default=60)
    max_attempts     : PositiveInteger (0=unlimited)
    penalty_coefficient : Float (0.0-1.0, default=0.33)
    
    # Access Control
    access_code      : CharField[50] (nullable, for private tests)
    is_active        : Boolean (db_index)
    
    # Pricing
    price            : DecimalField
    discount_price   : DecimalField (nullable)
    
    # Media
    intro_video      : ForeignKey → Video (nullable)
    
    # Gamification
    max_lifelines    : PositiveInteger (default=3)
    
    # Metadata
    modul            : ForeignKey → Modul (nullable)
    owner            : ForeignKey → User
    created_at       : DateTime (auto_now_add)
    updated_at       : DateTime (auto_now)
    
    @property
    is_available     : is_active AND now between start_time-end_time
    
    @property
    total_possible_xp : sum of all questions' xp
    
    # Signals:
    # - pre_save: Validate start_time < end_time
    # - post_save: Update enrollment counts
    
    indexes:
        Index(['slug'])
        Index(['modul'])

class Question(models.Model):
    """Quiz question (polymorphic: lesson-bound OR test-bound)"""
    
    class Difficulty(models.TextChoices):
        EASY = "easy", "Oson"
        MEDIUM = "medium", "O'rtacha"
        HARD = "hard", "Qiyin"
    
    # Can belong to EITHER lesson OR test (not both)
    lesson           : ForeignKey → Lesson (nullable)
    test             : ForeignKey → Test (nullable)
    
    # Content
    text             : MDTextField              # Markdown
    difficulty       : Choice (auto-set xp)
    xp               : PositiveInteger (5-20)
    order            : PositiveInteger (db_index)
    
    # Media
    explanation_video : ForeignKey → Video (nullable)
    
    # Metadata
    owner            : ForeignKey → User
    created_at       : DateTime (auto_now_add)
    updated_at       : DateTime (auto_now)
    
    # Signals:
    # - pre_save: Auto-set xp from difficulty
    # - post_save: Increment Test.question_count
    # - post_delete: Decrement Test.question_count
    # - post_save: Send to Lesson.total_tasks_count
    
    constraints:
        CheckConstraint: Q(lesson__isnull=False, test__isnull=True)
                      OR Q(lesson__isnull=True, test__isnull=False)

class Choice(models.Model):
    """Answer option for question"""
    
    question         : ForeignKey → Question
    text             : MDTextField              # Option text
    is_correct       : Boolean (db_index)
    explanation      : MDTextField (nullable)   # Why correct/wrong?
    order            : PositiveInteger
    
    owner            : ForeignKey → User
    created_at       : DateTime (auto_now_add)
    
    # Validation:
    # - Only ONE correct choice per question

class TestSession(models.Model):
    """Quiz attempt by user"""
    
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        EXPIRED = "expired"
    
    id               : UUID (primary_key)
    
    user             : ForeignKey → BaseUser
    test             : ForeignKey → Test
    
    status           : Choice (db_index)
    
    # Results
    score            : Float (S = Sum(C*P) - Sum(W*P*K))
    correct_count    : PositiveInteger
    wrong_count      : PositiveInteger
    unanswered_count : PositiveInteger
    
    total_xp_earned  : PositiveInteger (db_index, only if previous_best < current)
    
    # Gamification
    lifelines_used   : PositiveInteger
    
    # Timestamps
    started_at       : DateTime (auto_now_add)
    completed_at     : DateTime (nullable)
    
    # Signals:
    # - post_save (status=COMPLETED): Award XP only if > previous_best
    # - post_save: Update UserStats.xp + level
    # - post_save: Update LessonStatus if lesson-bound
    
    indexes:
        Index(['user', 'test', 'status'])
        Index(['status', '-started_at'])

class UserResponse(models.Model):
    """Individual answer by user to question"""
    
    session          : ForeignKey → TestSession
    user             : ForeignKey → BaseUser
    question         : ForeignKey → Question
    
    choice           : ForeignKey → Choice (nullable)  # If no choice = unanswered
    created_at       : DateTime (auto_now_add)
    
    # Signals:
    # - post_save: Track response for real-time grading
    # - post_save (lesson-question): Award micro-XP if correct

class TestEnrollment(models.Model):
    """Purchase history for paid tests"""
    
    id               : UUID
    user             : ForeignKey → BaseUser
    test             : ForeignKey → Test
    
    amount           : DecimalField
    transaction_id   : CharField (unique)
    created_at       : DateTime (auto_now_add)
    
    unique_together: ['user', 'test']
```

### Contest System

```python
# contests/models.py

class Contest(models.Model):
    """Coding competition"""
    
    class ContestTypes(models.TextChoices):
        OPEN = 'open'
        PRIVATE = 'private'
    
    class Status(models.TextChoices):
        UPCOMING = 'upcoming'
        ONGOING = 'ongoing'
        ENDED = 'ended'
    
    # Identity
    title            : CharField[200]
    slug             : SlugField (unique, auto-generated)
    description      : MDTextField (nullable)
    cover_image      : ImageField (nullable)
    
    # Type & Status
    type             : Choice (auto-set from access_key)
    status           : Choice (auto-set from timestamps)
    
    # Timing
    start_time       : DateTime
    end_time         : DateTime
    registration_deadline : DateTime (nullable)
    
    # Participation
    max_participants : PositiveInteger (0=unlimited)
    questions_count  : PositiveInteger
    pass_score_percent : PositiveInteger (0-100)
    
    # Access Control
    access_key       : CharField (nullable)  # If set → private
    is_active        : Boolean
    
    # Media
    intro_video      : ForeignKey → Video (nullable)
    
    # Metadata
    owner            : ForeignKey → User
    created_at       : DateTime (auto_now_add)
    updated_at       : DateTime (auto_now)
    
    @property
    duration_minutes : (end_time - start_time).total_seconds() / 60
    
    @property
    participants_count : Count of ContestRegistration
    
    @property
    is_registration_open : status=='upcoming' AND now <= registration_deadline
    
    @property
    can_join : is_active AND status=='ongoing'
    
    # Signals:
    # - pre_save: Generate slug
    # - pre_save: Auto-set type based on access_key
    # - pre_save: Auto-set status based on timestamps
    
    indexes:
        Index(['status', 'start_time'])
        Index(['type'])
        Index(['slug'])

class ContestPrize(models.Model):
    contest          : ForeignKey → Contest
    title            : CharField[200]
    rank_target      : PositiveInteger        # 1st, 2nd, 3rd
    monetary_value   : DecimalField (nullable)
    image            : ImageField (nullable)
    owner            : ForeignKey → User
    
    unique_together: ['contest', 'rank_target']

class ContestRegistration(models.Model):
    """Participation record + leaderboard entry"""
    
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        EXPIRED = "expired"
        DISQUALIFIED = "disqualified"
    
    id               : UUID (primary_key)
    
    user             : ForeignKey → BaseUser
    contest          : ForeignKey → Contest
    
    status           : Choice (db_index)
    
    # Statistics
    correct_count    : PositiveInteger
    wrong_count      : PositiveInteger
    unanswered_count : PositiveInteger
    
    time_spent_seconds : PositiveInteger
    total_xp_earned  : PositiveInteger (db_index, main ranking)
    
    # Ranking
    rank             : PositiveInteger (nullable, db_index)
    
    # Fraud Detection
    ip_address       : GenericIPAddressField (nullable)
    
    # Timestamps
    started_at       : DateTime (auto_now_add)
    completed_at     : DateTime (nullable, db_index)
    
    @property
    accuracy_percent : (correct_count / (correct_count + wrong_count)) * 100
    
    @property
    medal : 🥇 if rank==1 else (🥈 if rank==2 else (🥉 if rank==3 else ""))
    
    unique_together: ['user', 'contest']
    
    # Signals:
    # - post_save: Update leaderboard rankings
    # - post_save (completed): Award XP to UserStats
    
    indexes:
        Index(['contest', 'rank'])
        Index(['contest', '-total_xp_earned'])
```

### Course & Learning Path

```python
# courses/models.py

class Course(TimeStampedModel):
    title            : CharField[200]
    slug             : SlugField (unique)
    description      : MDTextField
    
    # Pricing
    price            : DecimalField (default=0)
    discount_price   : DecimalField (nullable)
    
    @property
    current_price    : discount_price if valid else price
    
    is_active        : Boolean (default=False)
    
    owner            : ForeignKey → User
    total_lessons_count : PositiveSmallInteger (auto-updated)
    total_test_count : PositiveSmallInteger (auto-updated)
    
    intro_video      : ForeignKey → Video (nullable)

class Modul(TimeStampedModel):
    """Chapter/Section of course"""
    course           : ForeignKey → Course
    title            : CharField[200]
    slug             : SlugField
    owner            : ForeignKey → User
    
    # Signals:
    # - post_save: Update course module count

class Lesson(TimeStampedModel):
    """Lesson within module"""
    modul            : ForeignKey → Modul
    
    title            : CharField[100]
    slug             : SlugField
    order            : PositiveInteger
    
    total_tasks_count : PositiveSmallInteger (auto-calc)
    
    owner            : ForeignKey → User
    
    # Signals:
    # - post_save: Recalculate from Lecture + Question (lesson-bound) + Problem (lesson-bound)

class Lecture(TimeStampedModel):
    """Video lesson + markdown notes"""
    lesson           : ForeignKey → Lesson
    
    title            : CharField[200]
    slug             : SlugField
    
    body             : MDTextField (nullable)  # Lecture notes
    video           : ForeignKey → Video (nullable)
    
    xp               : PositiveInteger (5-20)
    order            : PositiveInteger
    
    owner            : ForeignKey → User
    
    # Validation: Must have video OR body (not empty)
    
    # Signals:
    # - post_save: Increment lesson.total_tasks_count
    
    indexes:
        Index(['lesson', 'order'])

class Enrollment(TimeStampedModel):
    """Student enrollment in course"""
    user             : ForeignKey → BaseUser
    course           : ForeignKey → Course
    
    is_paid          : Boolean
    is_completed     : Boolean (db_index)
    
    finished_darslar_soni : PositiveSmallInteger
    finished_test_soni : PositiveSmallInteger
    
    completed_at     : DateTime (nullable)
    
    unique_together: ['user', 'course']
    
    # Signals:
    # - post_save (is_completed=True): Award course XP
```

### Gamification & Statistics

```python
# status/models.py

class UserStats(models.Model):
    """Global user statistics"""
    
    user             : OneToOneField → BaseUser
    
    xp               : PositiveInteger (default=0)
    level            : PositiveInteger (computed: xp / 100)
    
    total_problems_solved : PositiveInteger
    easy_solved      : PositiveInteger
    medium_solved    : PositiveInteger
    hard_solved      : PositiveInteger
    
    total_quizzes_passed : PositiveInteger
    
    current_streak   : PositiveInteger (days)
    longest_streak   : PositiveInteger (days)
    
    updated_at       : DateTime (auto_now)
    
    @property
    level            : compute from xp
    
    # Signals:
    # - post_save: Update badges if thresholds met

class LessonStatus(models.Model):
    """Student progress in lesson"""
    user             : ForeignKey → BaseUser
    lesson           : ForeignKey → Lesson
    
    is_completed     : Boolean
    completed_at     : DateTime (nullable)
    
    unique_together: ['user', 'lesson']
```

---

## 🔌 Django Signals — Automatic Data Synchronization

### Problem Creation/Update

```python
# problems/signals.py

@receiver(pre_save, sender=Problem)
def auto_generate_slug(sender, instance, **kwargs):
    """Auto-generate slug from title"""
    if not instance.slug:
        instance.slug = slugify(instance.title)

@receiver(pre_save, sender=Problem)
def auto_set_xp(sender, instance, **kwargs):
    """Auto-set XP based on difficulty"""
    if not instance.xp or instance.xp == 0:
        defaults = {'easy': 10, 'medium': 25, 'hard': 50}
        instance.xp = defaults.get(instance.difficulty, 10)

@receiver(post_save, sender=Problem)
def update_problem_counts(sender, instance, created, **kwargs):
    """Update contest problem count"""
    if instance.contest:
        instance.contest.questions_count = Problem.objects.filter(
            contest=instance.contest
        ).count()
        instance.contest.save(update_fields=['questions_count'])

@receiver(post_delete, sender=Problem)
def cleanup_problem_submissions(sender, instance, **kwargs):
    """Archive submissions before deleting problem"""
    Submission.objects.filter(problem=instance).update(problem=None)
```

### Question Counter

```python
# quizs/signals.py

@receiver(pre_save, sender=Question, dispatch_uid="capture_old_test_id")
def capture_old_test_id(sender, instance, **kwargs):
    """Cache old test_id before save"""
    if instance.id:
        try:
            instance._old_test_id = Question.objects.only("test_id").get(
                id=instance.id
            ).test_id
        except Question.DoesNotExist:
            instance._old_test_id = None
    else:
        instance._old_test_id = None

@receiver(post_save, sender=Question, dispatch_uid="increment_question_count")
def increment_question_count(sender, instance, created, **kwargs):
    """Update Test.question_count when question added/moved"""
    if created and instance.test_id:
        with transaction.atomic():
            test = Test.objects.select_for_update().filter(
                id=instance.test_id
            ).first()
            if test:
                test.question_count = F("question_count") + 1
                test.save(update_fields=["question_count"])
    
    old_test_id = getattr(instance, "_old_test_id", None)
    if old_test_id != instance.test_id:
        with transaction.atomic():
            # Decrement old test
            if old_test_id:
                old_test = Test.objects.select_for_update().filter(
                    id=old_test_id
                ).first()
                if old_test and old_test.question_count > 0:
                    old_test.question_count = F("question_count") - 1
                    old_test.save(update_fields=["question_count"])
            
            # Increment new test
            if instance.test_id:
                new_test = Test.objects.select_for_update().filter(
                    id=instance.test_id
                ).first()
                if new_test:
                    new_test.question_count = F("question_count") + 1
                    new_test.save(update_fields=["question_count"])

@receiver(post_delete, sender=Question, dispatch_uid="decrement_question_count")
def decrement_question_count(sender, instance, **kwargs):
    """Decrement Test.question_count on question delete"""
    if instance.test_id:
        with transaction.atomic():
            test = Test.objects.select_for_update().filter(
                id=instance.test_id
            ).first()
            if test and test.question_count > 0:
                test.question_count = F("question_count") - 1
                test.save(update_fields=["question_count"])
```

### Submission & XP Award

```python
# submissions/signals.py

@receiver(post_save, sender=Submission)
def award_xp_for_accepted(sender, instance, created, **kwargs):
    """Award XP only on first Accepted (AC) submission"""
    if not created or instance.verdict != Submission.VerdictChoices.ACCEPTED:
        return
    
    # Check if user already solved this problem
    previous_ac = Submission.objects.filter(
        user=instance.user,
        problem=instance.problem,
        verdict=Submission.VerdictChoices.ACCEPTED,
    ).exclude(id=instance.id).exists()
    
    if previous_ac:
        return  # Already solved, no XP
    
    # Award XP to user stats
    with transaction.atomic():
        stats, created = UserStats.objects.select_for_update().get_or_create(
            user=instance.user
        )
        stats.xp += instance.problem.xp
        stats.total_problems_solved += 1
        
        # Update difficulty counter
        if instance.problem.difficulty == 'easy':
            stats.easy_solved += 1
        elif instance.problem.difficulty == 'medium':
            stats.medium_solved += 1
        elif instance.problem.difficulty == 'hard':
            stats.hard_solved += 1
        
        stats.level = stats.xp // 100
        stats.save()

@receiver(post_save, sender=Submission)
def update_contest_registration(sender, instance, created, **kwargs):
    """Update contest leaderboard if problem is in contest"""
    if not instance.problem.contest:
        return
    
    try:
        reg = ContestRegistration.objects.get(
            user=instance.user,
            contest=instance.problem.contest
        )
        # Recompute registration XP based on new submission
        # ... complex logic here
    except ContestRegistration.DoesNotExist:
        pass
```

### Quiz Completion & XP

```python
# quizs/signals.py

@receiver(post_save, sender=TestSession)
def award_quiz_xp(sender, instance, created, **kwargs):
    """Award XP when quiz completed with passing score"""
    if instance.status != TestSession.Status.COMPLETED:
        return
    
    if instance.total_xp_earned == 0:
        return
    
    # Get previous best score for this test
    previous_best = TestSession.objects.filter(
        user=instance.user,
        test=instance.test,
        status=TestSession.Status.COMPLETED
    ).exclude(id=instance.id).order_by('-total_xp_earned').first()
    
    xp_to_award = 0
    if previous_best:
        if instance.total_xp_earned > previous_best.total_xp_earned:
            xp_to_award = instance.total_xp_earned - previous_best.total_xp_earned
    else:
        xp_to_award = instance.total_xp_earned
    
    if xp_to_award > 0:
        with transaction.atomic():
            stats = UserStats.objects.select_for_update().get(user=instance.user)
            stats.xp += xp_to_award
            stats.total_quizzes_passed += 1
            stats.level = stats.xp // 100
            stats.save()

@receiver(post_save, sender=UserResponse)
def update_lesson_completion(sender, instance, created, **kwargs):
    """Award micro-XP if lesson question answered correctly"""
    if not instance.question.lesson or not instance.choice:
        return
    
    if not instance.choice.is_correct:
        return
    
    # Check if already awarded
    if UserResponse.objects.filter(
        user=instance.user,
        question=instance.question,
        choice__is_correct=True
    ).exclude(id=instance.id).exists():
        return
    
    # Award XP
    stats = UserStats.objects.get(user=instance.user)
    stats.xp += instance.question.xp
    stats.save(update_fields=['xp'])
```

### Like/Dislike Counter

```python
# problems/signals.py

@receiver(post_save, sender=Like)
def update_like_counts(sender, instance, created, **kwargs):
    """Update problem like/dislike counters"""
    if not created:
        return
    
    if instance.like_or_dislike:
        instance.problem.likes_count = F("likes_count") + 1
    else:
        instance.problem.dislikes_count = F("dislikes_count") + 1
    
    instance.problem.save()

@receiver(post_delete, sender=Like)
def decrement_like_counts(sender, instance, **kwargs):
    """Decrement like/dislike on deletion"""
    if instance.like_or_dislike:
        instance.problem.likes_count = F("likes_count") - 1
    else:
        instance.problem.dislikes_count = F("dislikes_count") - 1
    
    instance.problem.save()
```

---

## 🛠️ REST API Design (DRF Serializers & Views)

### Authentication Serializers

```python
# baseuser/serializers.py

class SendOTPSerializer(serializers.Serializer):
    """Send OTP to user phone"""
    phone = serializers.CharField(max_length=20)
    
    def validate_phone(self, value):
        if not BaseUser.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Foydalanuvchi topilmadi")
        return value

class VerifyOTPSerializer(serializers.Serializer):
    """Verify OTP and return tokens"""
    phone = serializers.CharField(max_length=20)
    otp = serializers.CharField(max_length=6)

class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()

class UserProfileSerializer(serializers.ModelSerializer):
    level = serializers.SerializerMethodField()
    
    class Meta:
        model = BaseUser
        fields = ['id', 'telegram_id', 'username', 'phone', 'full_name', 'level']
    
    def get_level(self, obj):
        stats = getattr(obj, 'stats', None)
        if stats:
            return stats.level
        return 1
```

### Problem Serializers

```python
# problems/serializers.py

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['id', 'name', 'version']

class FunctionSerializer(serializers.ModelSerializer):
    language_name = serializers.CharField(source='language.name', read_only=True)
    
    class Meta:
        model = Function
        fields = ['id', 'language', 'language_name', 'function']

class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ['id', 'input_txt', 'output_txt', 'explanation', 'is_sample', 'order']

class HintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hint
        fields = ['id', 'text']

class ProblemListSerializer(serializers.ModelSerializer):
    """Lightweight for list view"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display')
    
    class Meta:
        model = Problem
        fields = [
            'id', 'title', 'slug', 'difficulty', 'difficulty_display',
            'xp', 'category_name', 'likes_count', 'dislikes_count'
        ]

class ProblemDetailSerializer(serializers.ModelSerializer):
    """Full details for detail view"""
    functions = FunctionSerializer(many=True, read_only=True)
    test_cases_sample = serializers.SerializerMethodField()
    hints = HintSerializer(many=True, read_only=True)
    
    class Meta:
        model = Problem
        fields = [
            'id', 'title', 'slug', 'description', 'difficulty', 'xp',
            'time_limit', 'memory_limit', 'functions', 'test_cases_sample',
            'hints', 'likes_count', 'dislikes_count'
        ]
    
    def get_test_cases_sample(self, obj):
        samples = obj.test_cases.filter(is_sample=True).order_by('order')
        return TestCaseSerializer(samples, many=True).data
```

### Submission Serializers

```python
# submissions/serializers.py

class SubmitCodeSerializer(serializers.Serializer):
    """Input for code submission"""
    problem_id = serializers.IntegerField()
    code = serializers.CharField()
    language_id = serializers.IntegerField()

class SubmissionResultSerializer(serializers.ModelSerializer):
    language_name = serializers.CharField(source='language.name', read_only=True)
    verdict_display = serializers.CharField(source='get_verdict_display')
    
    class Meta:
        model = Submission
        fields = [
            'id', 'problem_id', 'code', 'language_name', 'status',
            'verdict', 'verdict_display', 'passed_test_count', 'total_test_count',
            'execution_time', 'execution_memory', 'test_results', 'submitted_at'
        ]

class SubmissionListSerializer(serializers.ModelSerializer):
    problem_title = serializers.CharField(source='problem.title', read_only=True)
    
    class Meta:
        model = Submission
        fields = [
            'id', 'problem_id', 'problem_title', 'language_id', 'status',
            'submitted_at'
        ]
```

### Quiz Serializers

```python
# quizs/serializers.py

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'order', 'explanation']

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'difficulty', 'xp', 'order', 'choices']

class TestListSerializer(serializers.ModelSerializer):
    @property
    def current_price(self, obj):
        if obj.discount_price and obj.discount_price < obj.price:
            return obj.discount_price
        return obj.price
    
    class Meta:
        model = Test
        fields = [
            'id', 'title', 'slug', 'duration_minutes', 'question_count',
            'min_pass_percentage', 'is_active', 'price', 'discount_price'
        ]

class TestDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Test
        fields = [
            'id', 'title', 'slug', 'description', 'duration_minutes',
            'question_count', 'random_questions_count', 'min_pass_percentage',
            'max_attempts', 'penalty_coefficient', 'questions'
        ]

class TestSessionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSession
        fields = [
            'id', 'score', 'correct_count', 'wrong_count', 'unanswered_count',
            'total_xp_earned', 'completed_at'
        ]

class SubmitAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    choice_id = serializers.IntegerField(required=False, allow_null=True)
```

### Contest Serializers

```python
# contests/serializers.py

class ContestListSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display')
    status_display = serializers.CharField(source='get_status_display')
    participants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Contest
        fields = [
            'id', 'title', 'slug', 'type', 'type_display', 'status',
            'status_display', 'start_time', 'end_time', 'participants_count',
            'max_participants'
        ]
    
    def get_participants_count(self, obj):
        return obj.registrations.count()

class ContestDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contest
        fields = [
            'id', 'title', 'slug', 'description', 'type', 'status',
            'start_time', 'end_time', 'max_participants', 'questions_count',
            'pass_score_percent'
        ]

class ContestLeaderboardSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.telegram_id', read_only=True)
    medal = serializers.SerializerMethodField()
    
    class Meta:
        model = ContestRegistration
        fields = [
            'rank', 'username', 'user_id', 'total_xp_earned', 'correct_count',
            'wrong_count', 'medal', 'time_spent_seconds'
        ]
    
    def get_medal(self, obj):
        return obj.medal
```

---

## 📡 REST API Endpoints with Pagination & Filtering

### Authentication Endpoints

```
POST /api/v1/auth/send-otp/
  Request:  { "phone": "+998901234567" }
  Response: 200 { "message": "OTP sent", "expires_in": 120 }
            404 { "error": "User not found" }

POST /api/v1/auth/verify-otp/
  Request:  { "phone": "+998...", "otp": "123456" }
  Response: 200 { 
              "access": "eyJhb...",
              "refresh": "eyJhb...",
              "user": { "id": 1, "username": "user", "level": 5 }
            }
            400 { "error": "Invalid OTP" }

POST /api/v1/auth/refresh/
  Request:  { "refresh": "eyJhb..." }
  Response: 200 { "access": "eyJhb..." }

GET /api/v1/auth/profile/
  Headers: Authorization: Bearer {access_token}
  Response: 200 { "id": 1, "username": "user", "xp": 4750, "level": 12 }
```

### Problems Endpoints

```
GET /api/v1/problems/
  Query: ?difficulty=easy&category=arrays&page=1&limit=20
  Response: 200 {
    "count": 1000,
    "next": "...?page=2",
    "previous": null,
    "results": [
      {
        "id": 1,
        "title": "Two Sum",
        "slug": "two-sum",
        "difficulty": "easy",
        "xp": 10,
        "likes_count": 150
      },
      ...
    ]
  }

GET /api/v1/problems/{id}/
  Response: 200 {
    "id": 1,
    "title": "Two Sum",
    "description": "## Problem...",
    "functions": [
      {
        "id": 1,
        "language": "python",
        "function": "def twoSum(...)"
      },
      ...
    ],
    "test_cases_sample": [
      {
        "id": 1,
        "input_txt": "[2,7,11,15]\n9",
        "output_txt": "[0,1]",
        "explanation": "nums[0] + nums[1] = ..."
      }
    ],
    "hints": [
      { "id": 1, "text": "Use a hash map..." }
    ]
  }

POST /api/v1/problems/{id}/like/
  Request:  { "like": true }  # true = like, false = dislike
  Response: 200 { "message": "Liked" }

POST /api/v1/problems/{id}/submissions/
  Request:  {
    "code": "def twoSum(nums, target):\n    pass",
    "language_id": 1
  }
  Response: 202 {
    "id": 123,
    "status": "queued",
    "job_id": "abc123"
  }

GET /api/v1/problems/{id}/submissions/
  Query: ?status=AC&page=1&limit=10
  Response: 200 {
    "results": [
      {
        "id": 123,
        "language": "python",
        "status": true,
        "submitted_at": "2026-05-11T10:23:00Z"
      }
    ]
  }

GET /api/v1/problems/{id}/leaderboard/
  Query: ?limit=10
  Response: 200 {
    "results": [
      {
        "rank": 1,
        "user": "sardor",
        "total_xp": 100,
        "submitted_at": "..."
      }
    ]
  }
```

### Submissions Endpoints

```
POST /api/v1/submissions/
  Request: {
    "problem_id": 1,
    "code": "...",
    "language_id": 1
  }
  Response: 202 {
    "id": 123,
    "status": "queued",
    "message": "Submission queued for execution"
  }

GET /api/v1/submissions/{id}/
  Response: 200 {
    "id": 123,
    "verdict": "AC",
    "passed_test_count": 5,
    "total_test_count": 5,
    "execution_time": 45,
    "test_results": [
      { "idx": 1, "ok": true, "stdout": "..." },
      ...
    ]
  }

WS ws://localhost:8000/api/v1/ws/submissions/{id}/
  Message Types:
    { "type": "queued", "data": { "position": 3 } }
    { "type": "running", "data": { "test_id": 1 } }
    { "type": "test_result", "data": { "idx": 1, "ok": true, ... } }
    { "type": "done", "data": { "passed": 5, "xp_earned": 10 } }
    { "type": "compile_error", "data": { "message": "..." } }
```

### Quizzes Endpoints

```
GET /api/v1/quizzes/
  Query: ?modul_id=1&page=1&limit=20
  Response: 200 { "results": [...] }

GET /api/v1/quizzes/{id}/
  Response: 200 {
    "id": 1,
    "title": "Hash Map Basics",
    "description": "...",
    "duration_minutes": 60,
    "question_count": 10,
    "min_pass_percentage": 60,
    "questions": [
      {
        "id": 1,
        "text": "What is...",
        "choices": [
          { "id": 1, "text": "Option A", "order": 1 },
          ...
        ]
      }
    ]
  }

POST /api/v1/quizzes/{id}/start/
  Request: {}
  Response: 201 {
    "session_id": "uuid-abc-123",
    "time_left_seconds": 3600,
    "questions": [...]
  }

POST /api/v1/quizzes/{id}/answer/
  Request: {
    "session_id": "uuid-abc-123",
    "question_id": 1,
    "choice_id": 2
  }
  Response: 200 { "message": "Answer saved" }

POST /api/v1/quizzes/{id}/submit/
  Request: { "session_id": "uuid-abc-123" }
  Response: 200 {
    "score": 85.5,
    "correct": 6,
    "wrong": 2,
    "unanswered": 2,
    "passed": true,
    "xp_earned": 50,
    "results": [
      { "question_id": 1, "correct": true },
      ...
    ]
  }

GET /api/v1/quizzes/{id}/result/{session_id}/
  Response: 200 {
    "score": 85.5,
    "passed": true,
    "results": [...]
  }

WS ws://localhost:8000/api/v1/ws/test-session/{session_id}/
  Message Types:
    { "type": "time_update", "data": { "seconds_left": 1234 } }
    { "type": "auto_submit", "data": { "reason": "time_up" } }
```

### Contests Endpoints

```
GET /api/v1/contests/
  Query: ?status=ongoing&difficulty=medium&page=1&limit=10
  Response: 200 { "results": [...] }

GET /api/v1/contests/{id}/
  Response: 200 { ... }

POST /api/v1/contests/{id}/join/
  Request: { "access_key": "..." }  # if private
  Response: 201 {
    "message": "Joined",
    "registration_id": "uuid",
    "start_time": "..."
  }

GET /api/v1/contests/{id}/leaderboard/
  Query: ?page=1&limit=50
  Response: 200 {
    "results": [
      {
        "rank": 1,
        "username": "sardor",
        "total_xp_earned": 1400,
        "correct": 4,
        "medal": "🥇"
      },
      ...
    ]
  }

WS ws://localhost:8000/api/v1/ws/contests/{id}/
  Message Types:
    { "type": "time_update", "data": { "seconds_left": 1234 } }
    { "type": "leaderboard_update", "data": { ... } }
    { "type": "participant_join", "data": { "count": 50 } }
```

### Courses Endpoints

```
GET /api/v1/courses/
  Query: ?page=1&limit=20
  Response: 200 { "results": [...] }

GET /api/v1/courses/{slug}/
  Response: 200 { ... }

POST /api/v1/courses/{slug}/enroll/
  Request: {}
  Response: 201 { "message": "Enrolled" }

GET /api/v1/courses/{slug}/lessons/
  Response: 200 {
    "results": [
      {
        "id": 1,
        "title": "Module 1",
        "lessons": [
          { "id": 1, "title": "Lesson 1", "completed": false },
          ...
        ]
      }
    ]
  }

GET /api/v1/courses/{slug}/lessons/{lesson_id}/
  Response: 200 {
    "id": 1,
    "title": "Lesson Title",
    "lectures": [...],
    "problems": [...],
    "quiz": {...},
    "is_completed": false
  }

GET /api/v1/courses/{slug}/progress/
  Response: 200 {
    "completed_lessons": 5,
    "total_lessons": 10,
    "completed_tests": 2,
    "total_tests": 3,
    "percentage": 50
  }
```

---

## 🔒 Authentication & Authorization

### JWT Token Structure

```
Access Token:  15 minutes
Refresh Token: 7 days

Header:
{
  "alg": "HS256",
  "typ": "JWT"
}

Payload (Access):
{
  "sub": "user_id",
  "user_id": 1,
  "telegram_id": 123456789,
  "username": "sardor_dev",
  "level": 12,
  "exp": 1620000000,
  "iat": 1619999100
}
```

### Permission Classes

```python
# permissions.py

class IsAuthenticated(permissions.BasePermission):
    """User must be logged in"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

class IsOwnerOrReadOnly(permissions.BasePermission):
    """Only owner can edit"""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user
```

---

## 📊 Performance Optimizations

### Database Indexes (Reviewed)
```
problems.test_cases: Index(['problem', 'order']) → fast test iteration
submissions: Index(['user', 'problem']) → user's submissions
submissions: Index(['problem', 'status']) → filter by result
contests.registrations: Index(['contest', '-total_xp_earned']) → leaderboard
quizs.questions: Index(['test', 'order']) → test rendering
```

### Query Optimization
```python
# Use select_related for ForeignKey
problems = Problem.objects.select_related('category', 'owner')

# Use prefetch_related for ManyToMany
problems = Problem.objects.prefetch_related('tags', 'language')

# Use only() for large tables
problems = Problem.objects.only('id', 'title', 'slug')

# Atomic transactions for consistency
with transaction.atomic():
    stats = UserStats.objects.select_for_update().get(user=user)
    stats.xp += points
    stats.save()
```

### Caching Strategy
```python
# Redis cache for frequently accessed data
cache.set(f"problem:{problem_id}:detail", serialized_data, timeout=3600)
cache.get(f"problem:{problem_id}:detail")

# Cache user stats
cache.set(f"user_stats:{user_id}", stats_dict, timeout=300)
```

---

## 🚀 Deployment Checklist

- [ ] Environment variables (.env) configured
- [ ] Database migrations applied (`python manage.py migrate`)
- [ ] Static files collected
- [ ] Redis cache running
- [ ] PostgreSQL database initialized
- [ ] MinIO S3 bucket created
- [ ] Piston API running
- [ ] Celery worker started (`celery -A app worker`)
- [ ] Django Bolt server running (`python manage.py runbolt`)
- [ ] SSL certificates configured (production)
- [ ] CORS whitelist updated (production)
- [ ] Admin user created (`createsuperuser`)

---

**Last Updated:** July 12, 2026
**Version:** v1.0.0
**Status:** Production Ready
