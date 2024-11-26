import sqlite3

def add_column(database, table_name, column_name, column_type):
    connection = sqlite3.connect(database)
    cursor = connection.cursor()
    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
    connection.commit()
    connection.close()

add_column('english.db', 'user', 'status_string', 'TEXT DEFAULT "one"')


def migrate_status(database):
    connection = sqlite3.connect(database)
    cursor = connection.cursor()
    
    status_mapping = {
        1: 'one',
        2: 'two',
        3: 'three',
        4: 'four',
        5: 'done'
    }

    for num_status, str_status in status_mapping.items():
        cursor.execute("UPDATE user SET status_string = ? WHERE status = ?", (str_status, num_status))
    
    connection.commit()
    connection.close()

migrate_status('english.db')