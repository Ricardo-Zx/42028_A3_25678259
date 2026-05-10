from django.urls import path
from .views import confirm_checkout, delete_session, history, home, poll_session, receipt

urlpatterns = [
    path("", home, name="home"),
    path("history/", history, name="history"),
    path("poll/<str:session_id>/", poll_session, name="poll_session"),
    path("confirm/<str:session_id>/", confirm_checkout, name="confirm_checkout"),
    path("receipt/<str:session_id>/", receipt, name="receipt"),
    path("delete/<str:session_id>/", delete_session, name="delete_session"),
]

