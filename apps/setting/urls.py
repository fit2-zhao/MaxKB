from django.urls import path

from . import views

app_name = "team"
urlpatterns = [
    path('team/member', views.TeamMember.as_view(), name="team"),
    path('team/member/_batch', views.TeamMember.Batch.as_view()),
    path('team/member/<str:member_id>', views.TeamMember.Operate.as_view(), name='member'),
    path('provider/<str:provider>/<str:method>', views.Provide.Exec.as_view(), name='provide_exec'),
    path('provider', views.Provide.as_view(), name='provide'),
    path('provider/model_type_list', views.Provide.ModelTypeList.as_view(), name="provider/model_type_list"),
    path('provider/model_list', views.Provide.ModelList.as_view(),
         name="provider/model_name_list"),
    path('provider/model_form', views.Provide.ModelForm.as_view(),
         name="provider/model_form"),
    path('model', views.Model.as_view(), name='model'),
    path('model/<str:model_id>', views.Model.Operate.as_view(), name='model/operate'),
    path('email_setting', views.SystemSetting.Email.as_view(), name='email_setting')

]
