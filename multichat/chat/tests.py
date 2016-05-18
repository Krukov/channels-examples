import json
from django.contrib import auth
from channels.tests import ChannelTestCase, Client, apply_routes

from .routing import custom_routing, websocket_routing
from .models import Room

User = auth.get_user_model()


@apply_routes([custom_routing, websocket_routing])
class TestChat(ChannelTestCase):

    def test_chat(self):
        room_1 = Room.objects.create(title='room_1')
        room_2 = Room.objects.create(title='room_2')
        user1 = User.objects.create_user('user_1', 'user_1@test.test', '123')
        user2 = User.objects.create_user('user_2', 'user_2@test.test', '123')

        # login as first user
        self.client.login(username=user1.username, password='123')
        self.client.send_and_consume('websocket.connect')
        self.client.send_and_consume('chat.receive', {'command': 'join', 'room': room_1.id})

        # create second client and join room 1 and 2 as user2
        second_client = Client()
        second_client.login(username=user2.username, password='123')
        second_client.send_and_consume('websocket.connect')
        second_client.send_and_consume('chat.receive', {'command': 'join', 'room': room_1.id})
        second_client.receive()  # drop info message after joining
        second_client.send_and_consume('chat.receive', {'command': 'join', 'room': room_2.id})
        second_client.receive()  # drop info message

        # first client send message to room 1
        self.client.send_and_consume('chat.receive',
                                     {'command': 'send', 'message': 'test message from user 1', 'room': room_1.id})

        # check that second user apply message
        self.assertDictEqual(second_client.receive(),
                             {'text': json.dumps({"message": "test message from user 1",
                                                  "room": str(room_1.id),
                                                  "username": user1.username})})

        # first client send message to room 2
        self.client.send_and_consume('chat.receive', {'command': 'send',
                                                      'message': 'test message from user 1 for 2 room',
                                                      'room': room_2.id})

        self.assertIsNone(second_client.receive())