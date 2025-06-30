from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User


class SingleGroupUserChangeForm(forms.ModelForm):
    # создаю кастомную форму для изменения пользователя в админке:
    # чтобы выбирать одну группу на юзера как в апи:
    groups = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        label="Group",
        help_text="Выберите одну группу для пользователя",
    )

    class Meta:
        model = User
        exclude = ("groups",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            groups_qs = self.instance.groups.all()
            if groups_qs.exists():
                self.fields["groups"].initial = groups_qs.first()


class SingleGroupUserAdmin(UserAdmin):
    form = SingleGroupUserChangeForm
    list_display = ("id", "username", "group_names", "email", "is_active")
    ordering = ("id",)

    def group_names(self, obj):
        # отображать группы в таблице админки(m2m полю туда нельзя)
        return ", ".join([g.name for g in obj.groups.all()])

    group_names.short_description = "Groups"  # имя колонки в таблице

    def save_model(self, request, obj, form, change):
        """Django хранит ManyToMany в отдельной промежуточной таблице
        (auth_user_groups); чтобы добавить запись в эту таблицу, нужно знать user.id.

        А id появляется только после obj.save() — до этого объект существует только в
        памяти и obj.id = None.
        """
        obj.save()  # сначала сохраняю пользователя
        group = form.cleaned_data.get("groups")
        if group:
            obj.groups.set([group])  # устанавливаю одну группу


admin.site.unregister(User)
admin.site.register(User, SingleGroupUserAdmin)
