from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

from .. import views

urlpatterns = patterns('',
                       url(r'^$', views.competition_index, name='list'),
                       url(r'^(?P<pk>\d+)$', views.CompetitionDetailView.as_view(), name='view'),
                       url(r'^create_competition$', views.CompetitionUpload.as_view(), name='create'),
                       url(r'^edit_competition/(?P<pk>\d+)$', views.CompetitionEdit.as_view(), name='edit'),
                       url(r'^delete_competition/(?P<pk>\d+)$', views.CompetitionDelete.as_view(), name='delete'),
                       url(r'^(?P<id>\d+)/submissions/(?P<phase>\d+)$', views.CompetitionSubmissionsPage.as_view(), name='competition_submissions_page'),
                       url(r'^(?P<id>\d+)/results/(?P<phase>\d+)$', views.CompetitionResultsPage.as_view(), name='competition_results_page'),
                       url(r'^scores/(?P<phase_id>\d+)$',views.ScoresTestView.as_view(template_name='web/competitions/scores.html'),
                           name='scores_test'),
                       )
