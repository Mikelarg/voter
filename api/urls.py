from django.urls import path, include
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from api import views

router = routers.DefaultRouter()
router.register(r'polls', views.PollViewSet)
router.register(r'questions', views.QuestionViewSet)
router.register(r'choices', views.ChoiceViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('active-polls/', views.ActivePollsView.as_view(), name='active-polls'),
    path('vote/', views.VoteView.as_view(), name='active-polls'),
    path('voted/<int:user>/', views.VotedView.as_view(), name='voted-polls'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api-token-auth/', obtain_auth_token)
]
