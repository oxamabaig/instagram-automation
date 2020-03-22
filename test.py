import flask
from SpotifyPlayer import SpotifyPlayer
import random


app = flask.Flask(__name__)


@app.route('/')
def index():
  return print_index_table()


@app.route('/test')
def test_api_request():
  start_player("temmuz11978","temmuz78")    
  pass


def start_player(un,pwd):
    player = SpotifyPlayer()
    if player.login_again(username=un, password=pwd):
        player.play('https://open.spotify.com/playlist/4AgFMJ84hQmWGhy4b5Xo4t', delay=random.randint(5,15))
        while True:
            player.play_next(delay=random.randint(40,50))


def print_index_table():
  return ('<h1><a href="/test">Click here to start ..!</a></h1>')


if __name__ == '__main__':
  app.run('localhost', 5000, debug=True)