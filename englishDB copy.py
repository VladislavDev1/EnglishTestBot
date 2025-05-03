import sqlite3
import threading

class Database:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.lock = threading.Lock()

    def add_user(self, chat_id, name):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO `user` (`chat_id`, `name`) VALUES (?, ?)", (chat_id, name))
            self.connection.commit()

    def get_user_name(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("SELECT `name` FROM `user` WHERE `chat_id` = ?", (chat_id,)).fetchone()
            if result:
                return result[0]

    def get_all_users(self):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("SELECT `chat_id`, `name`, `status`, `test_count`, `correct_answers`, `incorrect_answers` FROM `user`").fetchall()
            return result

    def user_exist(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("SELECT * FROM `user` WHERE `chat_id` = ?", (chat_id,)).fetchone()
            return bool(result)

    def set_status(self, chat_id, status):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE `user` SET `status` = ? WHERE `chat_id` = ?", (status, chat_id))
            self.connection.commit()

    def get_status(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("SELECT `status` FROM `user` WHERE `chat_id` = ?", (chat_id,)).fetchone()
            if result:
                return result[0]

    def update_test_info(self, chat_id, correct_answers, incorrect_answers):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE `user` SET `correct_answers` = ?, `incorrect_answers` = ? WHERE `chat_id` = ?", (correct_answers, incorrect_answers, chat_id))
            self.connection.commit()

    def set_test_count(self, chat_id, count):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE `user` SET `test_count` = `test_count` + ? WHERE `chat_id` = ?", (count, chat_id))
            self.connection.commit()
