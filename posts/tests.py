import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils.crypto import get_random_string

from .models import Post, Group, Follow, Comment


User = get_user_model()


@override_settings(CACHES={
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
})
class Hw04Test(TestCase):
    def setUp(self):
        self.client = Client()
        self.client_user2 = Client()
        self.client_user3 = Client()
        self.client_not_log = Client()
        password = User.objects.make_random_password(length=10)
        username = get_random_string(10)
        self.first_name = get_random_string(10)
        self.last_name = get_random_string(10)
        self.user = User.objects.create_user(
            username=username,
            email="asd@asd.com",
            password=password,
            first_name=self.first_name,
            last_name=self.last_name
        )
        self.text_for_new_post = (f"Текст для проверки создания нового"
                                  f" поста пользователя"
                                  f" {self.first_name} {self.last_name}")

        # создадим пост пользователя user2 для проверки,
        # сможет ли его редактировать другой залогиненый пользователь
        # или не залогиненый пользователь

        self.password2 = User.objects.make_random_password(length=10)
        self.username2 = get_random_string(10)
        self.user2 = User.objects.create_user(
            username=self.username2,
            email="asd2@asd2.com",
            password=self.password2,
        )
        self.group = Group.objects.create(
            title="Тестовая группа",
            slug="testgroup",
            description="Описание тестовая группа"
        )
        self.text_for_post_user2 = (f"Текст поста пользователя"
                                    f" user2 {self.username2}")
        Post.objects.create(
            text=self.text_for_post_user2,
            group=self.group,
            author=self.user2
        )
        self.post_id_user2 = (Post.objects.get(
            text=self.text_for_post_user2).id)

        # пользователь user3, ни на кого не подписан

        self.password3 = User.objects.make_random_password(length=10)
        self.username3 = get_random_string(10)
        self.user3 = User.objects.create_user(
            username=self.username3,
            email="asd3@asd3.com",
            password=self.password3,
        )
        self.client.force_login(self.user)
        self.client_user2.force_login(self.user2)
        self.client_user3.force_login(self.user3)

    def check_contains(self, text):
        urls = (
            reverse("index"),
            reverse("profile", args=[self.user.username]),
            reverse("post", args=[self.user.username,
                                  Post.objects.get(text=text).id])
        )
        for url in urls:
            response = self.client.get(url)
            self.assertContains(response, text)

    def test_profile_page(self):
        response = self.client.get(reverse("profile",
                                           args=[self.user.username]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, "profile.html")
        for item in [self.user.username.encode(),
                     self.user.first_name.encode(),
                     self.user.last_name.encode()]:
            self.assertContains(response, item)

    def test_new_post_auth(self):
        response = self.client.post(reverse("new_post"),
                                    {"text": self.text_for_new_post}
                                    )
        self.assertEqual(Post.objects.filter(
            text=self.text_for_new_post).count(),
                         1)
        self.assertEqual(response.status_code, 302)

    def test_new_post_not_auth(self):
        response = self.client_not_log.get(reverse("new_post"))
        self.assertRedirects(response, "/auth/login/?next=/new")
        response = self.client_not_log.post(
            reverse("new_post"),
            {'text': self.text_for_new_post})
        self.assertRedirects(response, "/auth/login/?next=/new")
        self.assertFalse(Post.objects.filter(
            text=self.text_for_new_post).exists())

    def test_new_post_everywhere(self):
        self.client.post(reverse("new_post"), {"text": self.text_for_new_post})
        self.check_contains(self.text_for_new_post)

    def test_edit_post_everywhere(self):
        self.client.post(reverse("new_post"), {"text": self.text_for_new_post})
        post_id = Post.objects.get(text=self.text_for_new_post).id
        new_text = f"изменения {self.first_name} {self.last_name}"
        self.client.post(reverse("post_edit",
                                 args=[self.user, post_id]),
                         {"text": new_text})
        self.assertEqual(self.user.posts.get(pk=post_id).text, new_text)
        self.check_contains(new_text)

    def test_logout_user_post_edit(self):
        response = self.client_not_log.get(reverse("post_edit",
                                                   args=[self.user2,
                                                         self.post_id_user2]))
        self.assertRedirects(response,
                             reverse("post", args=[self.user2,
                                                   self.post_id_user2]))

    def test_user_post_edit_user2(self):
        response = self.client.get(reverse("post_edit",
                                           args=[self.user2,
                                                 self.post_id_user2]))
        self.assertRedirects(response,
                             reverse("post", args=[self.user2,
                                                   self.post_id_user2]))

    def test_code_404(self):
        response = self.client.get(f"{get_random_string(10)}")
        self.assertEqual(response.status_code, 404)

    def test_upload_image(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            with override_settings(MEDIA_ROOT=temp_directory):
                with open("posts/tests/testImg.jpg", "rb") as img:
                    payload = {"author": self.user2,
                               "text": "post with image",
                               "group": self.group.id,
                               "image": img}
                    self.client_user2.post(reverse("post_edit",
                                                   args=[self.user2,
                                                         self.post_id_user2]),
                                           data=payload)
                    response = self.client.get(reverse("index"))
                    self.assertContains(response, "<img".encode())
                    image_id = Post.objects.get(
                        author=payload["author"],
                        text=payload["text"],
                        group=payload["group"],
                    ).id
                    self.assertContains(response, f"image_{image_id}".encode())

    def test_upload_not_image(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            with override_settings(MEDIA_ROOT=temp_directory):
                with open("posts/tests/testText.txt", "rb") as img:
                    payload = {"author": self.user2,
                               "text": "post with image",
                               "group": self.group.id,
                               "image": img}
                    self.client_user2.post(reverse("post_edit",
                                                   args=[self.user2,
                                                         self.post_id_user2]),
                                           data=payload)
                    self.assertFalse(Post.objects.filter(
                        author=payload["author"],
                        text=payload["text"],
                        group=payload["group"],
                    ).exists())
                    response = self.client.get(reverse("index"))
                    self.assertNotContains(response, "<img".encode())

    @override_settings(CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    })
    def test_cache_index(self):
        self.client.get(reverse("index"))
        self.client.post(reverse("new_post"), {"text": self.text_for_new_post})
        response = self.client.get(reverse("index"))
        self.assertNotContains(response, self.text_for_new_post.encode())
        response = self.client.get(reverse("profile",
                                           args=[self.user.username]))
        self.assertContains(response, self.text_for_new_post.encode())

    def test_auth_user_follow(self):
        self.client.get(reverse("profile_follow", args=[self.user2.username]))
        self.assertTrue(Follow.objects.get(
            user=self.user.id, author=self.user2.id))

    def test_auth_user_unfollow(self):
        self.client.get(reverse("profile_unfollow",
                                args=[self.user3.username]))
        self.assertFalse(Follow.objects.filter(
            user=self.user.id, author=self.user3.id).exists())
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_follow_posts(self):
        self.client_user2.post(reverse("new_post"),
                               {"text": f"пост для подписчиков {self.user2}"})
        self.client.get(reverse("profile_follow", args=[self.user2.username]))
        response = self.client.get(reverse("follow_index"))
        self.assertContains(response,
                            f"пост для подписчиков {self.user2}".encode())
        response = self.client_user3.get(reverse("follow_index"))
        self.assertNotContains(response,
                               f"пост для подписчиков {self.user2}".encode())

    def test_only_auth_comments(self):
        self.client.post(reverse("add_comment",
                                 args=[self.user2.username,
                                       self.post_id_user2]),
                         {"text": "первый коммент поста user2"})
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.get(
            text="первый коммент поста user2").text,
            "первый коммент поста user2"
                         )
        self.client.logout()
        self.client.post(reverse("add_comment",
                                 args=[self.user2.username,
                                       self.post_id_user2]),
                         {"text": "второй комментарий"})
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.filter(
            text="второй комментарий").count(),
            0)
