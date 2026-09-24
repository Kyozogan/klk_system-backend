from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BeneficiaryViewSet, GuardianViewSet, CountyViewSet, SponsorViewSet, BeneficiaryDocumentViewSet, GuardianUpdateViewSet

router = DefaultRouter()
router.register('records', BeneficiaryViewSet, basename='beneficiary')
router.register('guardians', GuardianUpdateViewSet, basename='guardian')
router.register('counties', CountyViewSet, basename='county')
router.register('sponsors', SponsorViewSet, basename='sponsor')
router.register('documents', BeneficiaryDocumentViewSet, basename='document')

urlpatterns = [path('', include(router.urls))]
