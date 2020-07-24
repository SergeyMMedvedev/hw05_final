from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from .models import Post, Group, Follow, Comment


User = get_user_model()


@override_settings(CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
})
class Hw04Test(TestCase):
    def setUp(self):
        self.client = Client()
        password = User.objects.make_random_password(length=10)
        username = get_random_string(10)
        self.first_name = get_random_string(10)
        self.last_name = get_random_string(10)
        self.user = User.objects.create_user(
            username=username,
            email='asd@asd.com',
            password=password,
            first_name=self.first_name,
            last_name=self.last_name
        )
        self.text_for_new_post = f'Текст для проверки создания ' \
                                 f'нового поста пользователя ' \
                                 f'{self.first_name} {self.last_name}'

        # создадим пост пользователя user2 для проверки,
        # сможет ли его редактировать другой залогиненый пользователь
        # или не залогиненый пользователь

        self.password2 = User.objects.make_random_password(length=10)
        self.username2 = get_random_string(10)
        self.user2 = User.objects.create_user(
            username=self.username2,
            email='asd2@asd2.com',
            password=self.password2,
        )
        self.group = Group.objects.create(
            title='Тестовая группа',
            slug='testgroup',
            description='Описание тестовая группа'
        )
        self.text_for__post_user2 = f'Текст поста пользователя user2' \
                                    f' {self.username2}'
        self.client.login(username=self.username2, password=self.password2)
        self.client.post('/new', {'text': self.text_for__post_user2,
                                  'group': self.group.id})
        self.post_id_user2 = (Post.objects.get(
            text=self.text_for__post_user2).id)
        self.client.logout()
        self.client.login(username=username, password=password)

        # пользователь user3, ни на кого не подписан

        self.password3 = User.objects.make_random_password(length=10)
        self.username3 = get_random_string(10)
        self.user3 = User.objects.create_user(
            username=self.username3,
            email='asd3@asd3.com',
            password=self.password3,
        )

    def testProfilePage(self):
        response = self.client.get(f"/{self.user.username}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, 'profile.html')
        for item in [self.user.username.encode(),
                     self.user.first_name.encode(),
                     self.user.last_name.encode()]:
            self.assertContains(response, item)

    def testNewPostAuth(self):
        response = self.client.post('/new', {'text': self.text_for_new_post})
        self.assertTrue(self.user.posts.filter(text=self.text_for_new_post))
        self.assertEqual(response.status_code, 302)

    def testNewPostNotAuth(self):
        self.client.logout()
        response = self.client.get('/new')
        self.assertRedirects(response, '/auth/login/?next=/new')
        response = self.client.post('/new', {'text': self.text_for_new_post})
        self.assertRedirects(response, '/auth/login/?next=/new')

    def testNewPostEverywhere(self):
        self.client.post('/new', {'text': self.text_for_new_post})
        response = self.client.get('')
        self.assertContains(response, self.text_for_new_post.encode())
        response = self.client.get(f'/{self.user.username}/')
        self.assertContains(response, self.text_for_new_post.encode())
        response = self.client.get(
            f'/{self.user.username}/'
            f'{Post.objects.get(text=self.text_for_new_post).id}/'
        )
        self.assertContains(response, self.text_for_new_post.encode())

    def testEditPostEverywhere(self):
        self.client.post('/new', {'text': self.text_for_new_post})
        post_id = Post.objects.get(text=self.text_for_new_post).id
        new_text = f'изменения ' \
                   f'{self.first_name} {self.last_name}'
        self.client.post(f'/{self.user}/{post_id}/edit/', {'text': new_text})
        self.assertEqual(self.user.posts.get(pk=post_id).text, new_text)
        response = self.client.get('')
        self.assertContains(response, new_text.encode())
        response = self.client.get(f'/{self.user.username}/')
        self.assertContains(response, new_text.encode())
        response = self.client.get(f'/{self.user.username}'
                                   f'/{Post.objects.get(text=new_text).id}/')
        self.assertContains(response, new_text.encode())

    def testLogoutUserPostEdit(self):
        self.client.logout()
        response = self.client.get(
            f'/{self.user2}/{self.post_id_user2}/edit/')
        self.assertRedirects(response,
                             f'/{self.user2}/{self.post_id_user2}/')

    def testUserPostEditUser2(self):
        response = self.client.get(
            f'/{self.user2}/{self.post_id_user2}/edit/')
        self.assertRedirects(response,
                             f'/{self.user2}/{self.post_id_user2}/')

    def testCode404(self):
        response = self.client.get(f'{get_random_string(10)}')
        self.assertEqual(response.status_code, 404)

    def testUploadImage(self):
        self.client.login(username=self.username2, password=self.password2)
        with open('media/posts/testImage.jpg', 'rb') as img:
            self.client.post(
                f'/{self.user2}/{self.post_id_user2}/edit/',
                {'author': self.user2,
                 'text': 'post with image',
                 'group': self.group.id,
                 'image': img}
            )
            response = self.client.get(f'/{self.user2.username}'
                                       f'/{self.post_id_user2}/')
            self.assertContains(response, '<img'.encode())
            self.assertContains(response, 'post with image'.encode())
            # response = self.client.get(f'')
            # self.assertContains(response, '<img'.encode())
            # self.assertContains(response, 'post with image'.encode())
            response = self.client.get(f'/{self.user2.username}/')
            self.assertContains(response, '<img'.encode())
            self.assertContains(response, 'post with image'.encode())
            response = self.client.get(f'/group/{self.group.slug}')
            self.assertContains(response, '<img'.encode())
            self.assertContains(response, 'post with image'.encode())

    def testUploadNotImage(self):
        self.client.login(username=self.username2, password=self.password2)
        with open('media/posts/testText.txt', 'rb') as img:
            self.client.post(
                f'/{self.user2}/{self.post_id_user2}/edit/',
                {'author': self.user2,
                 'text': 'post with image',
                 'group': self.group.id,
                 'image': img}
            )
            response = self.client.get(f'/{self.user2.username}/')
            self.assertNotContains(response, '<img'.encode())

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def testCacheIndex(self):
        self.client.get('')
        self.client.post('/new', {'text': self.text_for_new_post})
        response = self.client.get('')
        self.assertNotContains(response, self.text_for_new_post.encode())
        response = self.client.get(f'/{self.user.username}/')
        self.assertContains(response, self.text_for_new_post.encode())

    def testAuthUserFollow(self):
        self.client.get(f'/{self.user2.username}/')
        self.client.get(f'/{self.user2.username}/follow/')
        self.client.get(f'/{self.user2.username}/follow/')
        self.assertTrue(Follow.objects.get(
            user=self.user.id, author=self.user2.id))
        self.client.get(f'/{self.user2.username}/')
        self.client.get(f'/{self.user2.username}/unfollow/')
        self.assertEqual(Follow.objects.count(), 0)

    def testFollowPosts(self):

        self.client.login(username=self.username2, password=self.password2)
        self.client.post('/new',
                         {'text': f'пост для подписчиков {self.user2}'})
        self.client.force_login(self.user)
        self.client.get(f'/{self.user2.username}/follow/')
        response = self.client.get(f'/follow/')
        self.assertContains(response,
                            f'пост для подписчиков {self.user2}'.encode())
        self.client.force_login(self.user3)
        response = self.client.get(f'/follow/')
        self.assertNotContains(response,
                               f'пост для подписчиков {self.user2}'.encode())

    def testOnlyAuthComments(self):
        self.client.post(f"/{self.user2.username}/"
                         f"{self.post_id_user2}/comment",
                         {'text': 'первый коммент поста user2'})
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.get(
            text='первый коммент поста user2').text,
            'первый коммент поста user2'
                         )
        self.client.logout()
        self.client.post(f"/{self.user2.username}/"
                         f"{self.post_id_user2}/comment",
                         {'text': 'второй комментарий'})
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.filter(
            text='второй комментарий').count(),
            0)
