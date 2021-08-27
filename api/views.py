from django.contrib.auth.models import User
from django.http import Http404
from rest_framework import viewsets, permissions, generics, mixins, status
from rest_framework.response import Response

from api.serializers import PollSerializer, QuestionSerializer, ChoiceSerializer, FillPollSerializer, \
    VotedPollSerializer
from polls.models import Poll, Question, Choice


class CreateRetrieveUpdateDestroyViewSet(mixins.CreateModelMixin,
                                         mixins.RetrieveModelMixin,
                                         mixins.UpdateModelMixin,
                                         mixins.DestroyModelMixin,
                                         viewsets.GenericViewSet):
    pass


class PollViewSet(viewsets.ModelViewSet):
    """
    CRUD для опросов
    """
    queryset = Poll.objects.all()
    permission_classes = [permissions.IsAdminUser]
    serializer_class = PollSerializer


class QuestionViewSet(CreateRetrieveUpdateDestroyViewSet):
    """
    CRUD для вопросов в опросах
    """
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAdminUser]


class ChoiceViewSet(CreateRetrieveUpdateDestroyViewSet):
    """
    CRUD для ответов на вопросы
    """
    queryset = Choice.objects.all()
    serializer_class = ChoiceSerializer
    permission_classes = [permissions.IsAdminUser]


class ActivePollsView(generics.ListAPIView):
    """
    Список активных опросов
    """
    serializer_class = PollSerializer

    def get_queryset(self):
        return Poll.active()


class VoteView(generics.CreateAPIView):
    """
    Вьюха для голосования в опросе
    """
    serializer_class = FillPollSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({'success': True}, status=status.HTTP_201_CREATED)


class VotedView(generics.ListAPIView):
    """
    Получение опросов пройденных пользователем
    """
    serializer_class = VotedPollSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user_id'] = self.kwargs['user']
        if not User.objects.filter(pk=context['user_id']).exists():
            raise Http404()
        return context

    def get_queryset(self):
        return Poll.objects.filter(question__vote__user_id=self.kwargs['user']).distinct()
