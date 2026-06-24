import sqlite3
import threading
import json
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.lock = threading.Lock()
        self._ensure_stage_columns()

    # ------------------------------------------------------------------
    # Миграция: добавляем колонки для текущего этапа, если их нет
    # ------------------------------------------------------------------
    def _ensure_stage_columns(self):
        """Добавляет колонки stage_correct / stage_incorrect / stage_answers_json,
        если их ещё нет (backward-compatible миграция)."""
        with self.lock:
            cursor = self.connection.cursor()
            existing = {
                row[1]
                for row in cursor.execute("PRAGMA table_info(user)").fetchall()
            }
            migrations = {
                "stage_correct": "INTEGER NOT NULL DEFAULT 0",
                "stage_incorrect": "INTEGER NOT NULL DEFAULT 0",
                "stage_answers_json": "TEXT NOT NULL DEFAULT '{}'",
            }
            for col, definition in migrations.items():
                if col not in existing:
                    cursor.execute(f"ALTER TABLE user ADD COLUMN {col} {definition}")
            self.connection.commit()

    # ------------------------------------------------------------------
    # Пользователи
    # ------------------------------------------------------------------
    def add_user(self, chat_id, name):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO `user` "
                "(`chat_id`, `name`, `status`, `correct_answers`, `incorrect_answers`, "
                "`test_count`, `correct_answers_json`, "
                "`stage_correct`, `stage_incorrect`, `stage_answers_json`) "
                "VALUES (?, ?, 0, 0, 0, 0, '{}', 0, 0, '{}')",
                (chat_id, name),
            )
            self.connection.commit()

    def get_user_name(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute(
                "SELECT `name` FROM `user` WHERE `chat_id` = ?", (chat_id,)
            ).fetchone()
            return result[0] if result else None

    def update_user_name(self, chat_id, new_name):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE `user` SET `name` = ? WHERE `chat_id` = ?", (new_name, chat_id)
            )
            self.connection.commit()

    def get_user_by_id(self, user_id):
        with self.lock:
            cursor = self.connection.cursor()
            return cursor.execute(
                "SELECT `chat_id`, `name`, `status`, `test_count`, "
                "`correct_answers`, `incorrect_answers` "
                "FROM `user` WHERE `chat_id` = ?",
                (user_id,),
            ).fetchone()

    def get_all_users(self):
        with self.lock:
            cursor = self.connection.cursor()
            return cursor.execute(
                "SELECT `chat_id`, `name`, `status`, `test_count`, "
                "`correct_answers`, `incorrect_answers` FROM `user`"
            ).fetchall()

    def delete_user(self, user_id):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM `user` WHERE `chat_id` = ?", (user_id,))
            self.connection.commit()

    def user_exist(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute(
                "SELECT 1 FROM `user` WHERE `chat_id` = ?", (chat_id,)
            ).fetchone()
            return bool(result)

    # ------------------------------------------------------------------
    # Статус прохождения теста
    # ------------------------------------------------------------------
    def set_status(self, chat_id, status):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE `user` SET `status` = ? WHERE `chat_id` = ?", (status, chat_id)
            )
            self.connection.commit()

    def compare_and_set_status(self, chat_id, expected_status, new_status) -> bool:
        """Атомарно установить статус: только если текущий статус == expected_status.

        Возвращает True если обновление прошло (rowcount > 0), иначе False.
        Полезно для предотвращения гонок при одновременных переходах этапов.
        """
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE `user` SET `status` = ? WHERE `chat_id` = ? AND `status` = ?",
                (new_status, chat_id, expected_status),
            )
            self.connection.commit()
            return cursor.rowcount > 0

    def get_status(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute(
                "SELECT `status` FROM `user` WHERE `chat_id` = ?", (chat_id,)
            ).fetchone()
            return result[0] if result else None

    # ------------------------------------------------------------------
    # Сброс всего теста (при /tests)
    # ------------------------------------------------------------------
    def reset_test_info(self, chat_id):
        """Сбрасывает суммарные и поэтапные счётчики."""
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE `user` SET "
                "`correct_answers` = 0, `incorrect_answers` = 0, "
                "`correct_answers_json` = '{}', "
                "`stage_correct` = 0, `stage_incorrect` = 0, `stage_answers_json` = '{}' "
                "WHERE `chat_id` = ?",
                (chat_id,),
            )
            self.connection.commit()

    # ------------------------------------------------------------------
    # Счётчики текущего ЭТАПА
    # ------------------------------------------------------------------
    def reset_stage_counters(self, chat_id):
        """Вызывается перед каждым новым этапом."""
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE `user` SET "
                "`stage_correct` = 0, `stage_incorrect` = 0, `stage_answers_json` = '{}' "
                "WHERE `chat_id` = ?",
                (chat_id,),
            )
            self.connection.commit()

    def set_stage_answers(self, chat_id, answers: dict):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE `user` SET `stage_answers_json` = ? WHERE `chat_id` = ?",
                (json.dumps(answers), chat_id),
            )
            self.connection.commit()

    def get_stage_answers(self, chat_id) -> dict:
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute(
                "SELECT `stage_answers_json` FROM `user` WHERE `chat_id` = ?", (chat_id,)
            ).fetchone()
            if result:
                try:
                    return json.loads(result[0])
                except json.JSONDecodeError as e:
                    logger.error(f"stage_answers_json decode error for {chat_id}: {e}")
            return {}

    def increment_stage_correct(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE `user` SET `stage_correct` = `stage_correct` + 1 WHERE `chat_id` = ?",
                (chat_id,),
            )
            self.connection.commit()

    def increment_stage_incorrect(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE `user` SET `stage_incorrect` = `stage_incorrect` + 1 WHERE `chat_id` = ?",
                (chat_id,),
            )
            self.connection.commit()

    def get_stage_counts(self, chat_id) -> tuple[int, int]:
        """Возвращает (stage_correct, stage_incorrect)."""
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute(
                "SELECT `stage_correct`, `stage_incorrect` FROM `user` WHERE `chat_id` = ?",
                (chat_id,),
            ).fetchone()
            return result if result else (0, 0)

    # ------------------------------------------------------------------
    # Суммарные счётчики (по всему тесту)
    # ------------------------------------------------------------------
    def add_to_total_counts(self, chat_id, correct: int, incorrect: int):
        """Прибавляет результаты этапа к суммарным счётчикам."""
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE `user` SET "
                "`correct_answers` = `correct_answers` + ?, "
                "`incorrect_answers` = `incorrect_answers` + ? "
                "WHERE `chat_id` = ?",
                (correct, incorrect, chat_id),
            )
            self.connection.commit()

    def get_total_counts(self, chat_id) -> tuple[int, int]:
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute(
                "SELECT `correct_answers`, `incorrect_answers` FROM `user` WHERE `chat_id` = ?",
                (chat_id,),
            ).fetchone()
            return result if result else (0, 0)

    def increment_test_count(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE `user` SET `test_count` = `test_count` + 1 WHERE `chat_id` = ?",
                (chat_id,),
            )
            self.connection.commit()

    # ------------------------------------------------------------------
    # Совместимость — старые методы (используются в других местах кода)
    # ------------------------------------------------------------------
    def get_correct_count(self, chat_id):
        return self.get_stage_counts(chat_id)[0]

    def get_incorrect_count(self, chat_id):
        return self.get_stage_counts(chat_id)[1]

    def increment_correct_count(self, chat_id):
        self.increment_stage_correct(chat_id)

    def increment_incorrect_count(self, chat_id):
        self.increment_stage_incorrect(chat_id)

    def set_correct_answers(self, chat_id, answers: dict):
        self.set_stage_answers(chat_id, answers)

    def get_correct_answers(self, chat_id) -> dict:
        return self.get_stage_answers(chat_id)

    def update_test_info(self, chat_id, correct, incorrect):
        """Оставлен для совместимости; прибавляет к суммарным счётчикам."""
        self.add_to_total_counts(chat_id, correct, incorrect)

    # ------------------------------------------------------------------
    # Бан
    # ------------------------------------------------------------------
    def ban_exist(self, user_id) -> bool:
        with self.lock:
            cursor = self.connection.cursor()
            try:
                result = cursor.execute(
                    "SELECT `is_banned` FROM `baned_users` WHERE id = ?", (user_id,)
                ).fetchone()
                return result[0] == 1 if result else False
            except sqlite3.OperationalError as e:
                logger.error(f"ban_exist error: {e}")
                return False

    def user_ban(self, user_id, name, ban=True):
        with self.lock:
            cursor = self.connection.cursor()
            try:
                cursor.execute(
                    "INSERT INTO baned_users (`id`, `name`, `is_banned`) VALUES (?,?,?)",
                    (user_id, name, 1 if ban else 0),
                )
                self.connection.commit()
            except sqlite3.IntegrityError:
                cursor.execute(
                    "UPDATE baned_users SET is_banned = ? WHERE id = ?",
                    (1 if ban else 0, user_id),
                )
                self.connection.commit()
            except sqlite3.OperationalError as e:
                logger.error(f"user_ban error: {e}")

    def user_unban(self, user_id):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM baned_users WHERE id = ?", (user_id,))
            self.connection.commit()

    def get_banned_users(self):
        with self.lock:
            cursor = self.connection.cursor()
            try:
                return cursor.execute("SELECT * FROM baned_users").fetchall()
            except sqlite3.OperationalError as e:
                logger.error(f"get_banned_users error: {e}")
                return []

    def get_banned_user_by_id(self, user_id):
        with self.lock:
            cursor = self.connection.cursor()
            try:
                return cursor.execute(
                    "SELECT * FROM baned_users WHERE id = ?", (user_id,)
                ).fetchone()
            except sqlite3.OperationalError as e:
                logger.error(f"get_banned_user_by_id error: {e}")
                return None

    # ------------------------------------------------------------------
    # Группа
    # ------------------------------------------------------------------
    def set_group(self, chat_id, group):
        with self.lock:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE `user` SET `group` = ? WHERE `chat_id` = ?", (group, chat_id)
            )
            self.connection.commit()
            return True

    def group_exist(self, chat_id):
        with self.lock:
            cursor = self.connection.cursor()
            result = cursor.execute(
                "SELECT `group` FROM `user` WHERE `chat_id` = ?", (chat_id,)
            ).fetchone()
            return bool(result)