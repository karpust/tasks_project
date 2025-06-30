import factory
from django.contrib.auth.models import Group, User
from factory import Faker, post_generation


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = Faker("user_name")
    email = Faker("email")
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    is_staff = False

    @post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted or "defaultpassword123"
        self.set_password(password)
        if create:
            self.save(update_fields=["password"])

    @post_generation
    def groups(self, create, extracted, **kwargs):
        if (
            not create
        ):  # проверка был ли сохранен юзер в базе прежде чем добавлю ему поле
            return
        if extracted:
            group, _ = Group.objects.get_or_create(name=extracted)
            self.groups.add(group)
        else:
            group, _ = Group.objects.get_or_create(name="user")
            self.groups.set([group])

    @post_generation
    def is_active(self, create, extracted, **kwargs):
        if create:
            self.is_active = self.id % 2 == 0
            self.save(update_fields=["is_active"])
