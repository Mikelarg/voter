from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from rest_framework.authtoken.models import Token


class Poll(models.Model):
    """
    Опрос
    """
    title = models.CharField(max_length=200, verbose_name="Title")
    description = models.TextField(verbose_name="Description", blank=True, null=True)
    start_date = models.DateTimeField(verbose_name='Start Date')
    end_date = models.DateTimeField(verbose_name='End Date')

    def user_participated(self, user):
        """
        Участвовал ли юзер уже в опросе
        """
        return Vote.objects.filter(question__poll=self, user=user).count() > 0

    def can_vote(self):
        """
        Проверяет истекло время голосования или нет
        """
        return self.start_date < timezone.now() < self.end_date

    @staticmethod
    def active():
        """
        Активные опросы
        """
        return Poll.objects.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now())

    def __str__(self):
        return "{0} - {1}".format(self.pk, self.title)


class Question(models.Model):
    """
    Вопрос в опросе
    """
    ANSWER_WITH_TEXT = "ANSWER_WITH_TEXT"
    ANSWER_SINGLE_CHOICE = "ANSWER_SINGLE_CHOICE"
    ANSWER_MULTIPLE_CHOICES = "ANSWER_MULTIPLE_CHOICE"

    poll = models.ForeignKey(to=Poll, on_delete=models.CASCADE)
    question_text = models.CharField(max_length=200)
    question_type = models.CharField(max_length=50, choices=(
        (ANSWER_WITH_TEXT, "Answer with text"),
        (ANSWER_SINGLE_CHOICE, "Single choice answer"),
        (ANSWER_MULTIPLE_CHOICES, "Multiple choices answer"),
    ))

    def __str__(self):
        return "{0} - {1}".format(self.pk, self.question_text)


class Choice(models.Model):
    """
    Вариант ответа в вопросе
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=200)

    def __str__(self):
        return "{0} - {1}".format(self.pk, self.choice_text)


class Vote(models.Model):
    """
    Голос в опросе
    """
    choices = models.ManyToManyField(Choice, blank=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    answer = models.TextField(blank=True, null=True)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Создаем токен при создании пользователя
    """
    if created:
        Token.objects.create(user=instance)
