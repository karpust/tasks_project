# from django.urls import path, include
# from tasks.views import CommentViewSet
# from rest_framework.routers import DefaultRouter
# from tasks.views import TaskViewSet
# from rest_framework_nested import routers
#
#
# router = DefaultRouter()
# router.register(r'tasks', TaskViewSet)
#
# # # Вложенный роутер:
# comments_router = routers.NestedDefaultRouter(router, r'tasks', lookup='task')
# comments_router.register(r'comments', CommentViewSet, basename='task-comments')
#
# urlpatterns = [
#     path('', include(router.urls)),
#     path('', include(comments_router.urls)),
# ]
