CREATE TABLE lego_sets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id TEXT NOT NULL UNIQUE,
        set_num TEXT NOT NULL,
        name TEXT NOT NULL,
        year INTEGER,
        theme_id INTEGER,
        theme_name TEXT,
        num_parts INTEGER,
        img_url TEXT,
        description TEXT,
        specifications TEXT,
        features TEXT,
        price REAL,
        currency TEXT,
        availability TEXT,
        last_updated TIMESTAMP
    );

CREATE TABLE minifigures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fig_id TEXT NOT NULL,
        set_id TEXT NOT NULL,
        name TEXT NOT NULL,
        count INTEGER DEFAULT 1,
        FOREIGN KEY (set_id) REFERENCES lego_sets(set_id)
    );

CREATE TABLE prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id TEXT NOT NULL,
        price REAL NOT NULL,
        currency TEXT NOT NULL,
        source TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        FOREIGN KEY (set_id) REFERENCES lego_sets(set_id)
    );

CREATE TABLE images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id TEXT NOT NULL,
        url TEXT NOT NULL,
        cloudflare_url TEXT,
        is_high_res BOOLEAN DEFAULT 0,
        is_main_image BOOLEAN DEFAULT 0,
        type TEXT DEFAULT 'product',
        FOREIGN KEY (set_id) REFERENCES lego_sets(set_id)
    );

CREATE TABLE metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        set_id TEXT NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        FOREIGN KEY (set_id) REFERENCES lego_sets(set_id)
    );

CREATE INDEX idx_lego_sets_set_id ON lego_sets(set_id);

CREATE INDEX idx_minifigures_set_id ON minifigures(set_id);

CREATE INDEX idx_prices_set_id ON prices(set_id);

CREATE INDEX idx_images_set_id ON images(set_id);

CREATE INDEX idx_metadata_set_id ON metadata(set_id);

