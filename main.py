import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['SQLALCHEMY_DATABASE_URI'] \
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


@app.route('/api/user', methods=['GET'])
def get_all_users():

    query = db.session.query(Game.player_id.distinct().label("player_id"))
    users = [row.player_id for row in query.all()]

    if len(users) is 0:
        return jsonify({'message': 'No users found.'})
    else:
        return jsonify(users)


@app.route('/api/user/<user_id>', methods=['GET'])
def get_all_games_by_user(user_id):

    query = db.session.query(Game).filter_by(player_id=user_id)
    game_ids = [row.id for row in query.all()]

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
        return jsonify({"game_id": game.id, "game_time": game.game_time,
                        "gems": game.gems, "homing_daggers": game.homing_daggers,
                        "daggers_hit": game.daggers_hit,
                        "daggers_fired": game.daggers_fired,
                        "enemies_alive": game.enemies_alive,
                        "enemies_killed": game.enemies_killed})


@app.route('/api/game/<game_number>/all', methods=['GET'])
def get_all_game_states(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    states = [row.serialize for row in query.all()]

    if states is None:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(states)


@app.route('/api/game/<game_number>/game_time', methods=['GET'])
def get_game_time(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    game_time = [row.game_time for row in query.all()]

    if len(game_time) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(game_time)


@app.route('/api/game/<game_number>/gems', methods=['GET'])
def get_game_gems(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    gems = [row.gems for row in query.all()]

    if len(gems) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(gems)


@app.route('/api/game/<game_number>/homing_daggers', methods=['GET'])
def get_game_homing_daggers(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    homing_daggers = [row.homing_daggers for row in query.all()]

    if len(homing_daggers) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(homing_daggers)


@app.route('/api/game/<game_number>/daggers_hit', methods=['GET'])
def get_game_daggers_hit(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    daggers_hit = [row.daggers_hit for row in query.all()]

    if len(daggers_hit) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(daggers_hit)


@app.route('/api/game/<game_number>/daggers_fired', methods=['GET'])
def get_game_daggers_fired(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    daggers_fired = [row.daggers_fired for row in query.all()]

    if len(daggers_fired) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(daggers_fired)


@app.route('/api/game/<game_number>/enemies_alive', methods=['GET'])
def get_game_enemies_alive(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    enemies_alive = [row.enemies_alive for row in query.all()]

    if len(enemies_alive) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(enemies_alive)


@app.route('/api/game', methods=['GET'])
def get_all_games():

    query = db.session.query(Game.id.label("id"))
    games = [row.id for row in query.all()]

    if len(games) is 0:
        return jsonify({'message': 'No games found.'})
    else:
        return jsonify(games)


@app.route('/api/game/<game_number>/enemies_killed', methods=['GET'])
def get_game_enemies_killed(game_number):

    query = db.session.query(State).filter_by(game_id=game_number)
    enemies_killed = [row.enemies_killed for row in query.all()]

    if len(enemies_killed) is 0:
        return jsonify({'message': 'Game not found.'})
    else:
        return jsonify(enemies_killed)


@app.route('/submit_game', methods=['POST'])
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

    return jsonify({'message': 'Game submitted.'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5666)
