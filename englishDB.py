import sqlite3
import threading
import json

class Database:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.lock = threading.Lock()

    def add_user(self, chat_id, name):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO `user` (`chat_id`, `name`, `status`, `correct_answers`, `incorrect_answers`, `test_count`, `correct_answers_json`) VALUES (?, ?, 0, 0, 0, 0, '{}')", (chat_id, name))
            self.connection.commit()

    def get_user_name(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("SELECT `name` FROM `user` WHERE `chat_id` = ?", (chat_id,)).fetchone()
            if result:
                return result[0]

    def update_user_name(self, chat_id, new_name):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE `user` SET `name` = ? WHERE `chat_id` = ?", (new_name, chat_id,))
            self.connection.commit()

    def get_user_by_id(self, user_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("SELECT `chat_id`, `name`, `status`, `test_count`, `correct_answers`, `incorrect_answers` FROM `user` WHERE `chat_id` = ?", (user_id,)).fetchone()
            return result


    def get_all_users(self):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("SELECT `chat_id`, `name`, `status`, `test_count`, `correct_answers`, `incorrect_answers` FROM `user`").fetchall()
            return result



    def delete_user(self, user_id):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM `user` WHERE `chat_id` = ?", (user_id,))
            self.connection.commit()



    def user_exist(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("SELECT * FROM `user` WHERE `chat_id` = ?", (chat_id,)).fetchone()
            return bool(result)

    def set_status(self, chat_id, status):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE `user` SET `status` = ? WHERE `chat_id` = ?", (status, chat_id,))
            self.connection.commit()

    def get_status(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("SELECT `status` FROM `user` WHERE `chat_id` = ?", (chat_id,)).fetchone()
            if result:
                return result[0]

    def reset_test_info(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE `user` SET `correct_answers` = 0, `incorrect_answers` = 0, `correct_answers_json` = '{}' WHERE `chat_id` = ?", (chat_id,))
            self.connection.commit()

    def update_test_info(self, chat_id, correct_answers, incorrect_answers):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE `user` SET `correct_answers` = ?, `incorrect_answers` = ? WHERE `chat_id` = ?", (correct_answers, incorrect_answers, chat_id))
            self.connection.commit()

    def increment_correct_count(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE `user` SET `correct_answers` = `correct_answers` + 1 WHERE `chat_id` = ?", (chat_id,))
            self.connection.commit()

    def increment_incorrect_count(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE `user` SET `incorrect_answers` = `incorrect_answers` + 1 WHERE `chat_id` = ?", (chat_id,))
            self.connection.commit()

    def increment_test_count(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE `user` SET `test_count` = `test_count` + 1 WHERE `chat_id` = ?", (chat_id,))
            self.connection.commit()

    def set_correct_answers(self, chat_id, correct_answers):
        with self.lock:
            cursor = self.connection.cursor()
            correct_answers_json = json.dumps(correct_answers)
            # print(f"Setting correct answers for chat_id {chat_id}: {correct_answers_json}")  # Отладочное сообщение
            cursor.execute("UPDATE `user` SET `correct_answers_json` = ? WHERE `chat_id` = ?", (correct_answers_json, chat_id))
            self.connection.commit()

    def get_correct_answers(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("SELECT `correct_answers_json` FROM `user` WHERE `chat_id` = ?", (chat_id,)).fetchone()
            if result:
                # print(f"Retrieved correct answers for chat_id {chat_id}: {result[0]}")  # Отладочное сообщение
                return json.loads(result[0])
            return {}

    def get_correct_count(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("SELECT `correct_answers` FROM `user` WHERE `chat_id` = ?", (chat_id,)).fetchone()
            if result:
                return result[0]
            return 0

    def get_incorrect_count(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("SELECT `incorrect_answers` FROM `user` WHERE `chat_id` = ?", (chat_id,)).fetchone()
            if result:
                return result[0]
            return 0


    def ban_exist(self, user_id):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("SELECT isBaned FROM user WHERE chat_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] == 1 if result else False

    def user_ban(self, user_id, ban=True):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("UPDATE user SET isBaned = ? WHERE chat_id = ?", (1 if ban else 0, user_id))
            self.connection.commit()

    def set_group(self, chat_id, group):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("UPDATE `user` SET `group` = ? WHERE `chat_id` = ?", (group, chat_id,))
            return result


        
    def group_exist(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute("SELECT `group` FROM `user` WHERE `chat_id` = ?", (chat_id,))
            
            return bool(result)