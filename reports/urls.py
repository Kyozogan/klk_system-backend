from django.urls import path
from .views import DashboardStatsView, PerformanceAnalyticsView

urlpatterns = [
    path('dashboard/', DashboardStatsView.as_view()),
    path('performance-analytics/', PerformanceAnalyticsView.as_view()),
]
