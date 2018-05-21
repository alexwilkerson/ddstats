CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY,
    playerID INTEGER NOT NULL,
    granularity INTEGER NOT NULL,
    game_time FLOAT NOT NULL,
    death_type INTEGER NOT NULL,
    gems INTEGER NOT NULL,
    homing_daggers INTEGER NOT NULL,
    daggers_fired INTEGER NOT NULL,
    daggers_hit INTEGER NOT NULL,
    enemies_alive INTEGER NOT NULL,
    enemies_killed INTEGER NOT NULL,
    time_stamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS states (
    game_id INTEGER NOT NULL,
    state_number INTEGER NOT NULL,
    game_time FLOAT NOT NULL,
    gems INTEGER NOT NULL,
    homing_daggers INTEGER NOT NULL,
    daggers_hit INTEGER NOT NULL,
    daggers_fired INTEGER NOT NULL,
    enemies_alive INTEGER NOT NULL,
    enemies_killed INTEGER NOT NULL,
    FOREIGN KEY(game_id) REFERENCES games(id)
);
