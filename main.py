import os
import math
import requests
import json
from datetime import datetime
from flask import Flask, request, jsonify, Response, url_for
from flask import render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bower import Bower
from byte_converters import to_int_16, to_int_32, to_uint_64

# latest release
current_version = "0.1.11"
# lowest release number that is valid
valid_version = "0.1.9"

death_types = ["FALLEN", "SWARMED", "IMPALED", "GORED", "INFESTED", "OPENED", "PURGED",
               "DESECRATED", "SACRIFICED", "EVISCERATED", "ANNIHILATED", "INTOXICATED",
               "ENVENOMATED", "INCARNATED", "DISCARNATED", "BARBED"]

app = Flask(__name__)
app.url_map.strict_slashes = False
Bower(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI') \
    or 'sqlite:////Users/alex/code/ddstats/app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False

db = SQLAlchemy(app)


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    player_id = db.Column(db.Integer, nullable=False)
    granularity = db.Column(db.Integer, nullable=False)
    game_time = db.Column(db.Float, nullable=False)
    death_type = db.Column(db.Integer, nullable=False)
    gems = db.Column(db.Integer, nullable=False)
    homing_daggers = db.Column(db.Integer, nullable=False)
    daggers_fired = db.Column(db.Integer, nullable=False)
    daggers_hit = db.Column(db.Integer, nullable=False)
    enemies_alive = db.Column(db.Integer, nullable=False)
    enemies_killed = db.Column(db.Integer, nullable=False)
    time_stamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class State(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    game_time = db.Column(db.Float, nullable=False)
    gems = db.Column(db.Integer, nullable=False)
    homing_daggers = db.Column(db.Integer, nullable=False)
    daggers_hit = db.Column(db.Integer, nullable=False)
    daggers_fired = db.Column(db.Integer, nullable=False)
    enemies_alive = db.Column(db.Integer, nullable=False)
    enemies_killed = db.Column(db.Integer, nullable=False)

    @property
    def serialize(self):
        return {
                'game_time': self.game_time,
                'gems': self.gems,
                'homing_daggers': self.homing_daggers,
                'daggers_hit': self.daggers_hit,
                'daggers_fired': self.daggers_fired,
                'enemies_alive': self.enemies_alive,
                'enemies_killed': self.enemies_killed
               }


@app.route('/game_log/<game_number>')
def game_log(game_number):
    r = requests.get('http://ddstats.com/api/game/{}/all'.format(game_number))
    data = r.json()
    if "message" in data:
        return data["message"]
    gems_list = []
    homing_daggers_list = []
    accuracy_list = []
    enemies_killed_list = []
    enemies_alive_list = []
    for row in data["state_list"]:
        gems_list.append(row["gems"])
        homing_daggers_list.append(row["homing_daggers"])
        if row["daggers_fired"] is 0:
            accuracy_list.append(0)
        else:
            accuracy_list.append(round((row["daggers_hit"]/row["daggers_fired"])*100, 2))
        enemies_killed_list.append(row["enemies_killed"])
        enemies_alive_list.append(row["enemies_alive"])
    r = requests.get('http://ddstats.com/api/game/{}'.format(game_number))
    game_data = r.json()
    r = requests.get('http://ddstats.com/api/get_scores?user={}'.format(game_data["player_id"]))
    user_data = r.json()

    if game_data["daggers_fired"] is 0:
        accuracy = 0.0
    else:
        accuracy = round(game_data["daggers_hit"] / game_data["daggers_fired"] * 100, 2)

    return render_template('game_log.html',
                           player_name=user_data["player_name"],
                           player_id=game_data["player_id"],
                           game_time=round(game_data["game_time"], 4),
                           death_type=game_data["death_type"],
                           gems=game_data["gems"],
                           homing_daggers=game_data["homing_daggers"],
                           accuracy=accuracy,
                           enemies_alive=game_data["enemies_alive"],
                           enemies_killed=game_data["enemies_killed"],
                           gems_list=gems_list,
                           homing_daggers_list=homing_daggers_list,
                           accuracy_list=accuracy_list,
                           enemies_killed_list=enemies_killed_list,
                           enemies_alive_list=enemies_alive_list)


@app.route('/homing_log/<game_number>/')
def homing_log(game_number):
    r = requests.get('http://ddstats.com/api/game/{}/homing_daggers'.format(game_number))
    data = r.json()
    homing_daggers_list = []
    for row in data["homing_daggers_list"]:
        homing_daggers_list.append(row["homing_daggers"])
    return render_template('homing_log.html', homing_daggers_list=homing_daggers_list)


@app.route('/highcharts_test/')
def highcharts_test():
    return render_template('highcharts_test.html')


@app.route('/releases')
def releases():
    return render_template('releases.html', version=current_version,
                           link=url_for('static', filename='releases/ddstats'+current_version+'.zip'))


@app.route('/classic_homing_log/<game_number>', methods=['GET'])
def get_classic_homing(game_number):
    r = requests.get('http://uncorrected.com:5666/api/game/{}/homing_daggers'.format(game_number))
    data = r.json()
    text = ""
    last = 0
    for row in data["homing_daggers_list"]:
        if int(row["game_time"]) >= 10 and int(row["game_time"]) % 10 is 0:
            text += str(int(row["game_time"])-10) + "s:\t" +\
                    str(row["homing_daggers"]) + "\t|" +\
                    ("~" * math.ceil(row["homing_daggers"]/10)) + "\n"
            last = int(row["game_time"])
    text += str(last) + "s:\t" + str(data["homing_daggers_list"][-1]["homing_daggers"]) +\
        "\t|" + ("~" * math.ceil(data["homing_daggers_list"][-1]["homing_daggers"]/10))
    return Response(text, mimetype='text/plain')


@app.route('/api/user', methods=['GET'])
def get_all_users():

    query = db.session.query(Game.player_id.distinct().label("player_id"))
    user_list = [row.player_id for row in query.all()]
    users = {"user_list": user_list}

    if len(users) is 0:
        return jsonify({'message': 'No users found.'})
    else:
        return jsonify(users)


@app.route('/api/user/<user_id>', methods=['GET'])
def get_all_games_by_user(user_id):

    query = db.session.query(Game).filter_by(player_id=user_id)
    game_id_list = [row.id for row in query.all()]
    game_ids = {"player_id": user_id, "game_id_list": game_id_list}

    if len(game_ids) == 0:
        return jsonify({'message': 'No games found.'})
    else:
        return jsonify(game_ids)


@app.route('/api/game/<game_id>', methods=['GET'])
def get_game_stats(game_id):

    query = db.session.query(Game).filter_by(id=game_id)
    game = query.first()

    if game is None:
        return jsonify({'message': 'Game not found.'})
    else:
        if game.death_type is -1:
            death_type = "RESTART"
        else:
            death_type = death_types[game.death_type]
        return jsonify({"game_id": game.id, "player_id": game.player_id,
                        "game_time": game.game_time,
                        "death_type": death_type,
                        "gems": game.gems, "homing_daggers": game.homing_daggers,
                        "daggers_hit": game.daggers_hit,
                        "daggers_fired": game.daggers_fired,
                        "enemies_alive": game.enemies_alive,
                        "enemies_killed": game.enemies_killed,
                        "time_stamp": game.time_stamp})


@app.route('/api/game/<game_number>/all', methods=['GET'])
def get_all_game_states(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    state_list = [row.serialize for row in query.all()]
    states = {"state_list": state_list}

    if len(state_list) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(states)


@app.route('/api/game/<game_number>/game_time', methods=['GET'])
def get_game_time(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    game_time_list = [row.game_time for row in query.all()]
    game_time = {"game_time_list": game_time_list}

    if len(game_time) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(game_time)


@app.route('/api/game', methods=['GET'])
def get_all_games():

    query = db.session.query(Game.id.label("id"))
    games = [row.id for row in query.all()]
    game_id_list = {"game_id_list": games}

    if len(games) is 0:
        return jsonify({'message': 'No games found.'})
    else:
        return jsonify(game_id_list)


@app.route('/api/game/<game_number>/gems', methods=['GET'])
def get_game_gems(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    gems_list = []
    for row in query.all():
        gems_list.append({"game_time": round(row.game_time, 4),
                          "gems": row.gems})

    gems = {"gems_list": gems_list}

    if len(gems_list) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(gems)


@app.route('/api/game/<game_number>/homing_daggers', methods=['GET'])
def get_game_homing_daggers(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    homing_daggers_list = []
    for row in query.all():
        homing_daggers_list.append({"game_time": round(row.game_time, 4),
                                    "homing_daggers": row.homing_daggers})

    homing_daggers = {"homing_daggers_list": homing_daggers_list}

    if len(homing_daggers_list) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(homing_daggers)


@app.route('/api/game/<game_number>/daggers_hit', methods=['GET'])
def get_game_daggers_hit(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    daggers_hit_list = []
    for row in query.all():
        daggers_hit_list.append({"game_time": round(row.game_time, 4),
                                 "daggers_hit": row.daggers_hit})

    daggers_hit = {"daggers_hit_list": daggers_hit_list}

    if len(daggers_hit_list) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(daggers_hit)


@app.route('/api/game/<game_number>/daggers_fired', methods=['GET'])
def get_game_daggers_fired(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    daggers_fired_list = []
    for row in query.all():
        daggers_fired_list.append({"game_time": round(row.game_time, 4),
                                   "daggers_fired": row.daggers_fired})

    daggers_fired = {"daggers_fired_list": daggers_fired_list}

    if len(daggers_fired_list) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(daggers_fired)


@app.route('/api/game/<game_number>/enemies_killed', methods=['GET'])
def get_game_enemies_killed(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    enemies_killed_list = []
    for row in query.all():
        enemies_killed_list.append({"game_time": round(row.game_time, 4),
                                    "enemies_killed": row.enemies_killed})

    enemies_killed = {"enemies_killed_list": enemies_killed_list}

    if len(enemies_killed_list) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(enemies_killed)


@app.route('/api/game/<game_number>/enemies_alive', methods=['GET'])
def get_game_enemies_alive(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    enemies_alive_list = []
    for row in query.all():
        enemies_alive_list.append({"game_time": round(row.game_time, 4),
                                   "enemies_alive": row.enemies_alive})

    enemies_alive = {"enemies_alive_list": enemies_alive_list}

    if len(enemies_alive_list) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(enemies_alive)


@app.route('/api/submit_game', methods=['POST'])
def create_game():
    data = request.get_json()

    new_game = Game(player_id=data['playerID'], granularity=data['granularity'],
                    game_time=data['inGameTimer'], death_type=data['deathType'],
                    gems=data['gems'], homing_daggers=data['homingDaggers'],
                    daggers_fired=data['daggersFired'], daggers_hit=data['daggersHit'],
                    enemies_alive=data['enemiesAlive'], enemies_killed=data['enemiesKilled'])
    db.session.add(new_game)
    db.session.commit()
    db.session.refresh(new_game)

    for i in range(len(data["inGameTimerVector"])):
        new_state = State(game_id=new_game.id,
                          game_time=data["inGameTimerVector"][i],
                          gems=data["gemsVector"][i],
                          homing_daggers=data["homingDaggersVector"][i],
                          daggers_hit=data["daggersHitVector"][i],
                          daggers_fired=data["daggersFiredVector"][i],
                          enemies_alive=data["enemiesAliveVector"][i],
                          enemies_killed=data["enemiesKilledVector"][i])
        db.session.add(new_state)
    db.session.commit()

    return jsonify({'message': 'Game submitted.', 'game_id': new_game.id})


@app.route('/api/get_motd', methods=['POST'])
def get_motd():

    motd = ""
    with open('motd.json') as f:
        data = json.load(f)
        motd = data["motd"]

    update_available = True
    valid = False

    data = request.get_json()

    sv = data["version"].split('.')
    scv = current_version.split('.')
    svv = valid_version.split('.')

    if (int(sv[0]) > int(scv[0])):
        update_available = False
    elif (int(sv[0]) == int(scv[0])) and (int(sv[1]) > int(scv[1])):
        update_available = False
    elif (int(sv[1]) == int(scv[1])) and (int(sv[2]) >= int(scv[2])):
        update_available = False

    if (int(sv[0]) > int(svv[0])):
        valid = True
    elif (int(sv[0]) == int(svv[0])) and (int(sv[1]) > int(svv[1])):
        valid = True
    elif (int(sv[1]) == int(svv[1])) and (int(sv[2]) >= int(svv[2])):
        valid = True

    return jsonify({'motd': motd,
                    'valid_version': valid,
                    'update_available': update_available})


@app.route('/')
def index():
    content = get_file('dagger.txt')
    return Response(content, mimetype="text/plain")


def root_dir():  # pragma: no cover
    return os.path.abspath(os.path.dirname(__file__))


def get_file(filename):  # pragma: no cover
    try:
        src = os.path.join(root_dir(), filename)
        # Figure out how flask returns static files
        # Tried:
        # - render_template
        # - send_file
        # This should not be so non-obvious
        return open(src).read()
    except IOError as exc:
        return str(exc)


########################################################
#         devil dagger's backend api conversion        #
########################################################

class Leaderboard(object):
    leaderboard_data = ""

    deaths_global = 0
    kills_global = 0
    time_global = 0
    gems_global = 0
    shots_hit_global = 0
    shots_fired_global = 0
    players = 0
    entries = []

    def __init__(self, offset, user=None):
        if user is None:
            self.update(offset)

    def update(self, offset=None):
        if offset is None:
            offset = '0'

        post_values = dict(user='0', level='survival', offset=offset)

        req = requests.post("http://dd.hasmodai.com/backend16/get_scores.php", post_values)
        self.leaderboard_data = req.content

        self.deaths_global      = to_uint_64(self.leaderboard_data, 11)
        self.kills_global       = to_uint_64(self.leaderboard_data, 19)
        self.time_global        = to_uint_64(self.leaderboard_data, 35) / 10000
        self.gems_global        = to_uint_64(self.leaderboard_data, 43)
        self.shots_hit_global   = to_uint_64(self.leaderboard_data, 51)
        self.shots_fired_global = to_uint_64(self.leaderboard_data, 27)
        self.players            = to_int_32(self.leaderboard_data, 75)

        entry_count = to_int_16(self.leaderboard_data, 59)
        rank_iterator = 0
        byte_pos = 83
        self.entries = []
        while(rank_iterator < entry_count):
            entry = Entry()
            username_length = to_int_16(self.leaderboard_data, byte_pos)
            username_bytes = bytearray(username_length)
            byte_pos += 2
            for i in range(byte_pos, byte_pos + username_length):
                username_bytes[i-byte_pos] = self.leaderboard_data[i]

            byte_pos += username_length

            entry.username = username_bytes.decode("utf-8")
            entry.rank = to_int_32(self.leaderboard_data, byte_pos)
            entry.userid = to_int_32(self.leaderboard_data, byte_pos + 4)
            entry.time = to_int_32(self.leaderboard_data, byte_pos + 12) / 10000
            entry.kills = to_int_32(self.leaderboard_data, byte_pos + 16)
            entry.gems = to_int_32(self.leaderboard_data, byte_pos + 28)
            entry.shots_hit = to_int_32(self.leaderboard_data, byte_pos + 24)
            entry.shots_fired = to_int_32(self.leaderboard_data, byte_pos + 20)
            if entry.shots_fired == 0:
                entry.shots_fired = 1
            entry.death_type = death_types[to_int_16(self.leaderboard_data, byte_pos + 32)]
            entry.time_total = to_uint_64(self.leaderboard_data, byte_pos + 60) / 10000
            entry.kills_total = to_uint_64(self.leaderboard_data, byte_pos + 44)
            entry.gems_total = to_uint_64(self.leaderboard_data, byte_pos + 68)
            entry.deaths_total = to_uint_64(self.leaderboard_data, byte_pos + 36)
            entry.shots_hit_total = to_uint_64(self.leaderboard_data, byte_pos + 76)
            entry.shots_fired_total = to_uint_64(self.leaderboard_data, byte_pos + 52)
            if entry.shots_fired_total == 0:
                entry.shots_fired_total = 1

            byte_pos += 88

            self.entries.append(entry)

            rank_iterator += 1

    def get_user(self, user):
        post_values = dict(user=user, level='survival', offset='0')

        req = requests.post("http://dd.hasmodai.com/backend16/get_scores.php", post_values)
        self.leaderboard_data = req.content

        if (user < 1 or user > to_int_32(self.leaderboard_data, 75)):
            return None

        byte_pos = 83

        entry = Entry()

        while(byte_pos < len(self.leaderboard_data)):
            username_length = to_int_16(self.leaderboard_data, byte_pos)
            if (user != to_int_32(self.leaderboard_data, byte_pos + 6 + username_length)):
                byte_pos += 90 + username_length
            else:
                username_length = to_int_16(self.leaderboard_data, byte_pos)
                username_bytes = bytearray(username_length)
                byte_pos += 2
                for i in range(byte_pos, byte_pos + username_length):
                    username_bytes[i-byte_pos] = self.leaderboard_data[i]

                byte_pos += username_length

                entry.username = username_bytes.decode("utf-8")
                entry.rank = to_int_32(self.leaderboard_data, byte_pos)
                entry.userid = to_int_32(self.leaderboard_data, byte_pos + 4)
                entry.time = to_int_32(self.leaderboard_data, byte_pos + 12) / 10000
                entry.kills = to_int_32(self.leaderboard_data, byte_pos + 16)
                entry.gems = to_int_32(self.leaderboard_data, byte_pos + 28)
                entry.shots_hit = to_int_32(self.leaderboard_data, byte_pos + 24)
                entry.shots_fired = to_int_32(self.leaderboard_data, byte_pos + 20)
                if entry.shots_fired == 0:
                    entry.shots_fired = 1
                entry.death_type = death_types[to_int_16(self.leaderboard_data, byte_pos + 32)]
                entry.time_total = to_uint_64(self.leaderboard_data, byte_pos + 60) / 10000
                entry.kills_total = to_uint_64(self.leaderboard_data, byte_pos + 44)
                entry.gems_total = to_uint_64(self.leaderboard_data, byte_pos + 68)
                entry.deaths_total = to_uint_64(self.leaderboard_data, byte_pos + 36)
                entry.shots_hit_total = to_uint_64(self.leaderboard_data, byte_pos + 76)
                entry.shots_fired_total = to_uint_64(self.leaderboard_data, byte_pos + 52)
                if entry.shots_fired_total == 0:
                    entry.shots_fired_total = 1
                return entry


class Entry(object):
    username = ""
    userid = 0
    rank = 0
    time = 0
    kills = 0
    gems = 0
    shots_hit = 0
    shots_fired = 0
    death_type = ""
    time_total = 0
    kills_total = 0
    gems_total = 0
    deaths_total = 0
    shots_hit_total = 0
    shots_fired_total = 0

    def __eq__(self, other):
        try:
            return (self.rank, self.time, self.kills) == (other.rank, other.time,
                                                          other.kills)
        except AttributeError:
            return NotImplemented


@app.route('/api/get_scores', methods=['GET'])
def get_scores():
    offset = request.args.get('offset', default='0', type=int)
    user = request.args.get('user', default=None, type=int)
    leaderboard = Leaderboard(offset, user)
    if user is None:
        entry_list = []
        for entry in leaderboard.entries:
            entry_list.append({"player_name": entry.username,
                               "player_id": entry.userid,
                               "rank": entry.rank,
                               "game_time": entry.time,
                               "gems": entry.gems,
                               "daggers_hit": entry.shots_hit,
                               "daggers_fired": entry.shots_fired,
                               "enemies_killed": entry.kills,
                               "death_type": entry.death_type,
                               "total_game_time": entry.time_total,
                               "total_gems": entry.gems_total,
                               "total_daggers_hit": entry.shots_hit_total,
                               "total_daggers_fired": entry.shots_fired_total,
                               "total_enemies_killed": entry.kills_total,
                               "total_deaths": entry.deaths_total})

        leaderboard_json = {"global_player_count": leaderboard.players,
                            "global_time": leaderboard.time_global,
                            "global_gems": leaderboard.gems_global,
                            "global_daggers_hit": leaderboard.shots_hit_global,
                            "global_daggers_fired": leaderboard.shots_fired_global,
                            "global_enemies_killed": leaderboard.kills_global,
                            "global_deaths": leaderboard.deaths_global,
                            "entry_list": entry_list}
    else:
        entry = leaderboard.get_user(user)
        if entry is not None:
            leaderboard_json = {"player_name": entry.username,
                                "player_id": entry.userid,
                                "rank": entry.rank,
                                "game_time": entry.time,
                                "gems": entry.gems,
                                "daggers_hit": entry.shots_hit,
                                "daggers_fired": entry.shots_fired,
                                "enemies_killed": entry.kills,
                                "death_type": entry.death_type,
                                "total_game_time": entry.time_total,
                                "total_gems": entry.gems_total,
                                "total_daggers_hit": entry.shots_hit_total,
                                "total_daggers_fired": entry.shots_fired_total,
                                "total_enemies_killed": entry.kills_total,
                                "total_deaths": entry.deaths_total}
        else:
            leaderboard_json = {"message": "Invalid user ID."}

    return jsonify(leaderboard_json)


########################################################
#     end of devil dagger's backend api conversion     #
########################################################


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5666)
