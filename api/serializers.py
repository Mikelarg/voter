from django.db import transaction
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from polls.models import Poll, Question, Choice, Vote


class ChoiceSerializer(serializers.ModelSerializer):
    """
    Сериализатор варианта выбора
    """
    class Meta:
        model = Choice
        fields = ['id', 'question', 'choice_text']


class ChoiceInQuestionSerializer(serializers.ModelSerializer):
    """
    Сериализатор создания / обновления из сериализатора вопроса
    """
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Choice
        fields = ['id', 'choice_text']


class QuestionSerializer(serializers.ModelSerializer):
    """
    Сериализатор вопроса
    """
    choices = ChoiceInQuestionSerializer(many=True, source='choice_set', required=False)

    def create(self, validated_data):
        """
        Создание вопроса и также вместе с ним вариантов ответа на него
        """
        choices_data = validated_data.pop('choice_set', [])
        question = Question.objects.create(**validated_data)
        for choice_data in choices_data:
            choice_data.pop('id', None)
            Choice.objects.create(question=question, **choice_data)
        return question

    def update(self, instance, validated_data):
        """
        Обновление вопроса и вариантов ответов на него
        """
        instance.poll = validated_data.get('poll', instance.poll)
        instance.question_text = validated_data.get('question_text', instance.question_text)
        instance.question_type = validated_data.get('question_type', instance.question_type)
        instance.save()

        choices_data = validated_data.pop('choice_set', [])
        for choice_data in choices_data:
            if 'id' in choice_data and 'choice_text' in choice_data:
                Choice.objects.filter(
                    id=choice_data['id'], question=instance
                ).update(choice_text=choice_data['choice_text'])
        return instance

    class Meta:
        model = Question
        fields = ['id', 'poll', 'question_text', 'question_type', 'choices']


class PollSerializer(serializers.ModelSerializer):
    """
    Сериализатор опроса
    """
    questions = QuestionSerializer(many=True, source="question_set", read_only=True)

    def __init__(self, *args, **kwargs):
        """
        Если опрос уже создан, то мы делаем дату старта read-only
        """
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.fields.get('start_date').read_only = True

    def validate(self, attrs):
        """
        Проверяем что дата окончания опроса не раньше даты его старта
        """
        start_date = attrs.get('start_date', None) or self.instance.start_date
        if start_date > attrs['end_date']:
            raise ValidationError({"end_date": "End date must be after start date!"})
        return attrs

    class Meta:
        model = Poll
        fields = ['id', 'title', 'description', 'start_date', 'end_date', 'questions']


class VoteCreateSerializer(serializers.Serializer):
    """
    Сериализатор для создание голоса в вопросе
    """
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    choices = serializers.PrimaryKeyRelatedField(many=True, queryset=Choice.objects.all(), required=False,
                                                 allow_empty=True)
    answer = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

    def validate(self, attrs):
        """
        Делаем общие проверки на правильность голоса
        """
        question = attrs['question']
        choices = attrs.get('choices', [])
        answer = attrs.get('answer', "")
        if question.question_type == Question.ANSWER_WITH_TEXT:
            if choices or not answer:
                raise ValidationError("Question need text answer!")
        else:
            if question.choice_set.count() > 0 and not choices:
                raise ValidationError("Please, choose something!")
            if question.question_type == Question.ANSWER_SINGLE_CHOICE and len(choices) > 1:
                raise ValidationError({"choices": "Only one choice!"})
            for choice in choices:
                if choice.question != question:
                    raise ValidationError({"choices": "Choice not in question!"})
        return attrs


class FillPollSerializer(serializers.Serializer):
    """
    Создаем ответ на опрос
    """
    poll = serializers.PrimaryKeyRelatedField(queryset=Poll.objects.all())
    votes = VoteCreateSerializer(many=True)

    def update(self, instance, validated_data):
        pass

    def validate(self, attrs):
        """
        Делаем общие проверки на возможность участие в опросе и в правильности переданных данных
        """
        user = self.context['request'].user
        poll = attrs['poll']
        if not user.is_anonymous and poll.user_participated(user):
            raise ValidationError("User already participated in this poll!")
        if not poll.can_vote():
            raise ValidationError(
                "Poll time is ended or not started {0} - {1}".format(poll.start_date, poll.end_date)
            )

        # Полученные из JSON id вопросов
        question_ids = list(map(lambda vote: vote['question'].id, attrs['votes']))
        # Фильтруем id вопросов в опроснике. Если вопрос не был в опросе его не будет в результате
        filtered_question_count = poll.question_set.filter(id__in=question_ids).count()
        # Оригинальное количество вопросов в опросе
        question_count = poll.question_set.count()
        # Если количество отфильтрованных вопросов не совпадает с количество получаемых вопросов, то пришли ответы
        # на вопросы с другого опроса
        if filtered_question_count != len(question_ids):
            raise ValidationError("Probably some questions not in poll")
        if filtered_question_count != question_count:
            raise ValidationError("Please answer all questions!")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        for vote_data in validated_data['votes']:
            question = vote_data['question']
            vote = Vote(answer=vote_data.get('answer', None))
            vote.user = user if not user.is_anonymous else None
            vote.question = question
            vote.save()
            if question.question_type != Question.ANSWER_WITH_TEXT:
                vote.choices.add(*vote_data.get('choices', []))
        return validated_data['poll']


class VoteSerializer(serializers.ModelSerializer):
    """
    Сериализатор голоса пользователя
    """
    class Meta:
        model = Vote
        fields = ['id', 'answer', 'choices']


class VotedQuestionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения вопроса на который ответил пользователь
    """
    choices = ChoiceInQuestionSerializer(many=True, source='choice_set')
    voted = serializers.SerializerMethodField('get_vote')

    def get_vote(self, instance):
        """
        Получаем голос в вопросе от пользователя
        """
        qs = Vote.objects.filter(user_id=self.context['user_id'], question=instance)
        serializer = VoteSerializer(instance=qs, many=True)
        return serializer.data

    class Meta:
        model = Question
        fields = ['id', 'poll', 'question_text', 'question_type', 'choices', 'voted']


class VotedPollSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения опроса в котором участвовал пользователь
    """
    questions = VotedQuestionSerializer(many=True, source="question_set")

    class Meta:
        model = Poll
        fields = ['id', 'title', 'description', 'start_date', 'end_date', 'questions']
