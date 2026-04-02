import telebot
import sqlite3
import re
import random
import time
import logging
import threading
from datetime import datetime, timedelta


def get_moscow_time():
    """Возвращает текущее время в московском часовом поясе"""
    return datetime.now(MOSCOW_TZ)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

BOT_TOKEN = '8581773614:AAFy7J0smI7Omp3BSsQcnChOWAdxhoV3188'

try:
    bot = telebot.TeleBot(BOT_TOKEN)
    logging.info("✅ Бот успешно создан")
except Exception as e:
    logging.error(f"❌ Ошибка создания бота: {e}")
    exit(1)

class RobustBot:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.is_running = True
        
    def poll(self):
        """Запускает polling с обработкой ошибок"""
        while self.is_running:
            try:
                logging.info("🔄 Запуск polling...")
                self.bot.infinity_polling(timeout=60, long_polling_timeout=60)
                
            except Exception as e:
                logging.error(f"❌ Ошибка в polling: {e}")
                time.sleep(30)
    
    def stop(self):
        """Останавливает бота"""
        self.is_running = False
        logging.info("🛑 Бот остановлен")
    
    def restart(self):
        """Перезапускает бота"""
        logging.info("🔄 Перезапуск бота...")
        self.stop()
        time.sleep(2)
        self.is_running = True
        self.poll()

# Создаем устойчивого бота
robust_bot = RobustBot(bot)

def safe_edit_message(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    """
    Безопасное редактирование сообщения с обработкой распространенных ошибки
    """
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except Exception as e:
        error_msg = str(e)
        
        # Игнорируем безвредные ошибки
        if "message is not modified" in error_msg:
            # Сообщение уже имеет такое содержимое - это нормально
            return True
        elif "message to edit not found" in error_msg:
            logging.warning(f"Сообщение {message_id} не найдено в чате {chat_id}")
            return False
        elif "bot can't edit the message" in error_msg:
            logging.warning(f"Бот не может редактировать сообщение {message_id}")
            return False
        elif "Bad Request" in error_msg:
            logging.warning(f"Bad Request при редактировании сообщения {message_id}: {error_msg}")
            return False
        else:
            logging.error(f"Неизвестная ошибка при редактировании сообщения {message_id}: {error_msg}")
            return False

class MatchmakingBot:
    def __init__(self):
        # Обычные лобби (Default League)
        self.lobbies = {
            'lobby1': {'players': [], 'status': 'waiting', 'confirmed': [], 'max_players': 10, 'lobby_message_id': None, 'allowed_devices': ['Android'], 'league': 'default', 'lobby_messages': {}},
            'lobby2': {'players': [], 'status': 'waiting', 'confirmed': [], 'max_players': 10, 'lobby_message_id': None, 'allowed_devices': ['Android'], 'league': 'default', 'lobby_messages': {}},
            'lobby3': {'players': [], 'status': 'waiting', 'confirmed': [], 'max_players': 10, 'lobby_message_id': None, 'allowed_devices': ['Android', 'PC'], 'league': 'default', 'lobby_messages': {}},
            'lobby4': {'players': [], 'status': 'waiting', 'confirmed': [], 'max_players': 10, 'lobby_message_id': None, 'allowed_devices': ['Android', 'PC'], 'league': 'default', 'lobby_messages': {}},
            'lobby5': {'players': [], 'status': 'waiting', 'confirmed': [], 'max_players': 10, 'lobby_message_id': None, 'allowed_devices': ['PC'], 'league': 'default', 'lobby_messages': {}},
            'lobby6': {'players': [], 'status': 'waiting', 'confirmed': [], 'max_players': 4, 'lobby_message_id': None, 'allowed_devices': ['Android', 'PC'], 'league': 'default', 'lobby_messages': {}},
            'lobby7': {'players': [], 'status': 'waiting', 'confirmed': [], 'max_players': 4, 'lobby_message_id': None, 'allowed_devices': ['Android'], 'league': 'default', 'lobby_messages': {}}  # Новое лобби 7
        }
        
        # Pro League лобби
        self.pro_lobbies = {
            'pro_lobby1': {'players': [], 'status': 'waiting', 'confirmed': [], 'max_players': 4, 'lobby_message_id': None, 'allowed_devices': ['Android'], 'league': 'pro', 'mode': '2x2', 'lobby_messages': {}},
            'pro_lobby2': {'players': [], 'status': 'waiting', 'confirmed': [], 'max_players': 4, 'lobby_message_id': None, 'allowed_devices': ['PC'], 'league': 'pro', 'mode': '2x2', 'lobby_messages': {}},
            'pro_lobby3': {'players': [], 'status': 'waiting', 'confirmed': [], 'max_players': 10, 'lobby_message_id': None, 'allowed_devices': ['Android'], 'league': 'pro', 'mode': '5x5', 'lobby_messages': {}},
            'pro_lobby4': {'players': [], 'status': 'waiting', 'confirmed': [], 'max_players': 10, 'lobby_message_id': None, 'allowed_devices': ['PC'], 'league': 'pro', 'mode': '5x5', 'lobby_messages': {}}
        }
        
        self.admin_ids = [6909945528]
        self.wreg_admins = []  # Теперь команда /upd доступна всем админам
        self.log_chat_id = [1135455373, 5308916136, 7609266716]
        self.match_group_id = -1003783634756  # Группа для матчей
        self.ticket_group_id = -1003783634756 # Группа для тикетов
        self.current_match_scores = {}
        self.pending_registrations = {}
        self.user_lobbies = {}
        self.user_warnings = {}
        self.muted_users = {}
        self.banned_users = {}
        self.tickets = {}
        self.active_matches = {}
        self.user_match_threads = {}
        self.parties = {}
        self.party_invites = {}
        self.match_results_pending = {}
        self.map_veto_sessions = {}  # Сессии бан-пика карт
        self.last_match_threads = {}  # Защита от дублирования веток
        self.veto_messages = {}  # Храним ID сообщений бан-пика для каждого матча
        self.user_devices = {}  # Храним устройства пользователей
        self.pro_league_users = {}  # Пользователи с доступом к Pro League
        self.user_leagues = {}  # Текущая лига пользователя
        self.ticket_sessions = {}  # Сессии создания тикетов
        self.registered_players_in_thread = {}  # Храним зарегистрированных игроков по веткам
        self.rolled_back_players_in_thread = {}  # Храним откатанных игроков по веткам
        self.match_scores = {}  # Храним счета матчей по веткам
        self.confirmation_warnings = {}  # Храним предупреждения за неподтверждение матча
        self.init_db()
        self.load_pro_league_users()
    
    def init_db(self):
        """Инициализация базы данных"""
        try:
            conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
            cursor = conn.cursor()
            
            # Создание таблицы игроков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    nickname TEXT UNIQUE,
                    game_id TEXT UNIQUE,
                    elo INTEGER DEFAULT 0,
                    kills INTEGER DEFAULT 0,
                    assists INTEGER DEFAULT 0,
                    deaths INTEGER DEFAULT 0,
                    total_score INTEGER DEFAULT 0,
                    matches_played INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    warnings INTEGER DEFAULT 0,
                    confirmation_warnings INTEGER DEFAULT 0,
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT,
                    ban_until TIMESTAMP,
                    is_muted BOOLEAN DEFAULT FALSE,
                    mute_reason TEXT,
                    mute_until TIMESTAMP,
                    calibration_matches INTEGER DEFAULT 0,
                    device TEXT DEFAULT 'Android',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Создание таблицы матчей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lobby_id TEXT,
                    team_ct TEXT,
                    team_t TEXT,
                    score_ct INTEGER DEFAULT 0,
                    score_t INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    map TEXT DEFAULT 'Неизвестна',
                    league TEXT DEFAULT 'default'
                )
            ''')
            
            # Создание таблицы истории ELO
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS elo_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    old_elo INTEGER,
                    new_elo INTEGER,
                    match_id INTEGER,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Создание таблицы матчей игроков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    match_id INTEGER,
                    kills INTEGER DEFAULT 0,
                    assists INTEGER DEFAULT 0,
                    deaths INTEGER DEFAULT 0,
                    total_score INTEGER DEFAULT 0,
                    elo_change INTEGER DEFAULT 0,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES players (user_id)
                )
            ''')
            
            # Создание таблицы тикетов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    user_nickname TEXT,
                    message TEXT,
                    status TEXT DEFAULT 'open',
                    admin_response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Создание таблицы администраторов wreg (больше не используется)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS wreg_admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Создание таблицы пользователей Pro League
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pro_league_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Проверка и добавление отсутствующих колонок
            try:
                cursor.execute("SELECT calibration_matches FROM players LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE players ADD COLUMN calibration_matches INTEGER DEFAULT 0")
            
            try:
                cursor.execute("SELECT is_banned FROM players LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE players ADD COLUMN is_banned BOOLEAN DEFAULT FALSE")
                cursor.execute("ALTER TABLE players ADD COLUMN ban_reason TEXT")
                cursor.execute("ALTER TABLE players ADD COLUMN ban_until TIMESTAMP")
                cursor.execute("ALTER TABLE players ADD COLUMN is_muted BOOLEAN DEFAULT FALSE")
                cursor.execute("ALTER TABLE players ADD COLUMN mute_reason TEXT")
                cursor.execute("ALTER TABLE players ADD COLUMN mute_until TIMESTAMP")
            
            try:
                cursor.execute("SELECT device FROM players LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE players ADD COLUMN device TEXT DEFAULT 'Android'")
            
            try:
                cursor.execute("SELECT map FROM matches LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE matches ADD COLUMN map TEXT DEFAULT 'Неизвестна'")
            
            try:
                cursor.execute("SELECT league FROM matches LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE matches ADD COLUMN league TEXT DEFAULT 'default'")
            
            try:
                cursor.execute("SELECT confirmation_warnings FROM players LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE players ADD COLUMN confirmation_warnings INTEGER DEFAULT 0")
            
            conn.commit()
            conn.close()
            logging.info("✅ База данных готова")
        except Exception as e:
            logging.error(f"❌ Ошибка инициализации БД: {e}")
    
    def load_pro_league_users(self):
        """Загружает список пользователей с доступом к Pro League"""
        try:
            conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pro_league_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('SELECT user_id FROM pro_league_users')
            results = cursor.fetchall()
            
            self.pro_league_users = {result[0] for result in results}
            
            conn.close()
            logging.info(f"✅ Загружено {len(self.pro_league_users)} пользователей с доступом к Pro League")
        except Exception as e:
            logging.error(f"❌ Ошибка загрузки пользователей Pro League: {e}")
            self.pro_league_users = set()

    def add_pro_league_user(self, user_id):
        """Добавляет пользователя в Pro League"""
        try:
            conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute('INSERT OR IGNORE INTO pro_league_users (user_id) VALUES (?)', (user_id,))
            conn.commit()
            conn.close()
            
            self.pro_league_users.add(user_id)
            
            return True, f"✅ Пользователь {user_id} добавлен в Pro League"
        except Exception as e:
            return False, f"❌ Ошибка добавления в Pro League: {str(e)}"

    def remove_pro_league_user(self, user_id):
        """Удаляет пользователя из Pro League"""
        try:
            conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM pro_league_users WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()
            
            if user_id in self.pro_league_users:
                self.pro_league_users.remove(user_id)
            
            return True, f"✅ Пользователь {user_id} удален из Pro League"
        except Exception as e:
            return False, f"❌ Ошибка удаления из Pro League: {str(e)}"

    def has_pro_league_access(self, user_id):
        """Проверяет, есть ли у пользователя доступ к Pro League"""
        return user_id in self.pro_league_users

    def set_user_league(self, user_id, league):
        """Устанавливает лигу для пользователя"""
        current_league = self.get_user_league(user_id)
        if current_league == league:
            return False, "⚠️ Ты уже находишься в этой лиге."
        
        if league == 'pro' and not self.has_pro_league_access(user_id):
            return False, "❌ У вас нет доступа к Pro League. Обратитесь к @blesswayknow для получения доступа."
        
        self.user_leagues[user_id] = league
        return True, f"✅ Лига изменена на {league.upper()}"

    def get_user_league(self, user_id):
        """Получает текущую лигу пользователя"""
        return self.user_leagues.get(user_id, 'default')

    def get_user_device(self, user_id):
        """Получает устройство пользователя"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT device FROM players WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                return result[0]
            else:
                # Устанавливаем значение по умолчанию
                cursor.execute('UPDATE players SET device = ? WHERE user_id = ?', ('Android', user_id))
                conn.commit()
                return 'Android'
        except Exception as e:
            logging.error(f"Ошибка получения устройства пользователя: {e}")
            return 'Android'
        finally:
            conn.close()

    def update_user_device(self, user_id, device):
        """Обновляет устройство пользователя"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            cursor.execute('UPDATE players SET device = ? WHERE user_id = ?', (device, user_id))
            conn.commit()
            return True, "✅ Устройство успешно изменено!"
        except Exception as e:
            return False, f"❌ Ошибка при изменении устройства: {str(e)}"
        finally:
            conn.close()

    def get_faceit_level(self, elo):
        """Определяет уровень Faceit на основе ELO по новой системе"""
        if elo <= 800:
            return 1
        elif 801 <= elo <= 950:
            return 2
        elif 951 <= elo <= 1100:
            return 3
        elif 1101 <= elo <= 1250:
            return 4
        elif 1251 <= elo <= 1400:
            return 5
        elif 1401 <= elo <= 1550:
            return 6
        elif 1551 <= elo <= 1700:
            return 7
        elif 1701 <= elo <= 1850:
            return 8
        elif 1851 <= elo <= 2000:
            return 9
        else:
            return 10  # от 2001 ELO

    def get_faceit_level_emoji(self, level):
        """Возвращает эмодзи для уровня Faceit"""
        emojis = {
            1: "1️⃣",
            2: "2️⃣", 
            3: "3️⃣",
            4: "4️⃣",
            5: "5️⃣",
            6: "6️⃣",
            7: "7️⃣",
            8: "8️⃣", 
            9: "9️⃣",
            10: "🔟"
        }
        return emojis.get(level, "1️⃣")

    def calculate_elo_change(self, user_id, is_winner, current_elo):
        """Рассчитывает изменение ELO с учетом новой системы уровней"""
        faceit_level = self.get_faceit_level(current_elo)
        
        # Калибровочные матчи (первые 3 матча)
        calibration_matches = self.get_calibration_matches(user_id)
        
        if calibration_matches < 3:
            # Калибровочные матчи: +50 за победу, -20 за поражение
            if is_winner:
                return 50
            else:
                return -20
        else:
            # После калибровки используем новую систему по уровням
            if faceit_level == 1:
                # 1 LVL: победа +50, поражение -20
                return 50 if is_winner else -20
            elif faceit_level == 2:
                # 2 LVL: победа +50, поражение -25
                return 50 if is_winner else -25
            elif faceit_level == 3:
                # 3 LVL: победа +45, поражение -25
                return 45 if is_winner else -25
            elif faceit_level == 4:
                # 4 LVL: победа +40, поражение -30
                return 40 if is_winner else -30
            elif faceit_level == 5:
                # 5 LVL: победа +40, поражение -30
                return 40 if is_winner else -30
            elif faceit_level == 6:
                # 6 LVL: победа +35, поражение -30
                return 35 if is_winner else -30
            elif faceit_level == 7:
                # 7 LVL: победа +30, поражение -30
                return 30 if is_winner else -30
            elif faceit_level == 8:
                # 8 LVL: победа +25, поражение -30
                return 25 if is_winner else -30
            elif faceit_level == 9:
                # 9 LVL: победа +20, поражение -35
                return 20 if is_winner else -35
            elif faceit_level == 10:
                # 10 LVL: победа +20, поражение -40
                return 20 if is_winner else -40
            else:
                return 30 if is_winner else -10  # fallback

    def get_calibration_matches(self, user_id):
        """Получает количество сыгранных калибровочных матчей"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('SELECT calibration_matches FROM players WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0

    def update_calibration_matches(self, user_id):
        """Обновляет счетчик калибровочных матчей"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE players 
            SET calibration_matches = calibration_matches + 1 
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()

    def register_user(self, user_id, nickname, game_id, device='Android'):
        # Проверка никнейма - минимум 2 символа
        if len(nickname.strip()) < 2:
            return False, "❌ Никнейм должен содержать минимум 2 символа!"
        
        # Проверка на пробелы в никнейме
        if ' ' in nickname.strip():
            return False, "❌ Никнейм не должен содержать пробелов! Используйте одно слово."
        
        # Проверка игрового ID - минимум 3 символа (буквы и цифры разрешены)
        if len(game_id.strip()) < 3:
            return False, "❌ Игровой ID должен содержать минимум 3 символа!"
        
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            # Проверяем, не занят ли никнейм
            cursor.execute('SELECT user_id FROM players WHERE nickname = ?', (nickname,))
            if cursor.fetchone():
                return False, "❌ Этот никнейм уже занят! Попробуйте другой."
            
            # Проверяем, не занят ли игровой ID
            cursor.execute('SELECT user_id FROM players WHERE game_id = ?', (game_id,))
            if cursor.fetchone():
                return False, "❌ Этот игровой ID уже занят! Попробуйте другой."
            
            cursor.execute('''
                INSERT INTO players (user_id, nickname, game_id, elo, matches_played, calibration_matches, warnings, device, confirmation_warnings)
                VALUES (?, ?, ?, 0, 0, 0, 0, ?, 0)
            ''', (user_id, nickname, game_id, device))
            conn.commit()
            
            # Устанавливаем лигу по умолчанию
            self.user_leagues[user_id] = 'default'
            
            return True, "✅ Регистрация успешна! Начните калибровочные матчи. Ваш начальный SFP: 0"
        except sqlite3.IntegrityError as e:
            if "nickname" in str(e):
                return False, "❌ Этот никнейм уже занят! Попробуйте другой."
            elif "game_id" in str(e):
                return False, "❌ Этот игровой ID уже занят! Попробуйте другой."
            else:
                cursor.execute('UPDATE players SET elo = 0, calibration_matches = 0 WHERE user_id = ?', (user_id,))
                conn.commit()
                return False, "⚠️ Вы уже зарегистрированы! SFP сброшен для калибровки."
        finally:
            conn.close()

    def update_user_game_id(self, user_id, new_game_id):
        """Обновляет игровой ID пользователя"""
        # Разрешаем буквы и цифры, минимум 3 символа
        if len(new_game_id.strip()) < 3:
            return False, "❌ Игровой ID должен содержать минимум 3 символа!"
        
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            # Проверяем, не занят ли игровой ID другим пользователем
            cursor.execute('SELECT user_id FROM players WHERE game_id = ? AND user_id != ?', (new_game_id, user_id))
            if cursor.fetchone():
                return False, "❌ Этот игровой ID уже занят! Попробуйте другой."
            
            cursor.execute('UPDATE players SET game_id = ? WHERE user_id = ?', (new_game_id, user_id))
            conn.commit()
            return True, "✅ Игровой ID успешно изменен!"
        except sqlite3.IntegrityError:
            return False, "❌ Этот игровой ID уже занят! Попробуйте другой."
        except Exception as e:
            return False, f"❌ Ошибка при изменении игрового ID: {str(e)}"
        finally:
            conn.close()

    def get_user_profile(self, user_id):
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT nickname, game_id, elo, kills, assists, deaths, total_score, 
                   matches_played, wins, losses, warnings, confirmation_warnings, is_banned, is_muted, calibration_matches, device
            FROM players WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            faceit_level = self.get_faceit_level(result[2])
            level_emoji = self.get_faceit_level_emoji(faceit_level)
            current_league = self.get_user_league(user_id)
            has_pro_access = self.has_pro_league_access(user_id)
            
            return {
                'nickname': result[0],
                'game_id': result[1],
                'elo': result[2],
                'kills': result[3],
                'assists': result[4],
                'deaths': result[5],
                'total_score': result[6],
                'matches_played': result[7],
                'wins': result[8],
                'losses': result[9],
                'warnings': result[10],
                'confirmation_warnings': result[11],
                'is_banned': result[12],
                'is_muted': result[13],
                'calibration_matches': result[14],
                'device': result[15],
                'faceit_level': faceit_level,
                'level_emoji': level_emoji,
                'current_league': current_league,
                'has_pro_access': has_pro_access
            }
        return None

    def get_match_history(self, user_id, limit=5):
        """Получает историю матчей пользователя"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT pm.match_id, pm.kills, pm.assists, pm.deaths, pm.elo_change, pm.result,
                       m.lobby_id, m.status, m.created_at, m.map, m.league
                FROM player_matches pm
                LEFT JOIN matches m ON pm.match_id = m.id
                WHERE pm.user_id = ?
                ORDER BY pm.created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            matches = cursor.fetchall()
            match_history = []
            
            for i, match in enumerate(matches, 1):
                match_id, kills, assists, deaths, elo_change, result, lobby_id, status, created_at, map_name, league = match
                
                # Определяем режим игры на основе lobby_id
                if lobby_id in ['lobby1', 'lobby2', 'lobby3', 'lobby4', 'lobby5'] or lobby_id in ['pro_lobby3', 'pro_lobby4']:
                    game_mode = "5×5"
                elif lobby_id == 'lobby6' or lobby_id == 'lobby7' or lobby_id in ['pro_lobby1', 'pro_lobby2']:
                    game_mode = "2×2"
                else:
                    game_mode = "Неизвестно"
                
                # Если карта не указана, ставим "Неизвестна"
                if not map_name:
                    map_name = "Неизвестна"
                
                # Определяем статус матча
                if status == 'completed':
                    match_status = "рассмотрено"
                else:
                    match_status = "на рассмотрении"
                
                match_info = {
                    'number': i,
                    'match_id': match_id,
                    'kills': kills,
                    'assists': assists,
                    'deaths': deaths,
                    'elo_change': elo_change,
                    'result': result,
                    'lobby_id': lobby_id,
                    'status': status,
                    'match_status': match_status,  # Добавлен статус рассмотрения
                    'created_at': created_at,
                    'game_mode': game_mode,
                    'map': map_name,  # Теперь карта берется из базы данных
                    'league': league if league else 'default'
                }
                match_history.append(match_info)
            
            return match_history
            
        except Exception as e:
            logging.error(f"Ошибка получения истории матчей: {e}")
            return []
        finally:
            conn.close()

    def update_elo_after_match(self, winning_team, losing_team, match_id):
        """Обновляет ELO после матча с учетом новой системы"""
        results = []
        
        # Обновляем ELO для победителей
        for winner_id in winning_team:
            winner_profile = self.get_user_profile(winner_id)
            if winner_profile:
                elo_change = self.calculate_elo_change(winner_id, True, winner_profile['elo'])
                new_elo = winner_profile['elo'] + elo_change
                
                conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
                cursor = conn.cursor()
                
                cursor.execute('UPDATE players SET elo = ?, wins = wins + 1, matches_played = matches_played + 1 WHERE user_id = ?', 
                              (new_elo, winner_id))
                cursor.execute('UPDATE players SET calibration_matches = calibration_matches + 1 WHERE user_id = ? AND calibration_matches < 3', 
                              (winner_id,))
                
                cursor.execute('''
                    INSERT INTO elo_history (user_id, old_elo, new_elo, reason)
                    VALUES (?, ?, ?, ?)
                ''', (winner_id, winner_profile['elo'], new_elo, "match_win"))
                
                # Сохраняем информацию о матче для игрока
                cursor.execute('''
                    INSERT INTO player_matches (user_id, match_id, kills, assists, deaths, total_score, elo_change, result)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (winner_id, match_id, 0, 0, 0, 0, elo_change, 'win'))
                
                conn.commit()
                conn.close()
                
                calibration_info = " (калибровка)" if winner_profile['calibration_matches'] < 3 else ""
                
                results.append(f"🎯 {winner_profile['nickname']}: {winner_profile['elo']} → {new_elo} (+{elo_change}{calibration_info})")
        
        # Обновляем ELO для проигравших
        for loser_id in losing_team:
            loser_profile = self.get_user_profile(loser_id)
            if loser_profile:
                elo_change = self.calculate_elo_change(loser_id, False, loser_profile['elo'])
                new_elo = max(0, loser_profile['elo'] + elo_change)
                
                conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
                cursor = conn.cursor()
                
                cursor.execute('UPDATE players SET elo = ?, losses = losses + 1, matches_played = matches_played + 1 WHERE user_id = ?', 
                              (new_elo, loser_id))
                cursor.execute('UPDATE players SET calibration_matches = calibration_matches + 1 WHERE user_id = ? AND calibration_matches < 3', 
                              (loser_id,))
                
                cursor.execute('''
                    INSERT INTO elo_history (user_id, old_elo, new_elo, reason)
                    VALUES (?, ?, ?, ?)
                ''', (loser_id, loser_profile['elo'], new_elo, "match_loss"))
                
                # Сохраняем информацию о матче для игрока
                cursor.execute('''
                    INSERT INTO player_matches (user_id, match_id, kills, assists, deaths, total_score, elo_change, result)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (loser_id, match_id, 0, 0, 0, 0, elo_change, 'loss'))
                
                conn.commit()
                conn.close()
                
                calibration_info = " (калибровка)" if loser_profile['calibration_matches'] < 3 else ""
                results.append(f"🎯 {loser_profile['nickname']}: {loser_profile['elo']} → {new_elo} ({elo_change}{calibration_info})")
        
        return results

    def create_match_thread(self, match_id, team_ct, team_t, xoct_id, selected_map="Random", league='default'):
        """Создает тему для матча в группе с выбранной картой"""
        try:
            # Сохраняем карту в базу данных
            conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE matches SET map = ?, league = ? WHERE id = ?
            ''', (selected_map, league, match_id))
            
            conn.commit()
            conn.close()
            
            # Защита от дублирования веток
            thread_key = f"{match_id}_{selected_map}_{league}"
            if thread_key in self.last_match_threads:
                if time.time() - self.last_match_threads[thread_key]['timestamp'] < 30:  # 30 секунд защиты
                    logging.info(f"🛡️ Защита от дублирования ветки для матча {match_id}")
                    return self.last_match_threads[thread_key]['thread_id']
            
            league_prefix = "PRO " if league == 'pro' else ""
            thread_name = f"{league_prefix}Матч #{match_id} | {len(team_ct)}vs{len(team_t)}"
            
            result = bot.create_forum_topic(
                chat_id=self.match_group_id,
                name=thread_name
            )
            
            if result and hasattr(result, 'message_thread_id'):
                thread_id = result.message_thread_id
                
                success = self.send_match_info_to_thread(match_id, thread_id, team_ct, team_t, xoct_id, selected_map, league)
                
                if success:
                    # Сохраняем информацию о созданной ветке для защиты от дублирования
                    self.last_match_threads[thread_key] = {
                        'thread_id': thread_id,
                        'timestamp': time.time()
                    }
                    return thread_id
                else:
                    logging.error("❌ Не удалось отправить информацию в тему")
                    self.send_match_info_to_thread(match_id, None, team_ct, team_t, xoct_id, selected_map, league)
                    return None
            else:
                logging.error("❌ Не удалось создать тему форума")
                self.send_match_info_to_thread(match_id, None, team_ct, team_t, xoct_id, selected_map, league)
                return None
                
        except Exception as e:
            logging.error(f"❌ Ошибка создания темы матча: {e}")
            self.send_match_info_to_thread(match_id, None, team_ct, team_t, xoct_id, selected_map, league)
            return None

    def send_match_info_to_thread(self, match_id, thread_id, team_ct, team_t, xoct_id, selected_map="Random", league='default'):
        """Отправляет информацию о матче в тему с выбранной картой"""
        try:
            # Определяем режим игры
            if len(team_ct) == 2 and len(team_t) == 2:
                game_mode = "2×2"
            else:
                game_mode = "5×5"
            
            league_prefix = "🏆 PRO LEAGUE\n" if league == 'pro' else ""
            match_info = f"{league_prefix}🔑 Матч #{match_id} ({game_mode})\n"
            match_info += f"🗺️ Карта: {selected_map}\n\n"
            
            match_info += "🔵 CT\n"
            for player_id in team_ct:
                profile = self.get_user_profile(player_id)
                if profile:
                    match_info += f"{profile['nickname']} ({profile['game_id']}) - TG_ID: {player_id}\n"
            
            match_info += "\n🟠 T\n"
            for player_id in team_t:
                profile = self.get_user_profile(player_id)
                if profile:
                    match_info += f"{profile['nickname']} ({profile['game_id']}) - TG_ID: {player_id}\n"
            
            match_info += f"\n👤 XOCT — {xoct_id}\n\n"
            match_info += "📤 Все игроки должны зайти в игру в течении 4-х минут."
            
            # Для админов в группе показываем дополнительную информацию
            admin_match_info = match_info + f"\n\n👥 Информация для администраторов:\n"
            admin_match_info += "🔵 CT:\n"
            for player_id in team_ct:
                profile = self.get_user_profile(player_id)
                if profile:
                    admin_match_info += f"{profile['nickname']} (TG_ID: {player_id})\n"
            
            admin_match_info += "\n🟠 T:\n"
            for player_id in team_t:
                profile = self.get_user_profile(player_id)
                if profile:
                    admin_match_info += f"{profile['nickname']} (TG_ID: {player_id})\n"
            
            if thread_id:
                # Отправляем основное сообщение в тему
                bot.send_message(
                    chat_id=self.match_group_id,
                    message_thread_id=thread_id,
                    text=match_info,
                    parse_mode='Markdown'
                )
                
                # Отправляем сообщение о ожидании скриншотов для админов
                bot.send_message(
                    chat_id=self.match_group_id,
                    message_thread_id=thread_id,
                    text=f"⏳ Ожидаем скриншоты с результатами матча #{match_id}......"
                )
            else:
                # Если нет thread_id, отправляем в основную группу
                bot.send_message(
                    chat_id=self.match_group_id,
                    text=admin_match_info,
                    parse_mode='Markdown'
                )
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Ошибка отправки информации о матче: {e}")
            return False

    def create_ticket_thread(self, user_id, match_id, reported_nickname, complaint_text):
        """Создает ветку для тикета в группе"""
        try:
            user_profile = self.get_user_profile(user_id)
            user_nickname = user_profile['nickname'] if user_profile else "Неизвестный"
            
            thread_name = f"Жалоба #{match_id} | {user_nickname}"
            
            result = bot.create_forum_topic(
                chat_id=self.ticket_group_id,
                name=thread_name
            )
            
            if result and hasattr(result, 'message_thread_id'):
                thread_id = result.message_thread_id
                
                ticket_text = f"🎫 НОВАЯ ЖАЛОБА #{match_id}\n\n"
                ticket_text += f"👤 Подал жалобу: {user_nickname} (ID: {user_id})\n"
                ticket_text += f"🔍 Match ID: {match_id}\n"
                ticket_text += f"⚠️ На кого жалоба: {reported_nickname}\n\n"
                ticket_text += f"📝 Текст жалобы:\n{complaint_text}\n\n"
                ticket_text += f"💬 Ответить: /emsg {user_id} ваш_ответ"
                
                bot.send_message(
                    chat_id=self.ticket_group_id,
                    message_thread_id=thread_id,
                    text=ticket_text
                )
                
                # Сохраняем в базу данных
                conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO tickets (user_id, user_nickname, message, status)
                    VALUES (?, ?, ?, 'open')
                ''', (user_id, user_nickname, f"Match ID: {match_id}\nНа кого: {reported_nickname}\nЖалоба: {complaint_text}"))
                
                conn.commit()
                conn.close()
                
                return True, "✅ Ваша жалоба была подана на рассмотрение."
            else:
                return False, "❌ Ошибка при создании тикета. Попробуйте позже."
                
        except Exception as e:
            logging.error(f"❌ Ошибка создания тикета: {e}")
            return False, f"❌ Ошибка при создании тикета: {str(e)}"

    def send_ticket_response(self, user_id, admin_response):
        """Отправляет ответ на тикет"""
        try:
            conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE tickets 
                SET status = 'closed', admin_response = ?
                WHERE user_id = ? AND status = 'open'
            ''', (admin_response, user_id))
            
            conn.commit()
            conn.close()
            
            response_text = f"💬 Ответ администратора:\n\n{admin_response}"
            bot.send_message(user_id, response_text)
            
            return True, "✅ Ответ отправлен пользователю"
            
        except Exception as e:
            return False, f"❌ Ошибка при отправке ответа: {str(e)}"

    def _generate_lobby_text(self, lobby_id, is_pro=False):
        """Генерирует текст для отображения лобби с информацией об устройствах и ELO"""
        if is_pro:
            lobby = self.pro_lobbies[lobby_id]
        else:
            lobby = self.lobbies[lobby_id]
        
        if is_pro:
            lobby_names = {
                'pro_lobby1': 'PRO LOBBY 1 2×2',
                'pro_lobby2': 'PRO LOBBY 2 2×2', 
                'pro_lobby3': 'PRO LOBBY 3 5×5',
                'pro_lobby4': 'PRO LOBBY 4 5×5'
            }
        else:
            lobby_names = {
                'lobby1': 'LOBBY 1 5×5',
                'lobby2': 'LOBBY 2 5×5', 
                'lobby3': 'LOBBY 3 5×5',
                'lobby4': 'LOBBY 4 5×5',
                'lobby5': 'LOBBY 5 5×5',
                'lobby6': 'LOBBY 6 2×2',
                'lobby7': 'LOBBY 7 2×2'
            }
        
        text = f"🎮 {lobby_names[lobby_id]}\n\n"
        
        if lobby['players']:
            text += "📋 Список игроков:\n"
            for i, player_id in enumerate(lobby['players'], 1):
                profile = self.get_user_profile(player_id)
                if profile:
                    device_emoji = "📱" if profile['device'] == 'Android' else "💻"
                    level_emoji = profile.get('level_emoji', '1️⃣')
                    text += f"{i}. {profile['nickname']} {level_emoji} {device_emoji} (ID: {player_id}) {profile['elo']} ELO\n"
        else:
            text += "📋 Список игроков пуст\n"
        
        text += f"\n👥 Игроков: {len(lobby['players'])}/{lobby['max_players']}"
        
        return text

    def _update_lobby_message(self, lobby_id, is_pro=False):
        """Обновляет сообщение лобби для всех игроков с задержками"""
        if is_pro:
            lobby = self.pro_lobbies[lobby_id]
        else:
            lobby = self.lobbies[lobby_id]
            
        lobby_text = self._generate_lobby_text(lobby_id, is_pro)
        
        # Если идет подтверждение или бан-пик, убираем кнопку выхода
        if lobby['status'] in ['waiting_confirmation', 'veto']:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton('⏳ Идет процесс матча...', callback_data='no_action'))
        else:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton('🚪 Выйти из лобби', callback_data='leave_lobby'))
        
        # Обновляем сообщение для каждого игрока в лобби
        for i, player_id in enumerate(lobby['players']):
            try:
                if player_id in lobby['lobby_messages']:
                    if i > 0:
                        time.sleep(0.1)  # Небольшая задержка между обновлениями
                    
                    success = safe_edit_message(
                        chat_id=player_id,
                        message_id=lobby['lobby_messages'][player_id],
                        text=lobby_text,
                        reply_markup=markup
                    )
                    
                    if not success:
                        # Если не удалось обновить, отправляем новое сообщение
                        try:
                            message = bot.send_message(player_id, lobby_text, reply_markup=markup)
                            lobby['lobby_messages'][player_id] = message.message_id
                        except Exception as e:
                            logging.error(f"Не удалось отправить новое сообщение игроку {player_id}: {e}")
            except Exception as e:
                logging.error(f"Ошибка обновления сообщения лобби игроку {player_id}: {e}")

    def _send_lobby_message(self, user_id, lobby_id, is_pro=False):
        """Отправляет сообщение лобби новому игроку"""
        if is_pro:
            lobby = self.pro_lobbies[lobby_id]
        else:
            lobby = self.lobbies[lobby_id]
            
        lobby_text = self._generate_lobby_text(lobby_id, is_pro)
        
        # Если идет подтверждение или бан-пик, убираем кнопку выхода
        if lobby['status'] in ['waiting_confirmation', 'veto']:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton('⏳ Идет процесс матча...', callback_data='no_action'))
        else:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton('🚪 Выйти из лобби', callback_data='leave_lobby'))
        
        try:
            message = bot.send_message(user_id, lobby_text, reply_markup=markup)
            
            # Сохраняем ID сообщения для этого игрока
            lobby['lobby_messages'][user_id] = message.message_id
            
        except Exception as e:
            logging.error(f"Ошибка отправки сообщения лобби игроку {user_id}: {e}")

    def _remove_player_lobby_message(self, user_id, lobby_id, is_pro=False):
        """Удаляет сообщение лобби для игрока, который вышел"""
        if is_pro:
            lobby = self.pro_lobbies[lobby_id]
        else:
            lobby = self.lobbies[lobby_id]
        
        if user_id in lobby['lobby_messages']:
            try:
                bot.delete_message(
                    chat_id=user_id,
                    message_id=lobby['lobby_messages'][user_id]
                )
            except Exception as e:
                logging.debug(f"Не удалось удалить сообщение лобби игроку {user_id}: {e}")
            
            del lobby['lobby_messages'][user_id]

    def join_lobby(self, user_id, lobby_id, is_pro=False):
        """Присоединяет игрока к лобби"""
        try:
            # Проверяем, не находится ли уже игрок в лобби
            if user_id in self.user_lobbies:
                return False, "❌ Вы уже находитесь в активном лобби!"
            
            # Проверяем, не забанен ли игрок
            is_banned, ban_until = self.is_user_banned(user_id)
            if is_banned:
                if ban_until:
                    return False, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}"
                else:
                    return False, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан"
            
            # Проверяем, не замучен ли игрок
            is_muted, mute_until = self.is_user_muted(user_id)
            if is_muted:
                if mute_until:
                    return False, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}"
                else:
                    return False, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут"
            
            # Получаем профиль игрока
            profile = self.get_user_profile(user_id)
            if not profile:
                return False, "❌ Вы не зарегистрированы! Используйте /start"
            
            # Получаем лобби
            if is_pro:
                lobby = self.pro_lobbies.get(lobby_id)
            else:
                lobby = self.lobbies.get(lobby_id)
            
            if not lobby:
                return False, "❌ Лобби не найдено!"
            
            # Проверяем доступ к Pro League
            if is_pro and not self.has_pro_league_access(user_id):
                return False, "❌ У вас нет доступа к Pro League. Обратитесь к @blesswayknow для получения доступа."
            
            # Проверяем совместимость устройства
            user_device = self.get_user_device(user_id)
            if user_device not in lobby['allowed_devices']:
                if is_pro:
                    device_restriction = {
                        'pro_lobby1': '📱 Только телефоны (Android)',
                        'pro_lobby2': '💻 Только компьютеры',
                        'pro_lobby3': '📱 Только телефоны (Android)',
                        'pro_lobby4': '💻 Только компьютеры'
                    }
                else:
                    device_restriction = {
                        'lobby1': '📱 Только телефоны (Android)',
                        'lobby2': '📱 Только телефоны (Android)',
                        'lobby3': '📱💻 Телефоны (Android) + ПК',
                        'lobby4': '📱💻 Телефоны (Android) + ПК',
                        'lobby5': '💻 Только ПК',
                        'lobby6': '📱💻 Телефоны (Android) + ПК',
                        'lobby7': '📱 Только телефоны (Android)'
                    }
                return False, f"❌ Вы не можете присоединиться к этому лобби!\n{device_restriction[lobby_id]}"
            
            # Проверяем, не заполнено ли лобби
            if len(lobby['players']) >= lobby['max_players']:
                return False, "❌ Лобби уже заполнено!"
            
            # Если игрок в пати, присоединяем всю пати
            if user_id in self.parties:
                return self.join_lobby_with_party(user_id, lobby_id, is_pro)
            
            # Добавляем игрока в лобби
            lobby['players'].append(user_id)
            self.user_lobbies[user_id] = lobby_id
            
            # Отправляем сообщение лобби игроку
            self._send_lobby_message(user_id, lobby_id, is_pro)
            
            # Обновляем сообщение лобби для всех
            self._update_lobby_message(lobby_id, is_pro)
            
            # Если лобби заполнено, запускаем подтверждение
            if len(lobby['players']) == lobby['max_players']:
                return self.request_confirmation(lobby_id, is_pro)
            
            return True, f"✅ Вы присоединились к лобби!\nОжидаем игроков: {len(lobby['players'])}/{lobby['max_players']}"
            
        except Exception as e:
            logging.error(f"❌ Ошибка при присоединении к лобби: {e}")
            return False, f"❌ Ошибка при присоединении к лобби: {str(e)}"

    def create_party(self, leader_id):
        """Создает новую пати"""
        if leader_id in self.parties:
            return False, "❌ Вы уже состоите в пати!"
        
        max_party_size = 2
        
        self.parties[leader_id] = {
            'members': [leader_id],
            'max_size': max_party_size,
            'leader': leader_id
        }
        return True, f"✅ Пати создана! Теперь вы можете пригласить друга."

    def invite_to_party(self, leader_id, friend_id):
        """Приглашает друга в пати"""
        if leader_id not in self.parties:
            return False, "❌ У вас нет активной пати!"
        
        party = self.parties[leader_id]
        
        if len(party['members']) >= party['max_size']:
            return False, f"❌ В вашей пати уже максимальное количество игроков ({party['max_size']})!"
        
        friend_profile = self.get_user_profile(friend_id)
        if not friend_profile:
            return False, "⚠️ Такого ID не существует, или пользователь не зарегистрирован."
        
        if friend_id == leader_id:
            return False, "❌ Нельзя пригласить самого себя!"
        
        if friend_id in self.parties:
            return False, "❌ Этот игрок уже состоит в другой пати!"
        
        self.party_invites[friend_id] = leader_id
        
        leader_profile = self.get_user_profile(leader_id)
        leader_name = leader_profile['nickname'] if leader_profile else "Неизвестный"
        
        try:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton('✅ Принять', callback_data=f'accept_party_{leader_id}'),
                telebot.types.InlineKeyboardButton('❌ Отказать', callback_data=f'decline_party_{leader_id}')
            )
            
            invite_text = f"🎮 Вас пригласил в пати:\n"
            invite_text += f"👤 {leader_name} (ID: {leader_id})\n\n"
            invite_text += f"Хотите присоединиться к команде?"
            
            bot.send_message(friend_id, invite_text, reply_markup=markup)
            return True, "✅ Приглашение вашему товарищу было отправлено!"
        except Exception as e:
            return False, "❌ Не удалось отправить приглашение. Проверьте ID друга."

    def accept_party_invite(self, user_id, leader_id):
        """Принимает приглашение в пати"""
        if user_id not in self.party_invites or self.party_invites[user_id] != leader_id:
            return False, "❌ Приглашение не найдено или устарело!"
        
        if user_id in self.parties:
            return False, "❌ Вы уже состоите в пати!"
        
        party = self.parties[leader_id]
        
        if len(party['members']) >= party['max_size']:
            return False, "❌ В пати уже максимальное количество игроков!"
        
        party['members'].append(user_id)
        self.parties[user_id] = party
        
        del self.party_invites[user_id]
        
        user_profile = self.get_user_profile(user_id)
        user_name = user_profile['nickname'] if user_profile else "Неизвестный"
        
        try:
            bot.send_message(leader_id, f"✅ {user_name} принял ваше приглашение в пати!")
        except:
            pass
        
        return True, "✅ Вы присоединились к пати!"

    def decline_party_invite(self, user_id, leader_id):
        """Отклоняет приглашение в пати"""
        if user_id in self.party_invites and self.party_invites[user_id] == leader_id:
            del self.party_invites[user_id]
            
            user_profile = self.get_user_profile(user_id)
            user_name = user_profile['nickname'] if user_profile else "Неизвестный"
            
            try:
                bot.send_message(leader_id, f"❌ {user_name} отклонил ваше приглашение в пати.")
            except:
                pass
            
            return True, "❌ Вы отклонили приглашение в пати."
        return False, "❌ Приглашение не найдено."

    def leave_party(self, user_id):
        """Покидает пати"""
        if user_id not in self.parties:
            return False, "❌ Вы не состоите в пати!"
        
        party = self.parties[user_id]
        
        user_profile = self.get_user_profile(user_id)
        user_name = user_profile['nickname'] if user_profile else "Неизвестный"
        
        # Уведомляем других участников
        for member_id in party['members']:
            if member_id != user_id:
                try:
                    bot.send_message(member_id, f"🔴 {user_name} покинул пати.")
                except:
                    pass
        
        # Удаляем пользователя из пати
        party['members'].remove(user_id)
        
        # Если пати пустая, удаляем ее полностью
        if len(party['members']) == 0:
            for member_id in list(self.parties.keys()):
                if self.parties[member_id] == party:
                    del self.parties[member_id]
        else:
            # Если лидер вышел, назначаем нового лидера
            if user_id == party['leader']:
                party['leader'] = party['members'][0]
            del self.parties[user_id]
        
        return True, "✅ Вы покинули пати!"

    def get_party_info(self, user_id):
        """Получает информацию о пати"""
        if user_id not in self.parties:
            return None
        
        party = self.parties[user_id]
        
        members_info = []
        for member_id in party['members']:
            profile = self.get_user_profile(member_id)
            if profile:
                member_type = "👑" if member_id == party['leader'] else "👤"
                device_emoji = "📱" if profile['device'] == 'Android' else "💻"
                level_emoji = profile.get('level_emoji', '1️⃣')
                members_info.append({
                    'id': member_id,
                    'nickname': profile['nickname'],
                    'type': member_type,
                    'device': profile['device'],
                    'device_emoji': device_emoji,
                    'level_emoji': level_emoji
                })
        
        return {
            'members': members_info,
            'max_size': party['max_size'],
            'leader_id': party['leader']
        }

    def join_lobby_with_party(self, user_id, lobby_id, is_pro=False):
        """Присоединяет пати к лобби с проверкой устройств всех участников"""
        if user_id not in self.parties:
            return False, "❌ Вы не в пати!"
        
        party = self.parties[user_id]
        members = party['members']
        
        # Проверяем, что все участники пати имеют подходящие устройства для лобби
        for member_id in members:
            is_banned, ban_until = self.is_user_banned(member_id)
            if is_banned:
                return False, f"❌ Участник пати забанен!"
            
            is_muted, mute_until = self.is_user_muted(member_id)
            if is_muted:
                return False, f"❌ Участник пати замучен!"
            
            if member_id in self.user_lobbies:
                return False, f"❌ Участник пати уже находится в лобби!"
            
            # Проверяем совместимость устройства с лобби
            user_device = self.get_user_device(member_id)
            if is_pro:
                lobby = self.pro_lobbies[lobby_id]
            else:
                lobby = self.lobbies[lobby_id]
            
            if user_device not in lobby['allowed_devices']:
                if is_pro:
                    device_restriction = {
                        'pro_lobby1': '📱 Только телефоны (Android)',
                        'pro_lobby2': '💻 Только компьютеры',
                        'pro_lobby3': '📱 Только телефоны (Android)',
                        'pro_lobby4': '💻 Только компьютеры'
                    }
                else:
                    device_restriction = {
                        'lobby1': '📱 Только телефоны (Android)',
                        'lobby2': '📱 Только телефоны (Android)',
                        'lobby3': '📱💻 Телефоны (Android) + ПК',
                        'lobby4': '📱💻 Телефоны (Android) + ПК',
                        'lobby5': '💻 Только ПК',
                        'lobby6': '📱💻 Телефоны (Android) + ПК',
                        'lobby7': '📱 Только телефоны (Android)'
                    }
                profile = self.get_user_profile(member_id)
                nickname = profile['nickname'] if profile else "Неизвестный"
                return False, f"❌ Участник {nickname} не может присоединиться к этому лобби!\n{device_restriction[lobby_id]}"
        
        # Проверяем доступ к Pro League для всех участников пати
        if is_pro:
            for member_id in members:
                if not self.has_pro_league_access(member_id):
                    profile = self.get_user_profile(member_id)
                    nickname = profile['nickname'] if profile else "Неизвестный"
                    return False, f"ℹ️ У вашего тимейта {nickname} нет доступа к Pro League."
        
        if is_pro:
            lobby = self.pro_lobbies[lobby_id]
        else:
            lobby = self.lobbies[lobby_id]
        
        if len(lobby['players']) + len(members) > lobby['max_players']:
            return False, f"❌ В лобби недостаточно места для вашей пати!"
        
        # Для пати из 2 игроков разрешаем только лобби 3, 4, 5, 6, 7
        if not is_pro and len(members) > 2 and lobby_id not in ['lobby3', 'lobby4', 'lobby5', 'lobby6', 'lobby7']:
            return False, "❌ Пати из 2 игроков может играть только в лобби 3, 4, 5, 6, 7!"
        
        for member_id in members:
            if member_id not in lobby['players']:
                lobby['players'].append(member_id)
                self.user_lobbies[member_id] = lobby_id
        
        for member_id in members:
            self._send_lobby_message(member_id, lobby_id, is_pro)
        
        self._update_lobby_message(lobby_id, is_pro)
        
        if len(lobby['players']) == lobby['max_players']:
            return self.request_confirmation(lobby_id, is_pro)
        
        return True, f"✅ Ваша пати присоединилась к лобби {lobby_id}\nОжидаем игроков: {len(lobby['players'])}/{lobby['max_players']}"

    def update_user_nickname(self, user_id, new_nickname):
        """Обновляет никнейм пользователя"""
        # Проверка никнейма - минимум 2 символа, без пробелов
        if len(new_nickname.strip()) < 2:
            return False, "❌ Никнейм должен содержать минимум 2 символа!"
        
        # Проверка на пробелы в никнейме
        if ' ' in new_nickname.strip():
            return False, "❌ Никнейм не должен содержать пробелов! Используйте одно слово."
        
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            # Проверяем, не занят ли никнейм другим пользователем
            cursor.execute('SELECT user_id FROM players WHERE nickname = ? AND user_id != ?', (new_nickname, user_id))
            if cursor.fetchone():
                return False, "❌ Этот никнейм уже занят! Попробуйте другой."
            
            cursor.execute('UPDATE players SET nickname = ? WHERE user_id = ?', (new_nickname, user_id))
            conn.commit()
            return True, "✅ Никнейм успешно изменен!"
        except sqlite3.IntegrityError:
            return False, "❌ Этот никнейм уже занят! Попробуйте другой."
        except Exception as e:
            return False, f"❌ Ошибка при изменении никнейма: {str(e)}"
        finally:
            conn.close()

    def is_user_banned(self, user_id):
        """Проверяет, забанен ли пользователь"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('SELECT is_banned, ban_until FROM players WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            if result[1]:
                ban_until = datetime.fromisoformat(result[1])
                if get_moscow_time() < ban_until:
                    return True, ban_until
                else:
                    self.unban_user(user_id)
                    return False, None
            else:
                return True, None
        return False, None

    def is_user_muted(self, user_id):
        """Проверяет, заглушен ли пользователь"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('SELECT is_muted, mute_until FROM players WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            if result[1]:
                mute_until = datetime.fromisoformat(result[1])
                if get_moscow_time() < mute_until:
                    return True, mute_until
                else:
                    self.unmute_user(user_id)
                    return False, None
            else:
                return True, None
        return False, None

    def ban_user(self, user_id, reason, duration_days=None):
        """Банит пользователя"""
        # Проверяем, не забанен ли уже пользователь
        is_banned, _ = self.is_user_banned(user_id)
        if is_banned:
            return False, "✅ Данный пользователь уже забанен!"
        
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        ban_until = None
        if duration_days:
            ban_until = get_moscow_time() + timedelta(days=duration_days)
        
        cursor.execute('''
            UPDATE players 
            SET is_banned = TRUE, ban_reason = ?, ban_until = ?
            WHERE user_id = ?
        ''', (reason, ban_until.isoformat() if ban_until else None, user_id))
        
        conn.commit()
        conn.close()
        
        lobby_id = self.find_user_lobby(user_id)
        if lobby_id:
            self.leave_lobby(user_id)
        
        return True, f"✅ Пользователь забанен{' на ' + str(duration_days) + ' дней' if duration_days else ' перманентно'}!"

    def unban_user(self, user_id):
        """Разбанивает пользователя"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE players 
            SET is_banned = FALSE, ban_reason = NULL, ban_until = NULL
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        return True

    def mute_user(self, user_id, reason, duration_minutes=None):
        """Мутит пользователя"""
        # Проверяем, не замучен ли уже пользователь
        is_muted, _ = self.is_user_muted(user_id)
        if is_muted:
            return False, "✅ Данный пользователь уже замьючен!"
        
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        mute_until = None
        if duration_minutes:
            mute_until = get_moscow_time() + timedelta(minutes=duration_minutes)
        
        cursor.execute('''
            UPDATE players 
            SET is_muted = TRUE, mute_reason = ?, mute_until = ?
            WHERE user_id = ?
        ''', (reason, mute_until.isoformat() if mute_until else None, user_id))
        
        conn.commit()
        conn.close()
        
        lobby_id = self.find_user_lobby(user_id)
        if lobby_id:
            self.leave_lobby(user_id)
        
        return True, f"✅ Пользователь замьючен{' на ' + str(duration_minutes) + ' минут' if duration_minutes else ' перманентно'}!"

    def unmute_user(self, user_id):
        """Размучивает пользователя"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE players 
            SET is_muted = FALSE, mute_reason = NULL, mute_until = NULL
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        return True

    def add_warning(self, user_id):
        """Добавляет предупреждение пользователю"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT warnings FROM players WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if result:
                current_warnings = result[0] + 1
                cursor.execute('UPDATE players SET warnings = ? WHERE user_id = ?', (current_warnings, user_id))
                conn.commit()
                
                if current_warnings >= 3:
                    self.ban_user(user_id, "3 предупреждения", 1)  # Бан на 1 день
                    conn.close()
                    return current_warnings, f"🚨 Вы получили 3-е предупреждение! Вы забанены на 1 день."
                elif current_warnings == 2:
                    self.mute_user(user_id, "2 предупреждения", 20)  # Мут на 20 минут
                    conn.close()
                    return current_warnings, f"⚠️ Вы получили 2-е предупреждение! Вы замьючены на 20 минут."
                elif current_warnings == 1:
                    self.mute_user(user_id, "1 предупреждение", 5)  # Мут на 5 минут
                    conn.close()
                    return current_warnings, f"⚠️ Вы получили 1-е предупреждение! Вы замьючены на 5 минут."
                else:
                    conn.close()
                    return current_warnings, f"⚠️ Предупреждение {current_warnings}/3."
            else:
                cursor.execute('UPDATE players SET warnings = 1 WHERE user_id = ?', (user_id,))
                conn.commit()
                self.mute_user(user_id, "1 предупреждение", 5)  # Мут на 5 минут
                conn.close()
                return 1, f"⚠️ Предупреждение 1/3. Вы замьючены на 5 минут."
                
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE players ADD COLUMN warnings INTEGER DEFAULT 0")
            cursor.execute('UPDATE players SET warnings = 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            self.mute_user(user_id, "1 предупреждение", 5)  # Мут на 5 минут
            conn.close()
            return 1, f"⚠️ Предупреждение 1/3. Вы замьючены на 5 минут."

    def add_confirmation_warning(self, user_id):
        """Добавляет предупреждение за неподтверждение матча"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT confirmation_warnings FROM players WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if result:
                current_warnings = result[0] + 1
                
                if current_warnings >= 3:
                    # Третье предупреждение - мут на 30 минут
                    cursor.execute('UPDATE players SET confirmation_warnings = ? WHERE user_id = ?', (current_warnings, user_id))
                    conn.commit()
                    conn.close()
                    
                    self.mute_user(user_id, "3 предупреждения за неподтверждение", 30)
                    return current_warnings, f"⚠️ Вы получили наказание в размере 30m. За непринятие игры, просим вас подождать как закончится мут."
                else:
                    # Первое и второе предупреждение - только текст
                    cursor.execute('UPDATE players SET confirmation_warnings = ? WHERE user_id = ?', (current_warnings, user_id))
                    conn.commit()
                    conn.close()
                    
                    return current_warnings, f"⚠️ ({current_warnings}/3) Вы получили предупреждение! За то что не приняли — игру."
            else:
                cursor.execute('UPDATE players SET confirmation_warnings = 1 WHERE user_id = ?', (user_id,))
                conn.commit()
                conn.close()
                return 1, f"⚠️ (1/3) Вы получили предупреждение! За то что не приняли — игру."
                
        except Exception as e:
            logging.error(f"Ошибка добавления предупреждения за неподтверждение: {e}")
            conn.close()
            return 0, f"❌ Ошибка: {str(e)}"

    def add_warning_manual(self, user_id, reason):
        """Добавляет предупреждение пользователю вручную (админская команда)"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT warnings FROM players WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if result:
                current_warnings = result[0] + 1
                cursor.execute('UPDATE players SET warnings = ? WHERE user_id = ?', (current_warnings, user_id))
                conn.commit()
                
                profile = self.get_user_profile(user_id)
                nickname = profile['nickname'] if profile else "Неизвестный"
                
                if current_warnings >= 3:
                    self.ban_user(user_id, f"3 предупреждения: {reason}", 1)  # Бан на 1 день
                    conn.close()
                    return current_warnings, f"✅ Пользователь {nickname} получил 3-е предупреждение и забанен на 1 день!"
                elif current_warnings == 2:
                    self.mute_user(user_id, f"2 предупреждения: {reason}", 20)  # Мут на 20 минут
                    conn.close()
                    return current_warnings, f"✅ Пользователь {nickname} получил 2-е предупреждение и замьючен на 20 минут!"
                elif current_warnings == 1:
                    self.mute_user(user_id, f"1 предупреждение: {reason}", 5)  # Мут на 5 минут
                    conn.close()
                    return current_warnings, f"✅ Пользователь {nickname} получил 1-е предупреждение и замьючен на 5 минут!"
                else:
                    conn.close()
                    return current_warnings, f"✅ Пользователь {nickname} получил предупреждение {current_warnings}/3."
            else:
                cursor.execute('UPDATE players SET warnings = 1 WHERE user_id = ?', (user_id,))
                conn.commit()
                self.mute_user(user_id, f"1 предупреждение: {reason}", 5)  # Мут на 5 минут
                conn.close()
                return 1, f"✅ Пользователь {nickname} получил 1-е предупреждение и замьючен на 5 минут!"
                
        except Exception as e:
            return 0, f"❌ Ошибка при добавлении предупреждения: {str(e)}"

    def remove_warning(self, user_id):
        """Убирает одно предупреждение у пользователя"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT warnings FROM players WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if result and result[0] > 0:
                new_warnings = result[0] - 1
                cursor.execute('UPDATE players SET warnings = ? WHERE user_id = ?', (new_warnings, user_id))
                conn.commit()
                
                profile = self.get_user_profile(user_id)
                nickname = profile['nickname'] if profile else "Неизвестный"
                
                conn.close()
                return new_warnings, f"✅ Снято одно предупреждение у пользователя {nickname}. Теперь предупреждений: {new_warnings}/3"
            else:
                conn.close()
                return 0, "❌ У пользователя нет предупреждений"
                
        except Exception as e:
            return 0, f"❌ Ошибка при снятии предупреждения: {str(e)}"

    def reset_warnings(self, user_id):
        """Обнуляет все предупреждения пользователя"""
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            cursor.execute('UPDATE players SET warnings = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
            
            profile = self.get_user_profile(user_id)
            nickname = profile['nickname'] if profile else "Неизвестный"
            
            conn.close()
            return True, f"✅ Все предупреждения пользователя {nickname} обнулены!"
                
        except Exception as e:
            return False, f"❌ Ошибка при обнулении предупреждений: {str(e)}"

    def manual_register_stats(self, user_id, kills, assists, deaths, total_score, result_type, match_id=None, thread_id=None):
        """Ручная регистрация статистики с указанием победы/поражения по Telegram ID"""
        time.sleep(0.1)
        
        # ИСПРАВЛЕНА ЛОГИКА: проверяем, был ли игрок откатан в этой ветке
        if thread_id and thread_id in self.rolled_back_players_in_thread:
            if user_id in self.rolled_back_players_in_thread[thread_id]:
                # Если игрок был откатан, удаляем его из списка откатанных и разрешаем регистрацию
                self.rolled_back_players_in_thread[thread_id].remove(user_id)
        
        # Проверяем, был ли уже зарегистрирован игрок в этой ветке (если не был откатан)
        if thread_id and thread_id in self.registered_players_in_thread:
            if user_id in self.registered_players_in_thread[thread_id]:
                return f"⚠️ Вы уже зарегистрировали данного игрока.\n👮‍♀️ Откатить статистику /backupd"
        
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT user_id, elo, calibration_matches, nickname FROM players WHERE user_id = ?', (user_id,))
            player_info = cursor.fetchone()
            
            if player_info:
                user_id, old_elo, calib_matches, nickname = player_info
                
                cursor.execute('''
                    UPDATE players 
                    SET kills = kills + ?, assists = assists + ?, 
                        deaths = deaths + ?, total_score = total_score + ?,
                        matches_played = matches_played + 1
                    WHERE user_id = ?
                ''', (kills, assists, deaths, total_score, user_id))
                
                # Используем новую систему ELO
                is_winner = (result_type == 'win')
                elo_change = self.calculate_elo_change(user_id, is_winner, old_elo)
                new_elo = max(0, old_elo + elo_change)
                
                if result_type == 'win':
                    cursor.execute('UPDATE players SET wins = wins + 1 WHERE user_id = ?', (user_id,))
                    reason = "manual_win"
                else:
                    cursor.execute('UPDATE players SET losses = losses + 1 WHERE user_id = ?', (user_id,))
                    reason = "manual_loss"
                
                # Обновляем калибровочные матчи если нужно
                if calib_matches < 3:
                    cursor.execute('UPDATE players SET calibration_matches = calibration_matches + 1 WHERE user_id = ?', (user_id,))
                
                cursor.execute('UPDATE players SET elo = ? WHERE user_id = ?', (new_elo, user_id))
                
                cursor.execute('''
                    INSERT INTO elo_history (user_id, old_elo, new_elo, reason)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, old_elo, new_elo, reason))
                
                # Сохраняем информацию о матче для игрока
                cursor.execute('''
                    INSERT INTO player_matches (user_id, match_id, kills, assists, deaths, total_score, elo_change, result)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, match_id, kills, assists, deaths, total_score, elo_change, result_type))
                
                conn.commit()
                
                # Добавляем игрока в список зарегистрированных в этой ветке
                if thread_id:
                    if thread_id not in self.registered_players_in_thread:
                        self.registered_players_in_thread[thread_id] = set()
                    self.registered_players_in_thread[thread_id].add(user_id)
                
                # Отправляем сообщение игроку о зарегистрированном матче
                try:
                    match_number = f"#{match_id}" if match_id else "#неизвестен"
                    match_message = f"✅ Матч ({match_number}) был зарегистрирован!\n\n"
                    match_message += f"🔄 Посмотреть свою статистку можно в меню:\n"
                    match_message += f"📊 Профиль — Статистика.\n\n"
                    match_message += f"⚠️ Если ваши результаты некорректны — обратитесь к @blesswayknow"
                    
                    bot.send_message(user_id, match_message)
                except Exception as e:
                    logging.error(f"Не удалось отправить сообщение игроку {user_id}: {e}")
                
                calib_info = " (калибровка)" if calib_matches < 3 else ""
                return f"✅ {nickname}: +{kills}K {assists}A {deaths}D | ELO: {old_elo} → {new_elo} (+{elo_change}{calib_info})"
            else:
                return f"❌ Игрок с ID {user_id} не найден в базе данных"
                
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"
        finally:
            conn.close()

    def manual_register_elo(self, user_id, elo_value, thread_id=None):
        """Ручная установка ELO по Telegram ID (админская команда)"""
        time.sleep(0.1)
        
        # ИСПРАВЛЕНА ЛОГИКА: проверяем, был ли игрок откатан в этой ветке
        if thread_id and thread_id in self.rolled_back_players_in_thread:
            if user_id in self.rolled_back_players_in_thread[thread_id]:
                # Если игрок был откатан, удаляем его из списка откатанных и разрешаем регистрацию
                self.rolled_back_players_in_thread[thread_id].remove(user_id)
        
        # Проверяем, был ли уже зарегистрирован игрок в этой ветке (если не был откатан)
        if thread_id and thread_id in self.registered_players_in_thread:
            if user_id in self.registered_players_in_thread[thread_id]:
                return f"⚠️ Вы уже зарегистрировали данного игрока.\n👮‍♀️ Откатить статистику /backupd"
        
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT user_id, elo, nickname FROM players WHERE user_id = ?', (user_id,))
            player_info = cursor.fetchone()
            
            if player_info:
                user_id, old_elo, nickname = player_info
                
                cursor.execute('UPDATE players SET elo = ? WHERE user_id = ?', (elo_value, user_id))
                
                cursor.execute('''
                    INSERT INTO elo_history (user_id, old_elo, new_elo, reason)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, old_elo, elo_value, "manual_set"))
                
                conn.commit()
                
                # Добавляем игрока в список зарегистрированных в этой ветке
                if thread_id:
                    if thread_id not in self.registered_players_in_thread:
                        self.registered_players_in_thread[thread_id] = set()
                    self.registered_players_in_thread[thread_id].add(user_id)
                
                return f"🛠️ ELO игрока {nickname} установлен на {elo_value} (было: {old_elo})"
            else:
                return f"❌ Игрок с ID {user_id} не найден в базе данных"
                
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"
        finally:
            conn.close()

    def cancel_match(self, match_id, user_id):
        """Отменяет матч (только для админов)"""
        try:
            # Проверяем существование матча
            conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, lobby_id, team_ct, team_t FROM matches WHERE id = ?', (match_id,))
            match_info = cursor.fetchone()
            
            if not match_info:
                return False, "❌ Матч с таким номером не найден."
            
            match_id, lobby_id, team_ct_str, team_t_str = match_info
            
            # Получаем всех игроков матча
            team_ct = eval(team_ct_str) if team_ct_str else []
            team_t = eval(team_t_str) if team_t_str else []
            all_players = team_ct + team_t
            
            # Уведомляем всех игроков об отмене матча
            for player_id in all_players:
                try:
                    bot.send_message(player_id, f"*❗ Матч #{match_id} был отменён.*\n\n👮‍♀️ По причине не один игрок не скинул скриншот «результатов матча».", parse_mode='Markdown')
                except Exception as e:
                    logging.error(f"Не удалось отправить уведомление игроку {player_id}: {e}")
            
            conn.close()
            return True, "✅ Матч успешно отменён!"
            
        except Exception as e:
            return False, f"❌ Ошибка при отмене матча: {str(e)}"

    def get_top_players(self, limit=10, league='default'):
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        if league == 'pro':
            # Для Pro League показываем только игроков с доступом к Pro League
            cursor.execute('''
                SELECT p.nickname, p.elo, p.kills, p.assists, p.deaths, p.matches_played, p.wins, p.calibration_matches, p.device
                FROM players p
                WHERE p.is_banned = FALSE AND p.user_id IN (
                    SELECT user_id FROM pro_league_users
                )
                ORDER BY p.elo DESC 
                LIMIT ?
            ''', (limit,))
        else:
            # Для Default League показываем всех игроков
            cursor.execute('''
                SELECT nickname, elo, kills, assists, deaths, matches_played, wins, calibration_matches, device
                FROM players 
                WHERE is_banned = FALSE
                ORDER BY elo DESC 
                LIMIT ?
            ''', (limit,))
        
        top_players = cursor.fetchall()
        conn.close()
        
        return top_players

    def leave_lobby(self, user_id):
        """Покидает лобби"""
        lobby_id = self.find_user_lobby(user_id)
        
        if not lobby_id:
            return False, "❌ Вы не находитесь в активном лобби"
        
        # Определяем, в какой лиге находится лобби
        is_pro = lobby_id.startswith('pro_')
        
        if is_pro:
            lobby = self.pro_lobbies[lobby_id]
        else:
            lobby = self.lobbies[lobby_id]
        
        # Если идет подтверждение или бан-пик, нельзя выйти из лобби
        if lobby['status'] in ['waiting_confirmation', 'veto']:
            return False, "❌ Нельзя выйти из лобби во время подтверждения игры или бан-пика карт!"
        
        if user_id in lobby['players']:
            lobby['players'].remove(user_id)
        if user_id in lobby['confirmed']:
            lobby['confirmed'].remove(user_id)
        
        if user_id in self.user_lobbies:
            del self.user_lobbies[user_id]
        
        self._remove_player_lobby_message(user_id, lobby_id, is_pro)
        
        self._update_lobby_message(lobby_id, is_pro)
        
        return True, "🚪 Вы вышли из лобби"

    def request_confirmation(self, lobby_id, is_pro=False):
        """Запускает процесс подтверждения игры"""
        if is_pro:
            lobby = self.pro_lobbies[lobby_id]
        else:
            lobby = self.lobbies[lobby_id]
            
        lobby['status'] = 'waiting_confirmation'
        lobby['confirmed'] = []
        lobby['confirmation_start_time'] = get_moscow_time()
        
        # Отправляем ОДНО сообщение подтверждения каждому игроку
        for player_id in lobby['players']:
            try:
                confirmation_text = self._generate_confirmation_text(lobby_id, is_pro)
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton('✅ Подтвердить готовность', callback_data='confirm_ready'))
                
                message = bot.send_message(player_id, confirmation_text, reply_markup=markup, parse_mode='Markdown')
                if 'confirmation_messages' not in lobby:
                    lobby['confirmation_messages'] = {}
                lobby['confirmation_messages'][player_id] = message.message_id
            except Exception as e:
                logging.error(f"Ошибка отправки сообщения подтверждения игроку {player_id}: {e}")
        
        # Обновляем сообщения лобби с заблокированной кнопкой выхода
        self._update_lobby_message(lobby_id, is_pro)
        
        self.start_confirmation_timer(lobby_id, is_pro)
        
        return True, "🔄 Ожидаем подтверждения от всех игроков..."

    def _generate_confirmation_text(self, lobby_id, is_pro=False):
        """Генерирует текст для подтверждения игры"""
        if is_pro:
            lobby = self.pro_lobbies[lobby_id]
        else:
            lobby = self.lobbies[lobby_id]
            
        max_players = lobby['max_players']
        confirmed_count = len(lobby['confirmed'])
        
        text = "📳 *ПОДТВЕРЖДЕНИЯ ИГРЫ*\n\n"
        text += "🔥 Подтвердите по кнопке ниже, и ожидайте других игроков.\n\n"
        text += "*Игроков подтвердило:*\n"
        
        confirmation_emojis = ""
        for i in range(max_players):
            if i < confirmed_count:
                confirmation_emojis += "✅"
            else:
                confirmation_emojis += "👤"
        
        text += f"`{confirmation_emojis}`\n\n"
        text += f"✅ *Подтвердили:* {confirmed_count}/{max_players}"
        
        return text

    def _update_confirmation_message(self, lobby_id, is_pro=False):
        """Обновляет сообщение подтверждения для всех игроков"""
        if is_pro:
            lobby = self.pro_lobbies[lobby_id]
        else:
            lobby = self.lobbies[lobby_id]
            
        confirmation_text = self._generate_confirmation_text(lobby_id, is_pro)
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton('✅ Подтвердить готовность', callback_data='confirm_ready'))
        
        if 'confirmation_messages' in lobby:
            for i, (player_id, message_id) in enumerate(lobby['confirmation_messages'].items()):
                try:
                    if i > 0:
                        time.sleep(0.1)
                    
                    success = safe_edit_message(
                        chat_id=player_id,
                        message_id=message_id,
                        text=confirmation_text,
                        reply_markup=markup,
                        parse_mode='Markdown'
                    )
                    
                    if not success:
                        del lobby['confirmation_messages'][player_id]
                        
                except Exception as e:
                    logging.error(f"Ошибка обновления сообщения игроку {player_id}: {e}")

    def start_confirmation_timer(self, lobby_id, is_pro=False):
        """Запускает таймер для проверки неподтвердивших игроков"""
        def check_confirmation():
            time.sleep(60)
            
            if is_pro:
                lobby = self.pro_lobbies.get(lobby_id)
            else:
                lobby = self.lobbies.get(lobby_id)
                
            if lobby and lobby['status'] == 'waiting_confirmation':
                not_confirmed = [pid for pid in lobby['players'] if pid not in lobby['confirmed']]
                confirmed_players = lobby['confirmed'].copy()
                
                # Наказываем только тех, кто не подтвердил (новая логика)
                for user_id in not_confirmed:
                    warnings, warning_msg = self.add_confirmation_warning(user_id)
                    try:
                        bot.send_message(user_id, warning_msg)
                        # Удаляем неподтвердившего из лобби
                        if user_id in lobby['players']:
                            lobby['players'].remove(user_id)
                        if user_id in self.user_lobbies:
                            del self.user_lobbies[user_id]
                    except:
                        pass
                
                # Уведомляем подтвердивших игроков новым текстом
                for user_id in confirmed_players:
                    try:
                        bot.send_message(user_id, "📝 Все игроки которые подтвердили были перенесены обратно в лобби. \n❗ Вы остались в лобби.")
                    except:
                        pass
                
                # Оставляем подтвердивших игроков в лобби
                lobby['players'] = confirmed_players
                lobby['confirmed'] = []
                lobby['status'] = 'waiting'
                
                if 'confirmation_messages' in lobby:
                    del lobby['confirmation_messages']
                
                # Обновляем сообщения лобби для оставшихся игроков
                self._update_lobby_message(lobby_id, is_pro)
        
        timer = threading.Thread(target=check_confirmation)
        timer.daemon = True
        timer.start()

    def find_user_lobby(self, user_id):
        """Находит лобби пользователя по всем лобби"""
        return self.user_lobbies.get(user_id)

    def confirm_ready(self, user_id):
        """Подтверждение готовности с автоматической проверкой всех игроков"""
        lobby_id = self.find_user_lobby(user_id)
        
        if not lobby_id:
            return False, "❌ Вы не находитесь в активном лобби"
        
        # Определяем, в какой лиге находится лобби
        is_pro = lobby_id.startswith('pro_')
        
        if is_pro:
            lobby = self.pro_lobbies[lobby_id]
        else:
            lobby = self.lobbies[lobby_id]
        
        if user_id not in lobby['players']:
            return False, "❌ Вы не в этом лобби"
        
        if user_id in lobby['confirmed']:
            return False, "✅ Вы уже подтвердили готовность"
        
        lobby['confirmed'].append(user_id)
        
        self._update_confirmation_message(lobby_id, is_pro)
        
        if len(lobby['confirmed']) == len(lobby['players']):
            return self.start_match(lobby_id, is_pro)
        
        return True, f"✅ Вы подтвердили готовность\nОжидаем других игроков: {len(lobby['confirmed'])}/{len(lobby['players'])}"

    def start_match(self, lobby_id, is_pro=False):
        """Начинает матч после подтверждения всех игроков - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            if is_pro:
                lobby = self.pro_lobbies[lobby_id]
            else:
                lobby = self.lobbies[lobby_id]
            
            players = lobby['players'].copy()
            
            if len(players) < lobby['max_players']:
                return False, f"❌ Недостаточно игроков для начала матча (нужно {lobby['max_players']})"
            
            # Создаем запись о матче в БД
            conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO matches (lobby_id, status, league)
                VALUES (?, 'in_progress', ?)
            ''', (lobby_id, 'pro' if is_pro else 'default'))
            
            match_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Запускаем бан-пик карт
            lobby['status'] = 'veto'
            success = self.start_map_veto(lobby_id, players, match_id, is_pro)
            
            if success:
                return True, "🎮 Запущен бан-пик карт! Ожидайте начала матча."
            else:
                # Если не удалось запустить бан-пик, сбрасываем лобби
                lobby['status'] = 'waiting'
                lobby['confirmed'] = []
                if 'confirmation_messages' in lobby:
                    del lobby['confirmation_messages']
                return False, "❌ Не удалось запустить бан-пик. Попробуйте снова."
            
        except Exception as e:
            logging.error(f"❌ Ошибка запуска матча: {e}")
            return False, f"❌ Ошибка: {str(e)}"

    def start_map_veto(self, lobby_id, players, match_id, is_pro=False):
        """Запускает процесс бан-пика карт в ОДНОМ сообщении"""
        try:
            # Сначала распределяем команды, чтобы выбрать капитанов из разных команд
            teams = self.assign_teams_with_parties(players, lobby_id, is_pro)
            if not teams:
                random.shuffle(players)
                if is_pro:
                    if lobby_id in ['pro_lobby1', 'pro_lobby2']:
                        team_ct = players[:2]
                        team_t = players[2:]
                    else:
                        team_ct = players[:5]
                        team_t = players[5:]
                else:
                    if lobby_id in ['lobby1', 'lobby2', 'lobby3', 'lobby4', 'lobby5']:
                        team_ct = players[:5]
                        team_t = players[5:]
                    else:
                        team_ct = players[:2]
                        team_t = players[2:]
            else:
                team_ct, team_t = teams
            
            # Выбираем по одному капитану из каждой команды
            captain_ct = team_ct[0]  # Первый игрок в команде CT - капитан
            captain_t = team_t[0]    # Первый игрок в команде T - капитан
            captains = [captain_ct, captain_t]
            
            # ИЗМЕНЕННЫЙ СПИСОК КАРТ
            available_maps = ["🏜️ Sandstone", "🪨 Province", "🏭 Zone 7", "🏗 Rust"]
            
            veto_session = {
                'match_id': match_id,
                'lobby_id': lobby_id,
                'captains': captains,
                'team_ct': team_ct,
                'team_t': team_t,
                'available_maps': available_maps,
                'banned_maps': [],
                'current_turn': 0,  # 0 - первый капитан (CT), 1 - второй капитан (T)
                'total_turns': 0,   # Общее количество ходов
                'start_time': get_moscow_time(),
                'all_players': players,  # Все игроки для отправки уведомлений
                'veto_message_sent': False,  # Флаг отправки сообщения
                'is_pro': is_pro,
                'timeout_timer': None  # Таймер для автоматического выбора карты
            }
            
            self.map_veto_sessions[match_id] = veto_session
            
            # Отправляем ОДНО сообщение о начале бан-пика всем игрокам
            self.send_veto_message(match_id)
            
            # Запускаем таймер для автоматического выбора карты (2 минуты)
            self.start_auto_map_selection_timer(match_id)
            
            logging.info(f"🎮 Запущен бан-пик для матча {match_id}. Капитаны: CT-{captain_ct}, T-{captain_t}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Ошибка запуска бан-пика карт: {e}")
            return False

    def start_auto_map_selection_timer(self, match_id):
        """Запускает таймер для автоматического выбора карты через 2 минуты"""
        def auto_select_map():
            time.sleep(120)  # 2 минуты
            
            veto_session = self.map_veto_sessions.get(match_id)
            if not veto_session:
                return
            
            # Если осталась одна карта, выбираем ее
            if len(veto_session['available_maps']) == 1:
                selected_map = veto_session['available_maps'][0]
                self.finish_map_veto(match_id, selected_map)
            else:
                # Если осталось несколько карт, выбираем случайную
                selected_map = random.choice(veto_session['available_maps'])
                self.finish_map_veto(match_id, selected_map)
            
            # Уведомляем всех игроков
            for player_id in veto_session['all_players']:
                try:
                    bot.send_message(player_id, f"⏰ Время на выбор карты истекло. Карта выбрана автоматически: {selected_map}")
                except:
                    pass
        
        timer = threading.Thread(target=auto_select_map)
        timer.daemon = True
        veto_session['timeout_timer'] = timer
        timer.start()

    def send_veto_message(self, match_id):
        """Отправляет ОДНО сообщение с бан-пиком всем игрокам"""
        try:
            veto_session = self.map_veto_sessions.get(match_id)
            if not veto_session:
                return False
            
            # Если сообщение уже отправлено, просто обновляем его
            if veto_session.get('veto_message_sent'):
                return self.update_veto_message(match_id)
            
            captains = veto_session['captains']
            current_captain = captains[veto_session['current_turn']]
            
            current_captain_profile = self.get_user_profile(current_captain)
            current_captain_name = current_captain_profile['nickname'] if current_captain_profile else "Капитан"
            
            # Определяем режим игры
            if len(veto_session['team_ct']) == 2 and len(veto_session['team_t']) == 2:
                game_mode = "2×2"
            else:
                game_mode = "5×5"
            
            league_prefix = "🏆 PRO LEAGUE - " if veto_session['is_pro'] else ""
            text = f"🎲 *{league_prefix}БАН-ПИК НАЧИНАЕТСЯ!* ({game_mode})\n\n"
            
            text += f"ℹ️ *Банит карту:* {current_captain_name}\n\n"
            
            text += f"🚫 *Забанено карт:* {len(veto_session['banned_maps'])}/4\n\n"
            
            # Показываем команды с капитанами
            text += "🔵 *CT*\n"
            for i, player_id in enumerate(veto_session['team_ct']):
                profile = self.get_user_profile(player_id)
                if profile:
                    captain_marker = " (C)" if player_id == veto_session['captains'][0] else ""
                    text += f"{profile['nickname']}{captain_marker}\n"
            
            text += "\n🟠 *T*\n"
            for i, player_id in enumerate(veto_session['team_t']):
                profile = self.get_user_profile(player_id)
                if profile:
                    captain_marker = " (C)" if player_id == veto_session['captains'][1] else ""
                    text += f"{profile['nickname']}{captain_marker}\n"
            
            text += "\n"
            
            # Показываем забаненные карты
            if veto_session['banned_maps']:
                text += f"🚫 *Забаненные карты:* {', '.join(veto_session['banned_maps'])}\n\n"
            
            # Показываем доступные карты
            text += f"🗺️ *Доступные карты:*\n"
            for map_name in veto_session['available_maps']:
                text += f"• {map_name}\n"
            
            text += "\n⌛ *Ожидаем полного бан-пика.....*"
            
            markup = telebot.types.InlineKeyboardMarkup()
            
            # Создаем кнопки для доступных карт (2 в ряд)
            row = []
            for i, map_name in enumerate(veto_session['available_maps']):
                # Только текущий капитан может банить карты
                callback_data = f'ban_map_{match_id}_{map_name}' 
                
                row.append(telebot.types.InlineKeyboardButton(
                    f"🚫 {map_name}", 
                    callback_data=callback_data
                ))
                if len(row) == 2 or i == len(veto_session['available_maps']) - 1:
                    markup.row(*row)
                    row = []
            
            # Отправляем сообщение только один раз для каждого игрока
            for player_id in veto_session['all_players']:
                try:
                    # Отправляем сообщение каждому игроку
                    message = bot.send_message(player_id, text, reply_markup=markup, parse_mode='Markdown')
                    # Сохраняем ID сообщения для этого игрока
                    if match_id not in self.veto_messages:
                        self.veto_messages[match_id] = {}
                    self.veto_messages[match_id][player_id] = message.message_id
                except Exception as e:
                    logging.error(f"Ошибка отправки сообщения бан-пика игроку {player_id}: {e}")
            
            veto_session['veto_message_sent'] = True
            return True
            
        except Exception as e:
            logging.error(f"❌ Ошибка отправки сообщения бан-пика: {e}")
            return False

    def update_veto_message(self, match_id):
        """Обновляет сообщение бан-пика для всех игроков"""
        try:
            veto_session = self.map_veto_sessions.get(match_id)
            if not veto_session:
                return False
            
            captains = veto_session['captains']
            current_captain = captains[veto_session['current_turn']]
            
            current_captain_profile = self.get_user_profile(current_captain)
            current_captain_name = current_captain_profile['nickname'] if current_captain_profile else "Капитан"
            
            # Определяем режим игры
            if len(veto_session['team_ct']) == 2 and len(veto_session['team_t']) == 2:
                game_mode = "2×2"
            else:
                game_mode = "5×5"
            
            league_prefix = "🏆 PRO LEAGUE - " if veto_session['is_pro'] else ""
            text = f"🎲 *{league_prefix}БАН-ПИК НАЧИНАЕТСЯ!* ({game_mode})\n\n"
            
            text += f"ℹ️ *Банит карту:* {current_captain_name}\n\n"
            
            text += f"🚫 *Забанено карт:* {len(veto_session['banned_maps'])}/4\n\n"
            
            # Показываем команды с капитанами
            text += "🔵 *CT*\n"
            for i, player_id in enumerate(veto_session['team_ct']):
                profile = self.get_user_profile(player_id)
                if profile:
                    captain_marker = " (C)" if player_id == veto_session['captains'][0] else ""
                    text += f"{profile['nickname']}{captain_marker}\n"
            
            text += "\n🟠 *T*\n"
            for i, player_id in enumerate(veto_session['team_t']):
                profile = self.get_user_profile(player_id)
                if profile:
                    captain_marker = " (C)" if player_id == veto_session['captains'][1] else ""
                    text += f"{profile['nickname']}{captain_marker}\n"
            
            text += "\n"
            
            # Показываем забаненные карты
            if veto_session['banned_maps']:
                text += f"🚫 *Забаненные карты:* {', '.join(veto_session['banned_maps'])}\n\n"
            
            # Показываем доступные карты
            text += f"🗺️ *Доступные карты:*\n"
            for map_name in veto_session['available_maps']:
                text += f"• {map_name}\n"
            
            text += "\n⌛ *Ожидаем полного бан-пика.....*"
            
            markup = telebot.types.InlineKeyboardMarkup()
            
            # Создаем кнопки для доступных карт (2 в ряд)
            row = []
            for i, map_name in enumerate(veto_session['available_maps']):
                # Только текущий капитан может банить карты
                callback_data = f'ban_map_{match_id}_{map_name}'
                
                row.append(telebot.types.InlineKeyboardButton(
                    f"🚫 {map_name}", 
                    callback_data=callback_data
                ))
                if len(row) == 2 or i == len(veto_session['available_maps']) - 1:
                    markup.row(*row)
                    row = []
            
            # Обновляем сообщение для каждого игрока
            if match_id in self.veto_messages:
                for player_id, message_id in self.veto_messages[match_id].items():
                    try:
                        success = safe_edit_message(
                            chat_id=player_id,
                            message_id=message_id,
                            text=text,
                            reply_markup=markup,
                            parse_mode='Markdown'
                        )
                        
                        if not success:
                            # Если не удалось обновить, отправляем новое сообщение
                            message = bot.send_message(player_id, text, reply_markup=markup, parse_mode='Markdown')
                            self.veto_messages[match_id][player_id] = message.message_id
                    except Exception as e:
                        logging.error(f"Ошибка обновления сообщения бан-пика игроку {player_id}: {e}")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Ошибка обновления сообщения бан-пика: {e}")
            return False

    def process_map_ban(self, match_id, user_id, map_name):
        """Обрабатывает бан карты с улучшенной логикой"""
        try:
            veto_session = self.map_veto_sessions.get(match_id)
            if not veto_session:
                return False, "❌ Сессия бан-пика не найдена или завершена"
            
            # Проверяем, что пользователь - текущий капитан
            current_captain = veto_session['captains'][veto_session['current_turn']]
            if user_id != current_captain:
                return False, "❌ Сейчас не ваш ход! Ожидайте своей очереди."
            
            # Проверяем, что карта доступна для бана
            if map_name not in veto_session['available_maps']:
                return False, "❌ Эта карта уже забанена или не существует"
            
            # Баним карту
            veto_session['available_maps'].remove(map_name)
            veto_session['banned_maps'].append(map_name)
            veto_session['total_turns'] += 1
            
            # Уведомляем всех игроков о бане
            self.notify_map_ban(match_id, user_id, map_name)
            
            # Проверяем, осталась ли одна карта
            if len(veto_session['available_maps']) == 1:
                selected_map = veto_session['available_maps'][0]
                return self.finish_map_veto(match_id, selected_map)
            
            # Меняем ход на следующего капитана
            veto_session['current_turn'] = 1 - veto_session['current_turn']  # 0->1 или 1->0
            
            # Обновляем сообщение бан-пика для всех игроков
            self.update_veto_message(match_id)
            
            return True, f"✅ Карта *{map_name}* забанена! Ход переходит следующему капитану."
            
        except Exception as e:
            logging.error(f"❌ Ошибка обработки бана карты: {e}")
            return False, f"❌ Ошибка: {str(e)}"

    def notify_map_ban(self, match_id, user_id, map_name):
        """Уведомляет всех игроков о бане карты в ОДНОМ сообщении"""
        try:
            veto_session = self.map_veto_sessions.get(match_id)
            if not veto_session:
                return
            
            captain_profile = self.get_user_profile(user_id)
            captain_name = captain_profile['nickname'] if captain_profile else "Капитан"
            
            # Вместо отдельного сообщения, просто обновляем основное сообщение бан-пика
            # Информация о бане уже будет отображена в основном сообщении
            logging.info(f"🗺️ Карта {map_name} забанена капитаном {captain_name}")
            
        except Exception as e:
            logging.error(f"❌ Ошибка уведомления о бане: {e}")

    def finish_map_veto(self, match_id, selected_map):
        """Завершает бан-пик и запускает матч"""
        try:
            veto_session = self.map_veto_sessions.get(match_id)
            if not veto_session:
                return False, "❌ Сессия бан-пика не найдена"
            
            lobby_id = veto_session['lobby_id']
            players = veto_session['all_players']
            team_ct = veto_session['team_ct']
            team_t = veto_session['team_t']
            is_pro = veto_session['is_pro']
            
            # Удаляем сообщения бан-пика
            self.cleanup_veto_messages(match_id)
            
            # Уведомляем всех игроков о выбранной карте
            self.notify_selected_map(match_id, selected_map)
            
            # Удаляем сессию бан-пика
            if match_id in self.map_veto_sessions:
                del self.map_veto_sessions[match_id]
            
            # Запускаем матч с выбранной картой
            return self.start_match_after_veto(lobby_id, players, match_id, selected_map, team_ct, team_t, is_pro)
            
        except Exception as e:
            logging.error(f"❌ Ошибка завершения бан-пика: {e}")
            return False, f"❌ Ошибка: {str(e)}"

    def cleanup_veto_messages(self, match_id):
        """Удаляет сообщения бан-пика"""
        try:
            if match_id in self.veto_messages:
                for player_id, message_id in self.veto_messages[match_id].items():
                    try:
                        bot.delete_message(player_id, message_id)
                    except:
                        pass
                del self.veto_messages[match_id]
        except Exception as e:
            logging.error(f"Ошибка очистки сообщений бан-пика: {e}")

    def notify_selected_map(self, match_id, selected_map):
        """Уведомляет всех игроков о выбранной карте - ИЗМЕНЕНО: не отправляем отдельное сообщение"""
        try:
            veto_session = self.map_veto_sessions.get(match_id)
            if not veto_session:
                return
            
            # ВМЕСТО ОТДЕЛЬНОГО СООБЩЕНИЯ, МЫ ПРОСТО ОБНОВЛЯЕМ СУЩЕСТВУЮЩЕЕ СООБЩЕНИЕ
            # С информацией о начале матча
            league_prefix = "🏆 PRO LEAGUE - " if veto_session['is_pro'] else ""
            text = f"🔄 *{league_prefix}ОБРАБОТКА МАТЧА*\n\n"
            text += f"🗺️ *Карта выбрана:* {selected_map}\n\n"
            text += "🎮 *Распределение команд...*"
            
            for player_id in veto_session['all_players']:
                try:
                    # Обновляем существующее сообщение вместо отправки нового
                    if match_id in self.veto_messages and player_id in self.veto_messages[match_id]:
                        success = safe_edit_message(
                            chat_id=player_id,
                            message_id=self.veto_messages[match_id][player_id],
                            text=text,
                            parse_mode='Markdown'
                        )
                        
                        if not success:
                            # Если не удалось обновить, отправляем новое сообщение
                            bot.send_message(player_id, text, parse_mode='Markdown')
                    else:
                        bot.send_message(player_id, text, parse_mode='Markdown')
                except Exception as e:
                    logging.error(f"Ошибка отправки уведомления игроку {player_id}: {e}")
            
        except Exception as e:
            logging.error(f"❌ Ошибка отправки уведомления о карте: {e}")

    def start_match_after_veto(self, lobby_id, players, match_id, selected_map, team_ct, team_t, is_pro=False):
        """Запускает матч после завершения бан-пика"""
        try:
            if is_pro:
                lobby = self.pro_lobbies[lobby_id]
            else:
                lobby = self.lobbies[lobby_id]
            
            if len(players) < lobby['max_players']:
                return False, f"❌ Недостаточно игроков для начала матча (нужно {lobby['max_players']})"
            
            xoct_user_id = random.choice(players)
            xoct_profile = self.get_user_profile(xoct_user_id)
            xoct_id = xoct_profile['game_id'] if xoct_profile else "Unknown"
            
            lobby['status'] = 'in_progress'
            lobby['teams'] = {'CT': team_ct, 'T': team_t}
            
            conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
            cursor = conn.cursor()
            
            league = 'pro' if is_pro else 'default'
            cursor.execute('''
                UPDATE matches SET team_ct = ?, team_t = ?, status = 'completed', league = ?
                WHERE id = ?
            ''', (str(team_ct), str(team_t), league, match_id))
            
            conn.commit()
            conn.close()
            
            thread_id = self.create_match_thread(match_id, team_ct, team_t, xoct_id, selected_map, league)
            
            self.active_matches[match_id] = {
                'lobby_id': lobby_id,
                'team_ct': team_ct,
                'team_t': team_t,
                'players': players,
                'thread_id': thread_id,
                'map': selected_map,
                'league': league
            }
            
            for player_id in players:
                self.user_match_threads[player_id] = thread_id
            
            # Отправляем информацию о матче всем игрокам
            league_prefix = "🏆 PRO LEAGUE\n" if is_pro else ""
            match_info_players = f"{league_prefix}🔑 Матч #{match_id} ({'2×2' if len(team_ct) == 2 else '5×5'})\n"
            match_info_players += f"🗺️ Карта: {selected_map}\n\n"
            
            match_info_players += "🔵 CT\n"
            for player_id in team_ct:
                profile = self.get_user_profile(player_id)
                if profile:
                    match_info_players += f"{profile['nickname']} ({profile['game_id']})\n"
            
            match_info_players += "\n🟠 T\n"
            for player_id in team_t:
                profile = self.get_user_profile(player_id)
                if profile:
                    match_info_players += f"{profile['nickname']} ({profile['game_id']})\n"
            
            match_info_players += f"\n👤 XOCT — {xoct_id}\n\n"
            match_info_players += "📤 Все игроки должны зайти в игру в течении 4-х минут."
            
            sent_players = set()
            for player_id in players:
                if player_id not in sent_players:
                    try:
                        markup = telebot.types.InlineKeyboardMarkup()
                        markup.add(telebot.types.InlineKeyboardButton('📸 Отправить результаты', callback_data='send_results'))
                        bot.send_message(player_id, match_info_players, parse_mode='Markdown', reply_markup=markup)
                        sent_players.add(player_id)
                        
                        if player_id in self.user_lobbies:
                            del self.user_lobbies[player_id]
                            
                    except Exception as e:
                        logging.error(f"Ошибка отправки сообщения о начале матча игроку {player_id}: {e}")
            
            # Очищаем лобби
            lobby['players'] = []
            lobby['confirmed'] = []
            lobby['status'] = 'waiting'
            if 'confirmation_messages' in lobby:
                del lobby['confirmation_messages']
            if 'lobby_messages' in lobby:
                lobby['lobby_messages'] = {}
            
            logging.info(f"🎮 Матч {match_id} начался на карте {selected_map} в лиге {league}")
            return True, "🎮 Матч начался!"
            
        except Exception as e:
            logging.error(f"❌ Ошибка запуска матча после бан-пика: {e}")
            return False, f"❌ Ошибка: {str(e)}"

    def assign_teams_with_parties(self, players, lobby_id, is_pro=False):
        """Распределяет команды с учетом пати - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        parties_in_lobby = []
        solo_players = []
        
        # Собираем информацию о пати
        for player_id in players:
            if player_id in self.parties:
                party = self.parties[player_id]
                if party not in parties_in_lobby:
                    parties_in_lobby.append(party)
            else:
                solo_players.append(player_id)
        
        # Определяем режим игры
        if is_pro:
            is_2x2 = lobby_id in ['pro_lobby1', 'pro_lobby2']
        else:
            is_2x2 = lobby_id in ['lobby6', 'lobby7']
        
        team_ct = []
        team_t = []
        
        if is_2x2:
            # Режим 2×2 - пати должны оставаться вместе
            for party in parties_in_lobby:
                if len(party['members']) == 2:
                    # Для пати из 2 игроков - распределяем всю пати в одну команду
                    if len(team_ct) <= len(team_t):
                        team_ct.extend(party['members'])
                    else:
                        team_t.extend(party['members'])
                else:
                    # Для пати из 1 игрока - распределяем как соло игрока
                    if len(team_ct) <= len(team_t):
                        team_ct.extend(party['members'])
                    else:
                        team_t.extend(party['members'])
            
            # Распределяем соло игроков
            for player in solo_players:
                if len(team_ct) <= len(team_t):
                    team_ct.append(player)
                else:
                    team_t.append(player)
        else:
            # Режим 5×5 - пати могут быть разделены для баланса
            for party in parties_in_lobby:
                # Распределяем игроков пати по командам для баланса
                for member in party['members']:
                    if len(team_ct) <= len(team_t):
                        team_ct.append(member)
                    else:
                        team_t.append(member)
            
            # Распределяем соло игроков
            for player in solo_players:
                if len(team_ct) <= len(team_t):
                    team_ct.append(player)
                else:
                    team_t.append(player)
        
        # Проверяем, что команды сбалансированы
        if abs(len(team_ct) - len(team_t)) > 1:
            # Если дисбаланс, перераспределяем соло игроков
            if len(team_ct) > len(team_t):
                while len(team_ct) - len(team_t) > 1:
                    player = team_ct.pop()
                    team_t.append(player)
            else:
                while len(team_t) - len(team_ct) > 1:
                    player = team_t.pop()
                    team_ct.append(player)
        
        return team_ct, team_t

    def set_match_score(self, lobby_id, score_ct, score_t):
        if lobby_id not in self.lobbies and lobby_id not in self.pro_lobbies:
            return False, "❌ Матч не найден"
        
        is_pro = lobby_id.startswith('pro_')
        if is_pro:
            lobby = self.pro_lobbies[lobby_id]
        else:
            lobby = self.lobbies[lobby_id]
        
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE matches SET score_ct = ?, score_t = ? 
            WHERE lobby_id = ? AND status = 'in_progress'
        ''', (score_ct, score_t, lobby_id))
        
        conn.commit()
        conn.close()
        
        if score_ct > score_t:
            winning_team = 'CT'
            losing_team = 'T'
        else:
            winning_team = 'T'
            losing_team = 'CT'
        
        lobby['score'] = {'CT': score_ct, 'T': score_t}
        lobby['winner'] = winning_team
        
        return True, f"✅ Счет установлен: CT {score_ct}-{score_t} T\nПобедила команда: {winning_team}"

    def parse_match_result(self, text):
        try:
            pattern = r'(\w+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)'
            matches = re.findall(pattern, text)
            
            players_data = []
            for match in matches:
                nickname, kills, assists, deaths, total_score = match
                players_data.append({
                    'nickname': nickname,
                    'kills': int(kills),
                    'assists': int(assists),
                    'deaths': int(deaths),
                    'total_score': int(total_score)
                })
            
            return players_data, f"✅ Найдено {len(players_data)} игроков"
            
        except Exception as e:
            return None, f"❌ Ошибка парсинга: {str(e)}"

    def log_unregistered_match(self, text, user_id):
        """Логирование незарегистрированного матча"""
        try:
            log_message = f"🚨 НЕЗАРЕГИСТРИРОВАННЫЙ МАТЧ\nОт: {user_id}\n\n{text}"
            for admin_id in self.log_chat_id:
                try:
                    bot.send_message(admin_id, log_message)
                except:
                    pass
        except:
            pass

    def forward_screenshot_to_match_thread(self, user_id, photo_file_id):
        """Пересылает скриншот в ветку матча"""
        try:
            thread_id = self.user_match_threads.get(user_id)
            
            if thread_id:
                # Отправляем скриншот в ветку матча
                bot.send_photo(
                    chat_id=self.match_group_id,
                    photo=photo_file_id,
                    message_thread_id=thread_id,
                    caption=f"📸 Скриншот результатов матча #{self.get_match_id_from_thread(thread_id)}"
                )
                return True, "✅ Скриншот отправлен в ветку матча!"
            else:
                return False, "❌ У вас нет активного матча или ветка матча не найдена"
                
        except Exception as e:
            logging.error(f"Ошибка пересылки скриншота: {e}")
            return False, f"❌ Ошибка отправки скриншота: {str(e)}"

    def get_match_id_from_thread(self, thread_id):
        """Получает ID матча из thread_id"""
        for match_id, match_data in self.active_matches.items():
            if match_data.get('thread_id') == thread_id:
                return match_id
        return None

    def send_match_results_to_thread(self, user_id, results_text):
        """Отправляет результаты матча в ветку"""
        try:
            thread_id = self.user_match_threads.get(user_id)
            
            if thread_id:
                bot.send_message(
                    chat_id=self.match_group_id,
                    message_thread_id=thread_id,
                    text=f"📊 *РЕЗУЛЬТАТЫ МАТЧА:*\n\n{results_text}",
                    parse_mode='Markdown'
                )
                return True, "✅ Результаты отправлены в ветку матча!"
            else:
                return False, "❌ У вас нет активного матча или ветка матча не найдена"
                
        except Exception as e:
            logging.error(f"Ошибка отправки результатов: {e}")
            return False, f"❌ Ошибка отправки результатов: {str(e)}"

    def set_score_for_thread(self, thread_id, score_ct, score_t):
        """Устанавливает счет для ветки матча"""
        self.match_scores[thread_id] = {'ct': score_ct, 't': score_t}
        return True, f"✅ Счет установлен: CT {score_ct}-{score_t} T"

    def is_score_set_for_thread(self, thread_id):
        """Проверяет, установлен ли счет для ветки"""
        return thread_id in self.match_scores

    def get_score_for_thread(self, thread_id):
        """Получает счет для ветки"""
        return self.match_scores.get(thread_id, {'ct': 0, 't': 0})

    def is_player_registered_in_thread(self, user_id, thread_id):
        """Проверяет, зарегистрирован ли игрок в ветке"""
        if thread_id in self.registered_players_in_thread:
            return user_id in self.registered_players_in_thread[thread_id]
        return False

    def is_player_rolled_back_in_thread(self, user_id, thread_id):
        """Проверяет, был ли откатан игрок в ветке"""
        if thread_id in self.rolled_back_players_in_thread:
            return user_id in self.rolled_back_players_in_thread[thread_id]
        return False

    def add_rolled_back_player_in_thread(self, user_id, thread_id):
        """Добавляет игрока в список откатанных в ветке"""
        if thread_id not in self.rolled_back_players_in_thread:
            self.rolled_back_players_in_thread[thread_id] = set()
        self.rolled_back_players_in_thread[thread_id].add(user_id)

# Создаем экземпляр бота
match_bot = MatchmakingBot()

# Словари для хранения состояний
user_states = {}
user_data = {}

# Декоратор для обработки ошибок в хендлерах
def safe_handler(func):
    def wrapper(message):
        try:
            return func(message)
        except Exception as e:
            logging.error(f"❌ Ошибка в хендлере {func.__name__}: {e}")
            try:
                bot.reply_to(message, "❌ Произошла ошибка. Попробуйте позже.")
            except:
                pass
    return wrapper

def show_main_menu(chat_id, message_id=None):
    """Показывает главное меню (исправленная версия)"""
    try:
        welcome_text = "👋 Привет. Выберите действие в главном меню бота.\n\n"
        welcome_text += "💬 Официальный канал разработки фейсита: https://t.me/shark_faceit\n\n"
        welcome_text += "Используй кнопки ниже, чтобы использовать бота. 👇"
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton('🎮 Поиск матча', callback_data='find_match'),
            telebot.types.InlineKeyboardButton('📊 Профиль', callback_data='profile')
        )
        markup.row(
            telebot.types.InlineKeyboardButton('👥 Пати', callback_data='party_menu'),
            telebot.types.InlineKeyboardButton('📈 Лидерборд', callback_data='top_players')
        )
        markup.row(
            telebot.types.InlineKeyboardButton('🗯️ Правила', url='https://telegra.ph/Shark-Faceit--Pravila-12-16'),
            telebot.types.InlineKeyboardButton('🎫 Создать тикет', callback_data='create_ticket')
        )
        
        if message_id:
            try:
                success = safe_edit_message(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=welcome_text,
                    reply_markup=markup
                )
                
                if not success:
                    bot.send_message(chat_id, welcome_text, reply_markup=markup)
                    
            except Exception as e:
                logging.error(f"Ошибка редактирования сообщения: {e}")
                bot.send_message(chat_id, welcome_text, reply_markup=markup)
        else:
            bot.send_message(chat_id, welcome_text, reply_markup=markup)
            
    except Exception as e:
        logging.error(f"❌ Ошибка в show_main_menu: {e}")
        try:
            bot.send_message(chat_id, "Добро пожаловать! Используйте кнопки для навигации.")
        except:
            pass

# ОБРАБОТЧИК ДЛЯ БАН-ПИКА КАРТ (ИСПРАВЛЕННЫЙ)
@bot.callback_query_handler(func=lambda call: call.data.startswith('ban_map_'))
@safe_handler
def ban_map_callback(call):
    user_id = call.from_user.id
    
    try:
        # Парсим данные из callback
        parts = call.data.split('_')
        match_id = int(parts[2])
        map_name = '_'.join(parts[3:])  # Объединяем оставшиеся части для карт с пробелами
        
        # Обрабатываем бан карты
        success, result_msg = match_bot.process_map_ban(match_id, user_id, map_name)
        
        if success:
            # Отправляем подтверждение
            bot.answer_callback_query(call.id, f"✅ Карта {map_name} забанена!")
        else:
            bot.answer_callback_query(call.id, result_msg)
            
    except Exception as e:
        logging.error(f"❌ Ошибка обработки бана карты: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка при выборе карты")

# ОБРАБОТЧИК ДЛЯ НЕАКТИВНЫХ КНОПОК
@bot.callback_query_handler(func=lambda call: call.data == 'no_action')
@safe_handler
def no_action_callback(call):
    """Обработчик для неактивных кнопок"""
    bot.answer_callback_query(call.id, "⏳ Эта кнопка сейчас неактивна")

# ОСНОВНЫЕ ХЕНДЛЕРЫ
@bot.message_handler(commands=['start'])
@safe_handler
def start_command(message):
    user_id = message.from_user.id
    
    # Отменяем любые активные состояния при вводе /start
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_data:
        del user_data[user_id]
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    profile = match_bot.get_user_profile(user_id)
    
    if profile:
        # Пользователь уже зарегистрирован
        show_main_menu(message.chat.id)
    else:
        # Начинаем поэтапную регистрацию с правильным форматом
        welcome_message = """
🎮 *Добро пожаловать в SHARK FACEIT!*

📝 *1 этап регистрации:*
Введите ваш никнейм (только русские/английские буквы, без цифр и символов)
        """
        
        user_states[user_id] = 'waiting_nickname'
        bot.send_message(message.chat.id, welcome_message, parse_mode='Markdown')
        
# КОМАНДА ДЛЯ ПОКАЗА МЕНЮ
@bot.message_handler(commands=['menu'])
@safe_handler
def menu_command(message):
    """Показывает меню команд"""
    user_id = message.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    menu_text = "📋 *МЕНЮ КОМАНД*\n\n"
    menu_text += "Доступные команды:\n\n"
    menu_text += "🎮 */start* - Начните пользоваться ботом! 🚀\n"
    menu_text += "📊 */profile* - Посмотреть ваш профиль ⚠️\n"
    menu_text += "👥 */party* - Управление пати\n"
    menu_text += "📈 */top* - Топ игроков\n"
    menu_text += "🎫 */ticket* - Создать тикет\n\n"
    menu_text += "Или используйте кнопки ниже:"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton('🎮 Найти матч', callback_data='find_match'),
        telebot.types.InlineKeyboardButton('📊 Профиль', callback_data='profile')
    )
    markup.row(
        telebot.types.InlineKeyboardButton('👥 Пати', callback_data='party_menu'),
        telebot.types.InlineKeyboardButton('📈 Топ игроков', callback_data='top_players')
    )
    markup.row(
        telebot.types.InlineKeyboardButton('🗯️ Правила', url='https://telegra.ph/Cristal-Faceit---Pravila-igry-10-31'),
        telebot.types.InlineKeyboardButton('🎫 Создать тикет', callback_data='create_ticket')
    )
    
    bot.send_message(message.chat.id, menu_text, reply_markup=markup, parse_mode='Markdown')

# КОМАНДА ДЛЯ ПРОФИЛЯ
@bot.message_handler(commands=['profile'])
@safe_handler
def profile_command(message):
    """Показывает профиль пользователя"""
    user_id = message.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    profile = match_bot.get_user_profile(user_id)
    
    if profile:
        device_emoji = "📱" if profile['device'] == 'Android' else "💻"
        league_emoji = "🏆" if profile['current_league'] == 'pro' else "⚡"
        
        profile_text = f"👤 Профиль игрока\n\n"
        profile_text += f"🎮 Никнейм: {profile['nickname']}\n"
        profile_text += f"🆔 ID: {profile['game_id']}\n"
        profile_text += f"📱 Устройство: {profile['device']} {device_emoji}\n"
        profile_text += f"{league_emoji} Лига: {profile['current_league'].upper()}\n"
        profile_text += f"{profile['level_emoji']} Уровень Faceit: {profile['faceit_level']}\n"
        profile_text += f"🦈 SFP: {profile['elo']}\n"
        
        # Информация о калибровке
        if profile['calibration_matches'] < 3:
            profile_text += f"🎯 Калибровка: {profile['calibration_matches']}/3 матчей\n"
        else:
            profile_text += f"✅ Калибровка завершена\n"
            
        profile_text += f"⚠️ Предупреждения: {profile['warnings']}/3\n"
        profile_text += f"📝 Предупреждения за неподтверждение: {profile['confirmation_warnings']}/3\n\n"
        profile_text += f"⚔️ Статистика:\n"
        profile_text += f"• K/D/A: {profile['kills']}/{profile['deaths']}/{profile['assists']}\n"
        profile_text += f"• Сыграно матчей: {profile['matches_played']}\n"
        profile_text += f"• Побед: {profile['wins']} | Поражений: {profile['losses']}"
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton('⚠️ Изменение данных', callback_data='edit_profile'))
        markup.row(telebot.types.InlineKeyboardButton('📊 История матчей', callback_data='match_history'))
        markup.row(telebot.types.InlineKeyboardButton('🎮 Выбрать лигу', callback_data='select_league'))
        
        markup.row(
            telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='main_menu')
        )
        
        bot.send_message(message.chat.id, profile_text, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Профиль не найден. Используйте /start")

# НОВЫЙ ХЕНДЛЕР ДЛЯ РЕДАКТИРОВАНИЯ ПРОФИЛЯ
@bot.callback_query_handler(func=lambda call: call.data == 'edit_profile')
@safe_handler
def edit_profile_callback(call):
    """Меню редактирования профиля"""
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    edit_text = "⚠️ *ИЗМЕНЕНИЕ ДАННЫХ*\n\n"
    edit_text += "Выберите, что вы хотите изменить:"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton('✏️ Изменить никнейм', callback_data='change_nickname'),
        telebot.types.InlineKeyboardButton('🆔 Изменить ID', callback_data='change_game_id')
    )
    markup.row(
        telebot.types.InlineKeyboardButton('📱 Изменить устройство', callback_data='change_device')
    )
    markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='profile'))
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text=edit_text, 
            reply_markup=markup,
            parse_mode='Markdown'
        )
        if not success:
            bot.send_message(call.message.chat.id, edit_text, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, edit_text, reply_markup=markup, parse_mode='Markdown')

# НОВЫЙ ХЕНДЛЕР ДЛЯ ВЫБОРА ЛИГИ
@bot.callback_query_handler(func=lambda call: call.data == 'select_league')
@safe_handler
def select_league_callback(call):
    """Меню выбора лиги"""
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    current_league = match_bot.get_user_league(user_id)
    has_pro_access = match_bot.has_pro_league_access(user_id)
    
    league_text = "🎮 *ВЫБОР ЛИГИ*\n\n"
    league_text += f"📊 Текущая лига: {current_league.upper()}\n\n"
    league_text += "Выберите лигу для игры:\n\n"
    league_text += "⚡ *DEFAULT* - Стандартная лига для всех игроков\n"
    
    if has_pro_access:
        league_text += "🏆 *PRO LEAGUE* - Премиум лига для опытных игроков ✅\n"
    else:
        league_text += "🏆 *PRO LEAGUE* - Премиум лига для опытных игроков 🔒\n"
        league_text += "\n❌ У вас нет доступа к Pro League\n"
        league_text += "💬 Обратитесь к @blesswayknow для получения доступа"
    
    markup = telebot.types.InlineKeyboardMarkup()
    
    if has_pro_access:
        markup.row(
            telebot.types.InlineKeyboardButton('⚡ DEFAULT', callback_data='set_league_default'),
            telebot.types.InlineKeyboardButton('🏆 PRO LEAGUE', callback_data='set_league_pro')
        )
    else:
        markup.row(telebot.types.InlineKeyboardButton('⚡ DEFAULT', callback_data='set_league_default'))
        markup.row(telebot.types.InlineKeyboardButton('🏆 PRO LEAGUE 🔒', callback_data='no_pro_access'))
    
    markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='profile'))
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text=league_text, 
            reply_markup=markup,
            parse_mode='Markdown'
        )
        if not success:
            bot.send_message(call.message.chat.id, league_text, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, league_text, reply_markup=markup, parse_mode='Markdown')

# ХЕНДЛЕР ДЛЯ УСТАНОВКИ ЛИГИ
@bot.callback_query_handler(func=lambda call: call.data.startswith('set_league_'))
@safe_handler
def set_league_callback(call):
    """Устанавливает лигу для пользователя"""
    user_id = call.from_user.id
    
    league = call.data.split('_')[2]  # default или pro
    
    success, result_msg = match_bot.set_user_league(user_id, league)
    
    if success:
        bot.answer_callback_query(call.id, f"✅ Лига изменена на {league.upper()}")
        profile_callback(call)
    else:
        bot.answer_callback_query(call.id, result_msg)

# ХЕНДЛЕР ДЛЯ ОТСУТСТВИЯ ДОСТУПА К PRO LEAGUE
@bot.callback_query_handler(func=lambda call: call.data == 'no_pro_access')
@safe_handler
def no_pro_access_callback(call):
    """Сообщение об отсутствии доступа к Pro League"""
    bot.answer_callback_query(call.id, "❌ У вас нет доступа к Pro League. Обратитесь к @blesswayknow")

@bot.callback_query_handler(func=lambda call: call.data == 'find_match')
@safe_handler
def find_match_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    current_league = match_bot.get_user_league(user_id)
    
    league_text = "🎮 *ВЫБОР РЕЖИМА ИГРЫ*\n\n"
    league_text += f"📊 Текущая лига: {current_league.upper()}\n\n"
    league_text += "Выберите режим игры:"
    
    markup = telebot.types.InlineKeyboardMarkup()
    
    if current_league == 'pro':
        markup.row(
            telebot.types.InlineKeyboardButton('⚡ DEFAULT', callback_data='switch_league_default'),
            telebot.types.InlineKeyboardButton('🏆 PRO LEAGUE ✅', callback_data='find_pro_match')
        )
    else:
        markup.row(
            telebot.types.InlineKeyboardButton('⚡ DEFAULT ✅', callback_data='find_default_match'),
            telebot.types.InlineKeyboardButton('🏆 PRO LEAGUE', callback_data='switch_league_pro')
        )
    
    markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='main_menu'))
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text=league_text, 
            reply_markup=markup,
            parse_mode='Markdown'
        )
        if not success:
            bot.send_message(call.message.chat.id, league_text, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, league_text, reply_markup=markup, parse_mode='Markdown')

# ХЕНДЛЕР ДЛЯ ПЕРЕКЛЮЧЕНИЯ ЛИГИ ИЗ МЕНЮ ПОИСКА МАТЧА
@bot.callback_query_handler(func=lambda call: call.data.startswith('switch_league_'))
@safe_handler
def switch_league_from_match_callback(call):
    """Переключает лигу из меню поиска матча"""
    user_id = call.from_user.id
    
    league = call.data.split('_')[2]  # default или pro
    
    if league == 'pro' and not match_bot.has_pro_league_access(user_id):
        bot.answer_callback_query(call.id, "❌ У вас нет доступа к Pro League. Обратитесь к @blesswayknow")
        return
    
    success, result_msg = match_bot.set_user_league(user_id, league)
    
    if success:
        bot.answer_callback_query(call.id, f"✅ Лига изменена на {league.upper()}")
        find_match_callback(call)
    else:
        bot.answer_callback_query(call.id, result_msg)

# ХЕНДЛЕР ДЛЯ ПОИСКА МАТЧА В DEFAULT ЛИГЕ
@bot.callback_query_handler(func=lambda call: call.data == 'find_default_match')
@safe_handler
def find_default_match_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    user_device = match_bot.get_user_device(user_id)
    
    markup = telebot.types.InlineKeyboardMarkup()
    
    # Показываем только доступные лобби для устройства пользователя
    available_lobbies = []
    
    # Лобби 1 - только телефоны (Android)
    if user_device == 'Android':
        markup.row(telebot.types.InlineKeyboardButton('📱 LOBBY 1 5×5', callback_data='lobby_1'))
        available_lobbies.append('lobby1')
    
    # Лобби 2 - только телефоны (Android)
    if user_device == 'Android':
        markup.row(telebot.types.InlineKeyboardButton('📱 LOBBY 2 5×5', callback_data='lobby_2'))
        available_lobbies.append('lobby2')
    
    # Лобби 3 - телефоны (Android) + ПК
    markup.row(telebot.types.InlineKeyboardButton('📱💻 LOBBY 3 5×5', callback_data='lobby_3'))
    available_lobbies.append('lobby3')
    
    # Лобби 4 - телефоны (Android) + ПК
    markup.row(telebot.types.InlineKeyboardButton('📱💻 LOBBY 4 5×5', callback_data='lobby_4'))
    available_lobbies.append('lobby4')
    
    # Лобби 5 - только ПК
    if user_device == 'PC':
        markup.row(telebot.types.InlineKeyboardButton('💻 LOBBY 5 5×5', callback_data='lobby_5'))
        available_lobbies.append('lobby5')
    
    # Лобби 6 - телефоны (Android) + ПК
    markup.row(telebot.types.InlineKeyboardButton('📱💻 LOBBY 6 2×2', callback_data='lobby_6'))
    available_lobbies.append('lobby6')
    
    # Лобби 7 - только телефоны (Android)
    if user_device == 'Android':
        markup.row(telebot.types.InlineKeyboardButton('📱 LOBBY 7 2×2', callback_data='lobby_7'))
        available_lobbies.append('lobby7')
    
    markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='find_match'))
    
    lobby_info = "🎮 *DEFAULT LEAGUE* - Доступные лобби:\n\n"
    
    device_restrictions = {
        'lobby1': '📱 Только телефоны (Android)',
        'lobby2': '📱 Только телефоны (Android)',
        'lobby3': '📱💻 Телефоны (Android) + ПК',
        'lobby4': '📱💻 Телефоны (Android) + ПК',
        'lobby5': '💻 Только ПК',
        'lobby6': '📱💻 Телефоны (Android) + ПК',
        'lobby7': '📱 Только телефоны (Android)'
    }
    
    for lobby_id in available_lobbies:
        lobby = match_bot.lobbies[lobby_id]
        players_count = len(lobby['players'])
        max_players = lobby['max_players']
        restriction = device_restrictions[lobby_id]
        
        lobby_info += f"🎮 {restriction}: {players_count}/{max_players} игроков\n"
    
    lobby_info += f"\n📱 Ваше устройство: {user_device}"
    lobby_info += "\n\nВыберите лобби для присоединения:"
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text=lobby_info, 
            reply_markup=markup,
            parse_mode='Markdown'
        )
        if not success:
            bot.send_message(call.message.chat.id, lobby_info, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, lobby_info, reply_markup=markup, parse_mode='Markdown')

# ХЕНДЛЕР ДЛЯ ПОИСКА МАТЧА В PRO LEAGUE
@bot.callback_query_handler(func=lambda call: call.data == 'find_pro_match')
@safe_handler
def find_pro_match_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    # Проверяем доступ к Pro League
    if not match_bot.has_pro_league_access(user_id):
        bot.answer_callback_query(call.id, "❌ У вас нет доступа к Pro League. Обратитесь к @blesswayknow")
        return
    
    user_device = match_bot.get_user_device(user_id)
    
    markup = telebot.types.InlineKeyboardMarkup()
    
    # Показываем только доступные лобби для устройства пользователя в Pro League
    available_lobbies = []
    
    # Pro Lobby 1 - 2x2 только телефоны (Android)
    if user_device == 'Android':
        markup.row(telebot.types.InlineKeyboardButton('📱 PRO LOBBY 1 2×2', callback_data='pro_lobby_1'))
        available_lobbies.append('pro_lobby1')
    
    # Pro Lobby 2 - 2x2 только компьютеры
    if user_device == 'PC':
        markup.row(telebot.types.InlineKeyboardButton('💻 PRO LOBBY 2 2×2', callback_data='pro_lobby_2'))
        available_lobbies.append('pro_lobby2')
    
    # Pro Lobby 3 - 5x5 только телефоны (Android)
    if user_device == 'Android':
        markup.row(telebot.types.InlineKeyboardButton('📱 PRO LOBBY 3 5×5', callback_data='pro_lobby_3'))
        available_lobbies.append('pro_lobby3')
    
    # Pro Lobby 4 - 5x5 только компьютеры
    if user_device == 'PC':
        markup.row(telebot.types.InlineKeyboardButton('💻 PRO LOBBY 4 5×5', callback_data='pro_lobby_4'))
        available_lobbies.append('pro_lobby4')
    
    markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='find_match'))
    
    lobby_info = "🏆 *PRO LEAGUE* - Доступные лобби:\n\n"
    
    device_restrictions = {
        'pro_lobby1': '📱 Только телефоны (Android) (2×2)',
        'pro_lobby2': '💻 Только компьютеры (2×2)',
        'pro_lobby3': '📱 Только телефоны (Android) (5×5)',
        'pro_lobby4': '💻 Только компьютеры (5×5)'
    }
    
    for lobby_id in available_lobbies:
        lobby = match_bot.pro_lobbies[lobby_id]
        players_count = len(lobby['players'])
        max_players = lobby['max_players']
        restriction = device_restrictions[lobby_id]
        
        lobby_info += f"🎮 {restriction}: {players_count}/{max_players} игроков\n"
    
    lobby_info += f"\n📱 Ваше устройство: {user_device}"
    lobby_info += "\n\nВыберите лобби для присоединения:"
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text=lobby_info, 
            reply_markup=markup,
            parse_mode='Markdown'
        )
        if not success:
            bot.send_message(call.message.chat.id, lobby_info, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, lobby_info, reply_markup=markup, parse_mode='Markdown')

# ОБНОВЛЕННЫЙ ХЕНДЛЕР ДЛЯ ПРИСОЕДИНЕНИЯ К ЛОББИ (ОБРАБАТЫВАЕТ ОБЕ ЛИГИ)
@bot.callback_query_handler(func=lambda call: call.data.startswith(('lobby_', 'pro_lobby_')))
@safe_handler
def join_lobby_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    # Определяем лигу по префиксу callback данных
    is_pro = call.data.startswith('pro_')
    
    if is_pro:
        # Проверяем доступ к Pro League
        if not match_bot.has_pro_league_access(user_id):
            bot.send_message(call.message.chat.id, "❌ У вас нет доступа к Pro League. Обратитесь к @blesswayknow для получения доступа.")
            return
        
        lobby_map = {
            'pro_lobby_1': 'pro_lobby1',
            'pro_lobby_2': 'pro_lobby2', 
            'pro_lobby_3': 'pro_lobby3',
            'pro_lobby_4': 'pro_lobby4'
        }
    else:
        lobby_map = {
            'lobby_1': 'lobby1',
            'lobby_2': 'lobby2', 
            'lobby_3': 'lobby3',
            'lobby_4': 'lobby4',
            'lobby_5': 'lobby5',
            'lobby_6': 'lobby6',
            'lobby_7': 'lobby7'
        }
    
    lobby_id = lobby_map[call.data]
    
    success, result_msg = match_bot.join_lobby(user_id, lobby_id, is_pro)
    
    # Отправляем только одно сообщение с результатом
    if success:
        # Не отправляем отдельное сообщение, так как _send_lobby_message уже отправил сообщение лобби
        # и result_msg содержит информацию о входе
        bot.answer_callback_query(call.id, result_msg)
    else:
        bot.send_message(call.message.chat.id, result_msg)

# ОСТАЛЬНЫЕ ХЕНДЛЕРЫ ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ (но адаптированы под две лиги)

@bot.callback_query_handler(func=lambda call: call.data == 'leave_lobby')
@safe_handler
def leave_lobby_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    success, result_msg = match_bot.leave_lobby(user_id)
    
    # Отправляем сообщение о выходе из лобби с кнопкой "Назад"
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='main_menu'))
    
    bot.send_message(call.message.chat.id, result_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'confirm_ready')
@safe_handler
def confirm_ready_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    success, result_msg = match_bot.confirm_ready(user_id)
    
    # ИСПРАВЛЕННАЯ ЛОГИКА: проверяем успешность
    if success:
        # Проверяем, не начинается ли бан-пик (матч)
        if "Запущен бан-пик" in result_msg:
            bot.send_message(call.message.chat.id, result_msg)
        else:
            bot.send_message(call.message.chat.id, result_msg)
    else:
        bot.send_message(call.message.chat.id, result_msg)

@bot.callback_query_handler(func=lambda call: call.data == 'profile')
@safe_handler
def profile_callback(call):
    user_id = call.from_user.id
    profile = match_bot.get_user_profile(user_id)
    
    if profile:
        device_emoji = "📱" if profile['device'] == 'Android' else "💻"
        league_emoji = "🏆" if profile['current_league'] == 'pro' else "⚡"
        
        profile_text = f"👤 Профиль игрока | {profile['nickname']}\n\n"
        profile_text += f"🆔 ID: {profile['game_id']}\n"
        profile_text += f"📱 Устройство: {profile['device']}\n"
        profile_text += f"{league_emoji} Лига: {profile['current_league'].upper()}\n"
        profile_text += f"{profile['level_emoji']} Уровень Faceit: {profile['faceit_level']}\n"
        profile_text += f"🦈 SFP: {profile['elo']}\n"
        
        # Информация о калибровке
        if profile['calibration_matches'] < 3:
            profile_text += f"🎯 Калибровочных матчей: {profile['calibration_matches']}/3\n"
        else:
            profile_text += f"✅ Калибровка завершена\n"
            
        profile_text += f"\n⚔️ Статистика:\n"
        profile_text += f"• Убийств: {profile['kills']}\n"
        profile_text += f"• Смертей: {profile['deaths']}\n"
        profile_text += f"• Помощи: {profile['assists']}\n"
        
        # Рассчитываем K/D
        kd = profile['kills'] / profile['deaths'] if profile['deaths'] > 0 else profile['kills']
        profile_text += f"• K/D: {kd:.2f}\n"
        
        profile_text += f"• Матчей: {profile['matches_played']}\n"
        profile_text += f"• Побед: {profile['wins']}\n"
        profile_text += f"• Поражений: {profile['losses']}\n"
        
        # Рассчитываем винрейт
        winrate = (profile['wins'] / profile['matches_played'] * 100) if profile['matches_played'] > 0 else 0
        profile_text += f"• Винрейт: {winrate:.1f}%"
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton('⚠️ Изменение данных', callback_data='edit_profile'))
        markup.row(telebot.types.InlineKeyboardButton('📊 История матчей', callback_data='match_history'))
        markup.row(telebot.types.InlineKeyboardButton('🎮 Выбрать лигу', callback_data='select_league'))
        markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='main_menu'))
        
        try:
            success = safe_edit_message(
                chat_id=call.message.chat.id, 
                message_id=call.message.message_id,
                text=profile_text, 
                reply_markup=markup
            )
            if not success:
                bot.send_message(call.message.chat.id, profile_text, reply_markup=markup)
        except Exception as e:
            logging.error(f"Ошибка редактирования сообщения: {e}")
            bot.send_message(call.message.chat.id, profile_text, reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, "❌ Профиль не найден. Используйте /start")

# НОВЫЙ ХЕНДЛЕР ДЛЯ ИСТОРИИ МАТЧЕЙ
@bot.callback_query_handler(func=lambda call: call.data == 'match_history')
@safe_handler
def match_history_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    profile = match_bot.get_user_profile(user_id)
    match_history = match_bot.get_match_history(user_id, 5)
    
    if not match_history:
        history_text = "📊 История матчей\n\n"
        history_text += "У вас пока нет сыгранных матчей.\n"
        history_text += "Сыграйте свой первый матч, чтобы увидеть здесь статистику!"
    else:
        history_text = "📊 История матчей\n\n"
        
        for match in match_history:
            league_prefix = "🏆 " if match['league'] == 'pro' else "⚡ "
            history_text += f"{league_prefix}Матч #{match['number']}\n"
            
            # Определяем номер матча
            if match['match_id']:
                match_number = f"#{match['match_id']}"
            else:
                match_number = "#неизвестный"
            
            history_text += f"🔍 Номер матча: {match_number}\n"
            history_text += f"✏️ Nickname: {profile['nickname']}\n"
            history_text += f"🦈 SFP: {profile['elo'] + match['elo_change']}\n"
            history_text += f"📊 Статистика: {match['kills']}/{match['assists']}/{match['deaths']}\n"
            history_text += f"📄 Карта: {match['map']}\n"
            history_text += f"🔑 Режим: {match['game_mode']}\n"
            history_text += f"📝 Статус: {match['match_status']}\n"
            
            # Определяем результат
            if match['result'] == 'win':
                history_text += "Результат: выиграл\n"
            else:
                history_text += "Результат: проиграл\n"
            
            history_text += "\n"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='profile'))
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text=history_text, 
            reply_markup=markup
        )
        if not success:
            bot.send_message(call.message.chat.id, history_text, reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, history_text, reply_markup=markup)

# НОВЫЙ ХЕНДЛЕР ДЛЯ ИЗМЕНЕНИЯ УСТРОЙСТВА
@bot.callback_query_handler(func=lambda call: call.data == 'change_device')
@safe_handler
def change_device_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    current_device = match_bot.get_user_device(user_id)
    
    device_text = f"📱 Изменение устройства\n\n"
    device_text += f"📱 Ваше устройство: {current_device}\n\n"
    device_text += "Выберите ваше устройство:"
    
    markup = telebot.types.InlineKeyboardMarkup()
    
    if current_device == 'Android':
        markup.row(
            telebot.types.InlineKeyboardButton('💻 PC', callback_data='set_device_pc')
        )
    else:  # PC
        markup.row(
            telebot.types.InlineKeyboardButton('📱 Android', callback_data='set_device_android')
        )
    
    markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='edit_profile'))
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text=device_text, 
            reply_markup=markup
        )
        if not success:
            bot.send_message(call.message.chat.id, device_text, reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, device_text, reply_markup=markup)

# ХЕНДЛЕРЫ ДЛЯ УСТАНОВКИ УСТРОЙСТВА
@bot.callback_query_handler(func=lambda call: call.data.startswith('set_device_'))
@safe_handler
def set_device_callback(call):
    user_id = call.from_user.id
    
    device_map = {
        'set_device_android': 'Android',
        'set_device_pc': 'PC'
    }
    
    device = device_map[call.data]
    
    success, result_msg = match_bot.update_user_device(user_id, device)
    
    if success:
        bot.answer_callback_query(call.id, f"✅ Устройство изменено на {device}")
        edit_profile_callback(call)
    else:
        bot.answer_callback_query(call.id, result_msg)

@bot.callback_query_handler(func=lambda call: call.data == 'top_players')
@safe_handler
def top_players_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    # Получаем текущую лигу пользователя для отображения соответствующего топа
    current_league = match_bot.get_user_league(user_id)
    
    top_players = match_bot.get_top_players(10, current_league)
    
    league_title = "PRO LEAGUE" if current_league == 'pro' else "DEFAULT"
    
    if not top_players:
        top_text = f"🏆 ТОП 10 ИГРОКОВ - {league_title}\n\n"
        top_text += "📊 Пока нет зарегистрированных игроков в этой лиге"
    else:
        top_text = f"🏆 ТОП 10 ИГРОКОВ - {league_title}:\n\n"
        
        for i, (nickname, elo, kills, assists, deaths, matches, wins, calib_matches, device) in enumerate(top_players, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            kda = f"K:{kills} D:{deaths} A:{assists}"
            win_rate = (wins / matches * 100) if matches > 0 else 0
            faceit_level = match_bot.get_faceit_level(elo)
            level_emoji = match_bot.get_faceit_level_emoji(faceit_level)
            device_emoji = "📱" if device == 'Android' else "💻"
            
            top_text += f"{medal} {nickname} {device_emoji}\n"
            top_text += f"   {level_emoji} Уровень {faceit_level} | 🦈 SFP: {elo}\n"
            top_text += f"   📊 {kda} | 🎯 Матчей: {matches}\n"
            
            if calib_matches < 3:
                top_text += f"   🎯 Калибровка: {calib_matches}/3\n"
            else:
                top_text += f"   📈 Винрейт: {win_rate:.1f}%\n"
            
            top_text += "\n"
    
    # УБРАНА ИНФОРМАЦИЯ О ПОЗИЦИИ ПОЛЬЗОВАТЕЛЯ
    
    markup = telebot.types.InlineKeyboardMarkup()
    
    # Добавляем кнопки для переключения между лигами
    if current_league == 'pro':
        markup.row(telebot.types.InlineKeyboardButton('⚡ Посмотреть топ DEFAULT', callback_data='top_default'))
    else:
        markup.row(telebot.types.InlineKeyboardButton('🏆 Посмотреть топ PRO LEAGUE', callback_data='top_pro'))
    
    markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='main_menu'))
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text=top_text, 
            reply_markup=markup
        )
        if not success:
            bot.send_message(call.message.chat.id, top_text, reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, top_text, reply_markup=markup)

# ХЕНДЛЕРЫ ДЛЯ ПЕРЕКЛЮЧЕНИЯ ТОПА МЕЖДУ ЛИГАМИ
@bot.callback_query_handler(func=lambda call: call.data == 'top_default')
@safe_handler
def top_default_callback(call):
    """Показывает топ игроков Default лиги"""
    user_id = call.from_user.id
    match_bot.set_user_league(user_id, 'default')
    top_players_callback(call)

@bot.callback_query_handler(func=lambda call: call.data == 'top_pro')
@safe_handler
def top_pro_callback(call):
    """Показывает топ игроков Pro League"""
    user_id = call.from_user.id
    
    # Проверяем доступ к Pro League
    if not match_bot.has_pro_league_access(user_id):
        bot.answer_callback_query(call.id, "❌ У вас нет доступа к Pro League. Обратитесь к @blesswayknow")
        return
    
    match_bot.set_user_league(user_id, 'pro')
    top_players_callback(call)

# ОБНОВЛЕННЫЕ ОБРАБОТЧИКИ ДЛЯ РЕГИСТРАЦИИ С ВЫБОРОМ УСТРОЙСТВА
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_nickname')
@safe_handler
def handle_nickname(message):
    user_id = message.from_user.id
    
    # Если пользователь ввел /start, отменяем текущее действие
    if message.text == '/start':
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        start_command(message)
        return
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    nickname = message.text.strip()
    
    # Проверка никнейма - минимум 2 символа
    if len(nickname) < 2:
        bot.send_message(message.chat.id, "❌ Никнейм должен содержать минимум 2 символа! Попробуйте еще раз:")
        return
    
    # Проверка на пробелы в никнейме
    if ' ' in nickname:
        bot.send_message(message.chat.id, "❌ Никнейм не должен содержать пробелов! Используйте одно слово. Попробуйте еще раз:")
        return
    
    # Проверка на наличие только букв (русские/английские)
    if not re.match(r'^[A-Za-zА-Яа-яЁё]+$', nickname):
        bot.send_message(message.chat.id, "❌ Никнейм должен содержать только русские или английские буквы, без цифр и символов! Попробуйте еще раз:")
        return
    
    user_data[user_id] = {'nickname': nickname}
    user_states[user_id] = 'waiting_game_id'
    
    # Отправляем сообщение о втором этапе
    step2_message = f"""
✅ *Никнейм принят:* {nickname}

📝 *2 этап регистрации:*
Введите ваш игровой ID (минимум 3 символа, можно буквы и цифры)
    """
    
    bot.send_message(message.chat.id, step2_message, parse_mode='Markdown')

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_game_id')
@safe_handler
def handle_game_id(message):
    user_id = message.from_user.id
    
    # Если пользователь ввел /start, отменяем текущее действие
    if message.text == '/start':
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        start_command(message)
        return
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    if user_id in user_data:
        game_id = message.text.strip()
        
        # Проверка игрового ID - минимум 3 символа
        if len(game_id) < 3:
            bot.send_message(message.chat.id, "❌ Игровой ID должен содержать минимум 3 символа! Попробуйте еще раз:")
            return
        
        user_data[user_id]['game_id'] = game_id
        user_states[user_id] = 'waiting_device'
        
        # Отправляем сообщение о третьем этапе
        nickname = user_data[user_id]['nickname']
        step3_message = f"""
✅ *Никнейм:* {nickname}
✅ *Игровой ID принят:* {game_id}

📝 *3 этап регистрации:*
Выберите ваше устройство:
На каком устройстве вы будете играть?
        """
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton('📱 Android (Телефон)', callback_data='reg_device_android'),
            telebot.types.InlineKeyboardButton('💻 PC (Компьютер)', callback_data='reg_device_pc')
        )
        
        bot.send_message(message.chat.id, step3_message, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('reg_device_'))
@safe_handler
def handle_reg_device(call):
    user_id = call.from_user.id
    
    if user_id in user_states and user_states[user_id] == 'waiting_device':
        device_map = {
            'reg_device_android': 'Android',
            'reg_device_pc': 'PC'
        }
        
        device = device_map[call.data]
        device_emoji = "📱" if device == 'Android' else "💻"
        
        if user_id in user_data:
            nickname = user_data[user_id]['nickname']
            game_id = user_data[user_id]['game_id']
            
            # Сохраняем устройство в user_data
            user_data[user_id]['device'] = device
            
            # Отправляем сообщение о четвертом этапе (подтверждение)
            confirmation_message = f"""
✅ *Никнейм:* {nickname}
✅ *Игровой ID:* {game_id}
✅ *Устройство:* {device} {device_emoji}

📝 *4 этап регистрации:*
Подтвердите вашу регистрацию

*Ваши данные:*
👤 Никнейм: {nickname}
🆔 Игровой ID: {game_id}
📱 Устройство: {device} {device_emoji}

Всё верно?
            """
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton('✅ Подтвердить', callback_data='confirm_registration'),
                telebot.types.InlineKeyboardButton('🔄 Начать заново', callback_data='restart_registration')
            )
            
            try:
                success = safe_edit_message(
                    chat_id=call.message.chat.id, 
                    message_id=call.message.message_id,
                    text=confirmation_message, 
                    reply_markup=markup,
                    parse_mode='Markdown'
                )
                if not success:
                    bot.send_message(call.message.chat.id, confirmation_message, reply_markup=markup, parse_mode='Markdown')
            except Exception as e:
                logging.error(f"Ошибка редактирования сообщения: {e}")
                bot.send_message(call.message.chat.id, confirmation_message, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'confirm_registration')
@safe_handler
def confirm_registration_callback(call):
    user_id = call.from_user.id
    
    if user_id in user_states and user_states[user_id] == 'waiting_device' and user_id in user_data:
        nickname = user_data[user_id]['nickname']
        game_id = user_data[user_id]['game_id']
        device = user_data[user_id]['device']
        
        # Регистрируем пользователя
        success, result_msg = match_bot.register_user(user_id, nickname, game_id, device)
        
        # Отправляем финальное сообщение
        if success:
            final_message = f"""
✅ *РЕГИСТРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!*

🎮 *Добро пожаловать в SHARK FACEIT!*

*Ваши данные:*
👤 Никнейм: {nickname}
🆔 Игровой ID: {game_id}
📱 Устройство: {device}
🦈 Начальный SFP: 0

{result_msg}

Используйте меню ниже для навигации:
            """
            
            # Очищаем состояния
            user_states.pop(user_id, None)
            user_data.pop(user_id, None)
            
            # Показываем главное меню
            show_main_menu(call.message.chat.id)
        else:
            bot.answer_callback_query(call.id, result_msg)

@bot.callback_query_handler(func=lambda call: call.data == 'restart_registration')
@safe_handler
def restart_registration_callback(call):
    user_id = call.from_user.id
    
    # Очищаем состояния и начинаем заново
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_data:
        del user_data[user_id]
    
    # Запускаем регистрацию заново
    welcome_message = """
🎮 *Добро пожаловать в SHARK FACEIT!*

📝 *1 этап регистрации:*
Введите ваш никнейм (только русские/английские буквы, без цифр и символов)
    """
    
    user_states[user_id] = 'waiting_nickname'
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text=welcome_message, 
            parse_mode='Markdown'
        )
        if not success:
            bot.send_message(call.message.chat.id, welcome_message, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, welcome_message, parse_mode='Markdown')

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_game_id')
@safe_handler
def handle_game_id(message):
    user_id = message.from_user.id
    
    # Если пользователь ввел /start, отменяем текущее действие
    if message.text == '/start':
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        start_command(message)
        return
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    if user_id in user_data:
        nickname = user_data[user_id]['nickname']
        game_id = message.text.strip()
        
        # Проверка игрового ID - минимум 3 символа
        if len(game_id) < 3:
            bot.send_message(message.chat.id, "❌ Игровой ID должен содержать минимум 3 символа! Попробуйте еще раз:")
            return
        
        user_data[user_id]['game_id'] = game_id
        user_states[user_id] = 'waiting_device'
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton('📱 Android', callback_data='reg_device_android'),
            telebot.types.InlineKeyboardButton('💻 PC', callback_data='reg_device_pc')
        )
        
        bot.send_message(message.chat.id, "📱 Выберите ваше устройство:", reply_markup=markup)

# ОБРАБОТЧИК ВЫБОРА УСТРОЙСТВА ПРИ РЕГИСТРАЦИИ
@bot.callback_query_handler(func=lambda call: call.data.startswith('reg_device_'))
@safe_handler
def handle_reg_device(call):
    user_id = call.from_user.id
    
    if user_id in user_states and user_states[user_id] == 'waiting_device':
        device_map = {
            'reg_device_android': 'Android',
            'reg_device_pc': 'PC'
        }
        
        device = device_map[call.data]
        
        if user_id in user_data:
            nickname = user_data[user_id]['nickname']
            game_id = user_data[user_id]['game_id']
            
            success, result_msg = match_bot.register_user(user_id, nickname, game_id, device)
            bot.send_message(call.message.chat.id, result_msg)
            
            if user_id in user_states:
                del user_states[user_id]
            if user_id in user_data:
                del user_data[user_id]
            
            if success:
                show_main_menu(call.message.chat.id)

# ОБНОВЛЕННЫЙ ОБРАБОТЧИК ИЗМЕНЕНИЯ ID
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_new_game_id')
@safe_handler
def handle_new_game_id(message):
    user_id = message.from_user.id
    
    # Если пользователь ввел /start, отменяем текущее действие
    if message.text == '/start':
        user_states.pop(user_id, None)
        show_main_menu(message.chat.id)
        return
    
    if user_id in user_states and user_states[user_id] == 'waiting_new_game_id':
        new_game_id = message.text.strip()
        
        if not new_game_id:
            bot.send_message(message.chat.id, "❌ Игровой ID не может быть пустым. Попробуйте еще раз:")
            return
        
        # Проверка игрового ID - минимум 3 символа
        if len(new_game_id) < 3:
            bot.send_message(message.chat.id, "❌ Игровой ID должен содержать минимум 3 символа! Попробуйте еще раз:")
            return
        
        success, result_msg = match_bot.update_user_game_id(user_id, new_game_id)
        bot.send_message(message.chat.id, result_msg)
        
        user_states.pop(user_id, None)
        show_main_menu(message.chat.id)

# НОВЫЙ ХЕНДЛЕР ДЛЯ СОЗДАНИЯ ТИКЕТА
@bot.callback_query_handler(func=lambda call: call.data == 'create_ticket')
@safe_handler
def create_ticket_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    # Начинаем процесс создания тикета
    match_bot.ticket_sessions[user_id] = {'step': 'waiting_match_id'}
    
    ticket_text = "ℹ️ *Подача жалобы.*\n\n"
    ticket_text += "Укажите Match ID матча, для подачи жалобы. Чтобы посмотреть Match ID можете в профиль — сыгранные игры и смотрите последнюю игру.\n\n"
    ticket_text += "⚠️ *За предоставление фейковой информации вы получите «наказание».*"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton('🔄 Отменить тикет', callback_data='cancel_ticket'))
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text=ticket_text, 
            reply_markup=markup,
            parse_mode='Markdown'
        )
        if not success:
            bot.send_message(call.message.chat.id, ticket_text, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, ticket_text, reply_markup=markup, parse_mode='Markdown')

# ХЕНДЛЕР ДЛЯ ОТМЕНЫ ТИКЕТА
@bot.callback_query_handler(func=lambda call: call.data == 'cancel_ticket')
@safe_handler
def cancel_ticket_callback(call):
    user_id = call.from_user.id
    
    if user_id in match_bot.ticket_sessions:
        del match_bot.ticket_sessions[user_id]
    
    cancel_text = "✏️ Подача тикета была отменена."
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu'))
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text=cancel_text, 
            reply_markup=markup
        )
        if not success:
            bot.send_message(call.message.chat.id, cancel_text, reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, cancel_text, reply_markup=markup)

# ОБРАБОТЧИК ДЛЯ ВВОДА MATCH ID
@bot.message_handler(func=lambda message: match_bot.ticket_sessions.get(message.from_user.id, {}).get('step') == 'waiting_match_id')
@safe_handler
def handle_ticket_match_id(message):
    user_id = message.from_user.id
    
    # Если пользователь ввел /start, отменяем текущее действие
    if message.text == '/start':
        if user_id in match_bot.ticket_sessions:
            del match_bot.ticket_sessions[user_id]
        show_main_menu(message.chat.id)
        return
    
    if user_id in match_bot.ticket_sessions and match_bot.ticket_sessions[user_id]['step'] == 'waiting_match_id':
        match_id = message.text.strip()
        
        # Проверяем, что введены только цифры
        if not match_id.isdigit():
            bot.send_message(message.chat.id, "❌ Match ID должен содержать только цифры! Попробуйте еще раз:")
            return
        
        match_bot.ticket_sessions[user_id] = {
            'step': 'waiting_nickname',
            'match_id': match_id
        }
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton('🔄 Отменить тикет', callback_data='cancel_ticket'))
        
        bot.send_message(message.chat.id, "⏳ Укажите никнейм игрока на которого вы хотите подать жалобу:", reply_markup=markup)

# ОБРАБОТЧИК ДЛЯ ВВОДА НИКНЕЙМА
@bot.message_handler(func=lambda message: match_bot.ticket_sessions.get(message.from_user.id, {}).get('step') == 'waiting_nickname')
@safe_handler
def handle_ticket_nickname(message):
    user_id = message.from_user.id
    
    # Если пользователь ввел /start, отменяем текущее действие
    if message.text == '/start':
        if user_id in match_bot.ticket_sessions:
            del match_bot.ticket_sessions[user_id]
        show_main_menu(message.chat.id)
        return
    
    if user_id in match_bot.ticket_sessions and match_bot.ticket_sessions[user_id]['step'] == 'waiting_nickname':
        reported_nickname = message.text.strip()
        
        if not reported_nickname:
            bot.send_message(message.chat.id, "❌ Никнейм не может быть пустым! Попробуйте еще раз:")
            return
        
        match_bot.ticket_sessions[user_id] = {
            'step': 'waiting_complaint',
            'match_id': match_bot.ticket_sessions[user_id]['match_id'],
            'reported_nickname': reported_nickname
        }
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton('🔄 Отменить тикет', callback_data='cancel_ticket'))
        
        complaint_text = "📤 Опишите жалобу на игрока.\n\n"
        complaint_text += "⚠️ Желаю вам удачи, но советую объяснять все подробно."
        
        bot.send_message(message.chat.id, complaint_text, reply_markup=markup)

# ОБРАБОТЧИК ДЛЯ ВВОДА ЖАЛОБЫ
@bot.message_handler(func=lambda message: match_bot.ticket_sessions.get(message.from_user.id, {}).get('step') == 'waiting_complaint')
@safe_handler
def handle_ticket_complaint(message):
    user_id = message.from_user.id
    
    # Если пользователь ввел /start, отменяем текущее действие
    if message.text == '/start':
        if user_id in match_bot.ticket_sessions:
            del match_bot.ticket_sessions[user_id]
        show_main_menu(message.chat.id)
        return
    
    if user_id in match_bot.ticket_sessions and match_bot.ticket_sessions[user_id]['step'] == 'waiting_complaint':
        complaint_text = message.text.strip()
        
        if not complaint_text:
            bot.send_message(message.chat.id, "❌ Текст жалобы не может быть пустым! Попробуйте еще раз:")
            return
        
        match_id = match_bot.ticket_sessions[user_id]['match_id']
        reported_nickname = match_bot.ticket_sessions[user_id]['reported_nickname']
        
        # Создаем тикет в группе
        success, result_msg = match_bot.create_ticket_thread(user_id, match_id, reported_nickname, complaint_text)
        
        # Удаляем сессию тикета
        if user_id in match_bot.ticket_sessions:
            del match_bot.ticket_sessions[user_id]
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton('🏠 Главное меню', callback_data='main_menu'))
        
        bot.send_message(message.chat.id, result_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
@safe_handler
def main_menu_callback(call):
    show_main_menu(call.message.chat.id, call.message.message_id)

# ДОБАВЛЕННЫЕ ОБРАБОТЧИКИ ДЛЯ СОСТОЯНИЙ
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_new_nickname')
@safe_handler
def handle_new_nickname(message):
    user_id = message.from_user.id
    
    # Если пользователь ввел /start, отменяем текущее действие
    if message.text == '/start':
        user_states.pop(user_id, None)
        show_main_menu(message.chat.id)
        return
    
    if user_id in user_states and user_states[user_id] == 'waiting_new_nickname':
        new_nickname = message.text.strip()
        
        if not new_nickname:
            bot.send_message(message.chat.id, "❌ Никнейм не может быть пустым. Попробуйте еще раз:")
            return
        
        # Проверка никнейма - минимум 2 символа, без пробелов
        if len(new_nickname) < 2:
            bot.send_message(message.chat.id, "❌ Никнейм должен содержать минимум 2 символа! Попробуйте еще раз:")
            return
        
        # Проверка на пробелы в никнейме
        if ' ' in new_nickname:
            bot.send_message(message.chat.id, "❌ Никнейм не должен содержать пробелов! Используйте одно слово. Попробуйте еще раз:")
            return
        
        success, result_msg = match_bot.update_user_nickname(user_id, new_nickname)
        bot.send_message(message.chat.id, result_msg)
        
        user_states.pop(user_id, None)
        show_main_menu(message.chat.id)

# ОБНОВЛЕННЫЙ ОБРАБОТЧИК СКРИНШОТОВ (С ИЗМЕНЕННЫМ ТЕКСТОМ)
@bot.message_handler(content_types=['photo'])
@safe_handler
def handle_screenshot(message):
    user_id = message.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    photo_file_id = message.photo[-1].file_id
    
    success, result_msg = match_bot.forward_screenshot_to_match_thread(user_id, photo_file_id)
    
    if success:
        # ИЗМЕНЕННЫЙ ТЕКСТ ОТВЕТА
        bot.reply_to(message, "✅ Спасибо за результат игры. Ваш матч будет рассмотрен администрацией и засчитан.")
    else:
        bot.reply_to(message, result_msg)

# ОБНОВЛЕННЫЙ ОБРАБОТЧИК ОТПРАВКИ РЕЗУЛЬТАТОВ (ТОЛЬКО СКРИНШОТЫ)
@bot.callback_query_handler(func=lambda call: call.data == 'send_results')
@safe_handler
def send_results_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    results_text = "📊 ОТПРАВКА РЕЗУЛЬТАТОВ МАТЧА\n\n"
    results_text += "🔍 Отправка результата матча, на обработку администрации.\n"
    results_text += "🔥 Отправь скриншот результатов матча, который ты только что сыграл."
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton('🔙 Отмена', callback_data='main_menu'))
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text=results_text, 
            reply_markup=markup
        )
        if not success:
            bot.send_message(call.message.chat.id, results_text, reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, results_text, reply_markup=markup)

# АДМИНСКИЕ КОМАНДЫ
@bot.message_handler(commands=['emsg'])
@safe_handler
def admin_message_command(message):
    """Команда для ответа на тикеты (только для админов)"""
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав.")
        return
    
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "❌ Формат: /emsg user_id ваш_текст_ответа\nПример: /emsg 123456 Ваша проблема решена")
            return
        
        user_id = int(parts[1])
        admin_response = parts[2]
        
        success, result_msg = match_bot.send_ticket_response(user_id, admin_response)
        bot.reply_to(message, result_msg)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# УДАЛЕНА КОМАНДА /score - больше не требуется для команды /upd
@bot.message_handler(commands=['score'])
@safe_handler
def score_command(message):
    """Установка счета матча - доступна только в ветках матчей (для совместимости)"""
    try:
        # Проверяем, что команда вызвана в ветке форума
        if not hasattr(message, 'message_thread_id') or not message.message_thread_id:
            bot.reply_to(message, "❌ Эта команда доступна только в ветках матчей.")
            return
        
        # Проверяем права пользователя (только админы могут устанавливать счет)
        if message.from_user.id not in match_bot.admin_ids:
            bot.reply_to(message, "❌ У вас недостаточно прав для установки счета.")
            return
        
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ Формат: /score счет_CT счет_T\nПример: /score 13 12")
            return
        
        score_ct = int(parts[1])
        score_t = int(parts[2])
        
        # Устанавливаем счет для ветки
        thread_id = message.message_thread_id
        success, result_msg = match_bot.set_score_for_thread(thread_id, score_ct, score_t)
        bot.reply_to(message, result_msg)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# НОВАЯ КОМАНДА /upd - УНИВЕРСАЛЬНАЯ КОМАНДА ДЛЯ РЕГИСТРАЦИИ СТАТИСТИКИ
@bot.message_handler(commands=['upd'])
@safe_handler
def update_stats_command(message):
    """Универсальная команда для обновления статистики игрока (для всех админов)"""
    # Проверяем права пользователя
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав для использования этой команды.")
        return
    
    try:
        parts = message.text.split()
        
        if len(parts) == 6:
            _, user_id, kills, assists, deaths, result_type = parts
            
            if result_type.lower() not in ['win', 'loss']:
                bot.reply_to(message, "❌ Неверный тип результата. Используйте 'win' или 'loss'")
                return
            
            # Получаем ID матча из сообщения (если есть)
            match_id = None
            if message.reply_to_message and hasattr(message.reply_to_message, 'forum_topic_created') and message.reply_to_message.forum_topic_created:
                # Если ответ в ветке форума, берем ID из названия темы
                topic_name = message.reply_to_message.forum_topic_created.name
                match_id_match = re.search(r'#(\d+)', topic_name)
                if match_id_match:
                    match_id = match_id_match.group(1)
            
            # Получаем thread_id если есть
            thread_id = message.message_thread_id if hasattr(message, 'message_thread_id') and message.message_thread_id else None
            
            # Проверяем, не был ли уже зарегистрирован игрок в этой ветке
            if thread_id and match_bot.is_player_registered_in_thread(int(user_id), thread_id):
                bot.reply_to(message, f"⚠️ Вы уже зарегистрировали данного игрока.\n👮‍♀️ Откатить статистику /backupd")
                return
            
            result = match_bot.manual_register_stats(int(user_id), int(kills), int(assists), int(deaths), 0, result_type.lower(), match_id, thread_id)
            bot.reply_to(message, result)
            
        elif len(parts) == 3:
            _, user_id, elo_value = parts
            
            # Получаем thread_id если есть
            thread_id = message.message_thread_id if hasattr(message, 'message_thread_id') and message.message_thread_id else None
            
            # Проверяем, не был ли уже зарегистрирован игрок в этой ветке
            if thread_id and match_bot.is_player_registered_in_thread(int(user_id), thread_id):
                bot.reply_to(message, f"⚠️ Вы уже зарегистрировали данного игрока.\n👮‍♀️ Откатить статистику /backupd")
                return
            
            result = match_bot.manual_register_elo(int(user_id), int(elo_value), thread_id)
            bot.reply_to(message, result)
            
        else:
            help_text = "🔄 *КОМАНДА /upd*\n\n"
            help_text += "📝 Для регистрации матча:\n"
            help_text += "/upd user_id K A D win/loss\n\n"
            help_text += "📊 Для установки ELO:\n"
            help_text += "/upd user_id ELO\n\n"
            help_text += "📋 *Примеры использования:*\n"
            help_text += "• Зарегистрировать победу: `/upd 123456 15 8 5 win`\n"
            help_text += "• Зарегистрировать поражение: `/upd 123456 12 10 7 loss`\n"
            help_text += "• Установить ELO: `/upd 123456 250`\n\n"
            help_text += "💡 *Примечание:*\n"
            help_text += "- K: Убийства\n"
            help_text += "- A: Помощи\n"
            help_text += "- D: Смерти\n"
            help_text += "- win/loss: Результат матча"
            
            bot.reply_to(message, help_text, parse_mode='Markdown')
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['ban'])
@safe_handler
def ban_command(message):
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав.")
        return
    
    try:
        parts = message.text.split(maxsplit=3)
        if len(parts) < 3:
            bot.reply_to(message, "❌ Формат: /ban user_id причина [дни]\nПример: /ban 123456 спам 7\nПример для пермамента: /ban 123456 читы")
            return
        
        user_id = int(parts[1])
        reason = parts[2]
        duration_days = int(parts[3]) if len(parts) > 3 else None
        
        profile = match_bot.get_user_profile(user_id)
        if not profile:
            bot.reply_to(message, "❌ Пользователь не найден")
            return
        
        success, result_msg = match_bot.ban_user(user_id, reason, duration_days)
        if success:
            duration_text = f"на {duration_days} дней" if duration_days else "перманентно"
            bot.reply_to(message, f"✅ Пользователь {profile['nickname']} забанен {duration_text}\nПричина: {reason}")
            
            try:
                if duration_days:
                    ban_until = get_moscow_time() + timedelta(days=duration_days)
                    bot.send_message(user_id, f"🚫 ВЫ ПОЛУЧИЛИ БАН!\nПричина: {reason}\nДлительность: {duration_days} дней\nДо: {ban_until.strftime('%d.%m.%Y %H:%M')}")
                else:
                    bot.send_message(user_id, f"🚫 ВЫ ПОЛУЧИЛИ ПЕРМАНЕНТНЫЙ БАН!\nПричина: {reason}")
            except:
                pass
        else:
            bot.reply_to(message, result_msg)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['mute'])
@safe_handler
def mute_command(message):
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав.")
        return
    
    try:
        parts = message.text.split(maxsplit=3)
        if len(parts) < 3:
            bot.reply_to(message, "❌ Формат: /mute user_id причина [минуты]\nПример: /mute 123456 спам 60\nПример для пермамента: /mute 123456 оскорбления")
            return
        
        user_id = int(parts[1])
        reason = parts[2]
        duration_minutes = int(parts[3]) if len(parts) > 3 else None
        
        profile = match_bot.get_user_profile(user_id)
        if not profile:
            bot.reply_to(message, "❌ Пользователь не найден")
            return
        
        success, result_msg = match_bot.mute_user(user_id, reason, duration_minutes)
        if success:
            duration_text = f"на {duration_minutes} минут" if duration_minutes else "перманентно"
            bot.reply_to(message, f"✅ Пользователь {profile['nickname']} замучен {duration_text}\nПричина: {reason}")
            
            try:
                if duration_minutes:
                    mute_until = get_moscow_time() + timedelta(minutes=duration_minutes)
                    bot.send_message(user_id, f"🚫 ВЫ ПОЛУЧИЛИ МУТ!\nПричина: {reason}\nДлительность: {duration_minutes} минут\nДо: {mute_until.strftime('%d.%m.%Y %H:%M')}")
                else:
                    bot.send_message(user_id, f"🚫 ВЫ ПОЛУЧИЛИ ПЕРМАНЕНТНЫЙ МУТ!\nПричина: {reason}")
            except:
                pass
        else:
            bot.reply_to(message, result_msg)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['funmute'])
@safe_handler
def funmute_command(message):
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Формат: /funmute user_id\nПример: /funmute 123456")
            return
        
        user_id = int(parts[1])
        
        profile = match_bot.get_user_profile(user_id)
        if not profile:
            bot.reply_to(message, "❌ Пользователь не найден")
            return
        
        success = match_bot.unmute_user(user_id)
        if success:
            bot.reply_to(message, f"✅ Пользователь {profile['nickname']} размучен")
            
            try:
                bot.send_message(user_id, "✅ ВАС РАЗМУТИЛИ! Теперь вы можете играть снова.")
            except:
                pass
        else:
            bot.reply_to(message, "❌ Ошибка при размуте пользователя")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['funban'])
@safe_handler
def funban_command(message):
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Формат: /funban user_id\nПример: /funban 123456")
            return
        
        user_id = int(parts[1])
        
        profile = match_bot.get_user_profile(user_id)
        if not profile:
            bot.reply_to(message, "❌ Пользователь не найден")
            return
        
        success = match_bot.unban_user(user_id)
        if success:
            bot.reply_to(message, f"✅ Пользователь {profile['nickname']} разбанен")
            
            try:
                bot.send_message(user_id, "✅ ВАС РАЗБАНИЛИ! Теперь вы можете играть снова.")
            except:
                pass
        else:
            bot.reply_to(message, "❌ Ошибка при разбане пользователя")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# АДМИНСКИЕ КОМАНДЫ ДЛЯ ВАРНОВ
@bot.message_handler(commands=['warn'])
@safe_handler
def warn_command(message):
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав.")
        return
    
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "❌ Формат: /warn user_id причина\nПример: /warn 123456 спам в чате")
            return
        
        user_id = int(parts[1])
        reason = parts[2]
        
        profile = match_bot.get_user_profile(user_id)
        if not profile:
            bot.reply_to(message, "❌ Пользователь не найден")
            return
        
        warnings, result_msg = match_bot.add_warning_manual(user_id, reason)
        bot.reply_to(message, result_msg)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['unwarn'])
@safe_handler
def unwarn_command(message):
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Формат: /unwarn user_id\nПример: /unwarn 123456")
            return
        
        user_id = int(parts[1])
        
        profile = match_bot.get_user_profile(user_id)
        if not profile:
            bot.reply_to(message, "❌ Пользователь не найден")
            return
        
        warnings, result_msg = match_bot.remove_warning(user_id)
        bot.reply_to(message, result_msg)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['addwarn'])
@safe_handler
def addwarn_command(message):
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Формат: /addwarn user_id\nПример: /addwarn 123456")
            return
        
        user_id = int(parts[1])
        
        profile = match_bot.get_user_profile(user_id)
        if not profile:
            bot.reply_to(message, "❌ Пользователь не найден")
            return
        
        success, result_msg = match_bot.reset_warnings(user_id)
        bot.reply_to(message, result_msg)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# УДАЛЕНЫ КОМАНДЫ /adminreg и /noreg - больше не нужны

# НОВЫЕ КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ PRO LEAGUE
@bot.message_handler(commands=['proadd'])
@safe_handler
def proadd_command(message):
    """Добавляет пользователя в Pro League"""
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Формат: /proadd user_id\nПример: /proadd 123456")
            return
        
        user_id = int(parts[1])
        
        profile = match_bot.get_user_profile(user_id)
        if not profile:
            bot.reply_to(message, "❌ Пользователь не найден")
            return
        
        success, result_msg = match_bot.add_pro_league_user(user_id)
        bot.reply_to(message, result_msg)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['neproadd'])
@safe_handler
def neproadd_command(message):
    """Убирает пользователя из Pro League"""
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Формат: /neproadd user_id\nПример: /neproadd 123456")
            return
        
        user_id = int(parts[1])
        
        profile = match_bot.get_user_profile(user_id)
        if not profile:
            bot.reply_to(message, "❌ Пользователь не найден")
            return
        
        success, result_msg = match_bot.remove_pro_league_user(user_id)
        bot.reply_to(message, result_msg)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# УДАЛЕНА КОМАНДА /wreg - заменена на /upd

# НОВАЯ КОМАНДА /cancel - ОТМЕНА МАТЧА (для всех админов)
@bot.message_handler(commands=['cancel'])
@safe_handler
def cancel_match_command(message):
    """Отмена матча (для всех админов)"""
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав для использования этой команды.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Формат: /cancel номер_матча\nПример: /cancel 27")
            return
        
        match_id = int(parts[1])
        
        success, result_msg = match_bot.cancel_match(match_id, message.from_user.id)
        bot.reply_to(message, result_msg)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# НОВЫЕ КОМАНДЫ ДЛЯ АДМИНОВ - ОТКАТ СТАТИСТИКИ
@bot.message_handler(commands=['backupd'])
@safe_handler
def backupd_command(message):
    """Откат ELO и статистики для одного игрока (только для админов)"""
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Формат: /backupd user_id\nПример: /backupd 123456")
            return
        
        user_id = int(parts[1])
        
        # Проверяем, зарегистрирован ли игрок
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id, nickname FROM players WHERE user_id = ?', (user_id,))
        player_info = cursor.fetchone()
        
        if not player_info:
            bot.reply_to(message, "🔑 Вы еще не зарегистрировали данного игрока, это команда будет доступна после ручной регистрации.")
            conn.close()
            return
        
        user_id, nickname = player_info
        
        # Проверяем, не был ли уже откатан игрок в этой ветке
        thread_id = message.message_thread_id if hasattr(message, 'message_thread_id') and message.message_thread_id else None
        if thread_id and match_bot.is_player_rolled_back_in_thread(user_id, thread_id):
            bot.reply_to(message, "⚠️ Вы уже откатили статистику игроку!\n\nПеререгистрировать ELO воспользуйтесь /upd.")
            conn.close()
            return
        
        # Получаем последний матч игрока
        cursor.execute('''
            SELECT pm.id, pm.match_id, pm.kills, pm.assists, pm.deaths, pm.total_score, pm.elo_change, pm.result
            FROM player_matches pm
            WHERE pm.user_id = ?
            ORDER BY pm.created_at DESC
            LIMIT 1
        ''', (user_id,))
        
        last_match = cursor.fetchone()
        
        if not last_match:
            bot.reply_to(message, "🔑 Вы еще не зарегистрировали данного игрока, это команда будет доступна после ручной регистрации.")
            conn.close()
            return
        
        pm_id, match_id, kills, assists, deaths, total_score, elo_change, result = last_match
        
        # Откатываем статистику
        cursor.execute('''
            UPDATE players 
            SET kills = kills - ?, 
                assists = assists - ?, 
                deaths = deaths - ?, 
                total_score = total_score - ?,
                matches_played = matches_played - 1,
                elo = elo - ?,
                wins = wins - CASE WHEN ? = 'win' THEN 1 ELSE 0 END,
                losses = losses - CASE WHEN ? = 'loss' THEN 1 ELSE 0 END
            WHERE user_id = ?
        ''', (kills, assists, deaths, total_score, elo_change, result, result, user_id))
        
        # Удаляем запись о матче
        cursor.execute('DELETE FROM player_matches WHERE id = ?', (pm_id,))
        
        # Добавляем запись в историю ELO
        cursor.execute('''
            INSERT INTO elo_history (user_id, old_elo, new_elo, reason)
            SELECT ?, elo + ?, elo, 'backup_rollback'
            FROM players WHERE user_id = ?
        ''', (user_id, elo_change, user_id))
        
        conn.commit()
        conn.close()
        
        # Добавляем игрока в список откатанных в этой ветке
        if thread_id:
            match_bot.add_rolled_back_player_in_thread(user_id, thread_id)
        
        # Удаляем игрока из списка зарегистрированных, чтобы можно было заново зарегистрировать
        if thread_id and thread_id in match_bot.registered_players_in_thread:
            if user_id in match_bot.registered_players_in_thread[thread_id]:
                match_bot.registered_players_in_thread[thread_id].remove(user_id)
        
        bot.reply_to(message, f"✅ Статистика игрока {nickname} была успешно сбросана.\nТеперь вы можете снова зарегистрировать его статистику командой /upd.")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['backupdall'])
@safe_handler
def backupdall_command(message):
    """Откат ELO и статистики для всех игроков матча (только для админов)"""
    if message.from_user.id not in match_bot.admin_ids:
        bot.reply_to(message, "❌ У вас недостаточно прав.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Формат: /backupdall номер_матча\nПример: /backupdall 27")
            return
        
        match_id = int(parts[1])
        
        conn = sqlite3.connect('matchmaking.db', check_same_thread=False)
        cursor = conn.cursor()
        
        # Проверяем существование матча
        cursor.execute('SELECT id FROM matches WHERE id = ?', (match_id,))
        match_info = cursor.fetchone()
        
        if not match_info:
            bot.reply_to(message, "❌ Матч с таким номером не найден.")
            conn.close()
            return
        
        # Получаем всех игроков этого матча
        cursor.execute('''
            SELECT pm.user_id, pm.kills, pm.assists, pm.deaths, pm.total_score, pm.elo_change, pm.result, p.nickname
            FROM player_matches pm
            JOIN players p ON pm.user_id = p.user_id
            WHERE pm.match_id = ?
        ''', (match_id,))
        
        players = cursor.fetchall()
        
        if not players:
            bot.reply_to(message, "❌ В этом матче не найдено зарегистрированных игроков.")
            conn.close()
            return
        
        results = []
        for player in players:
            user_id, kills, assists, deaths, total_score, elo_change, result, nickname = player
            
            # Откатываем статистику для каждого игрока
            cursor.execute('''
                UPDATE players 
                SET kills = kills - ?, 
                    assists = assists - ?, 
                    deaths = deaths - ?, 
                    total_score = total_score - ?,
                    matches_played = matches_played - 1,
                    elo = elo - ?,
                    wins = wins - CASE WHEN ? = 'win' THEN 1 ELSE 0 END,
                    losses = losses - CASE WHEN ? = 'loss' THEN 1 ELSE 0 END
                WHERE user_id = ?
            ''', (kills, assists, deaths, total_score, elo_change, result, result, user_id))
            
            # Добавляем запись в историю ELO
            cursor.execute('''
                INSERT INTO elo_history (user_id, old_elo, new_elo, reason)
                SELECT ?, elo + ?, elo, 'backup_rollback_all'
                FROM players WHERE user_id = ?
            ''', (user_id, elo_change, user_id))
            
            results.append(f"✅ {nickname}: откат ELO {elo_change}")
        
        # Удаляем все записи о матче
        cursor.execute('DELETE FROM player_matches WHERE match_id = ?', (match_id,))
        
        conn.commit()
        conn.close()
        
        result_text = "📊 Откат статистики для всех игроков матча:\n\n" + "\n".join(results)
        bot.reply_to(message, result_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

# ХЕНДЛЕР ДЛЯ ИЗМЕНЕНИЯ НИКНЕЙМА
@bot.callback_query_handler(func=lambda call: call.data == 'change_nickname')
@safe_handler
def change_nickname_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    user_states[user_id] = 'waiting_new_nickname'
    
    change_text = "✏️ Изменение никнейма\n\n"
    change_text += "Введите новый никнейм (минимум 2 символа, без пробелов):"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='edit_profile'))
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text=change_text, 
            reply_markup=markup
        )
        if not success:
            bot.send_message(call.message.chat.id, change_text, reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, change_text, reply_markup=markup)

# ХЕНДЛЕР ДЛЯ ИЗМЕНЕНИЯ ИГРОВОГО ID
@bot.callback_query_handler(func=lambda call: call.data == 'change_game_id')
@safe_handler
def change_game_id_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    user_states[user_id] = 'waiting_new_game_id'
    
    change_text = "🆔 Изменение игрового ID\n\n"
    change_text += "Введите новый игровой ID (минимум 3 символа, можно буквы и цифры):"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='edit_profile'))
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text=change_text, 
            reply_markup=markup
        )
        if not success:
            bot.send_message(call.message.chat.id, change_text, reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, change_text, reply_markup=markup)

# ХЕНДЛЕР ДЛЯ МЕНЮ ПАТИ
@bot.callback_query_handler(func=lambda call: call.data == 'party_menu')
@safe_handler
def party_menu_callback(call):
    user_id = call.from_user.id
    
    is_banned, ban_until = match_bot.is_user_banned(user_id)
    if is_banned:
        if ban_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nБан до: {ban_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный бан")
        return
    
    is_muted, mute_until = match_bot.is_user_muted(user_id)
    if is_muted:
        if mute_until:
            bot.send_message(call.message.chat.id, f"🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nМут до: {mute_until.strftime('%d.%m.%Y %H:%M')}")
        else:
            bot.send_message(call.message.chat.id, "🚫 ТЫ НАРУШИЛ ПРАВИЛА ЖДИ ОКОНЧАНИЯ\nПерманентный мут")
        return
    
    party_info = match_bot.get_party_info(user_id)
    
    if party_info:
        # Пользователь уже в пати
        party_text = "👥 Ваша пати:\n\n"
        
        for member in party_info['members']:
            leader_marker = " 👑" if member['id'] == party_info['leader_id'] else ""
            party_text += f"{member['type']} {member['nickname']} {member['level_emoji']} {member['device_emoji']}{leader_marker}\n"
        
        party_text += f"\n👥 Размер: {len(party_info['members'])}/{party_info['max_size']}"
        
        markup = telebot.types.InlineKeyboardMarkup()
        
        # Если пользователь лидер, может приглашать
        if user_id == party_info['leader_id'] and len(party_info['members']) < party_info['max_size']:
            markup.row(telebot.types.InlineKeyboardButton('➕ Пригласить друга', callback_data='invite_friend'))
        
        markup.row(telebot.types.InlineKeyboardButton('🚪 Покинуть пати', callback_data='leave_party'))
        markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='main_menu'))
        
    else:
        # Пользователь не в пати
        party_text = "👥 Система пати\n\n"
        party_text += "Создайте пати чтобы играть с друзьями!\n"
        party_text += "Максимальный размер пати: 2 игрока"
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton('➕ Создать пати', callback_data='create_party'))
        markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='main_menu'))
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text=party_text, 
            reply_markup=markup
        )
        if not success:
            bot.send_message(call.message.chat.id, party_text, reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, party_text, reply_markup=markup)

# ХЕНДЛЕР ДЛЯ СОЗДАНИЯ ПАТИ
@bot.callback_query_handler(func=lambda call: call.data == 'create_party')
@safe_handler
def create_party_callback(call):
    user_id = call.from_user.id
    
    success, result_msg = match_bot.create_party(user_id)
    
    if success:
        bot.answer_callback_query(call.id, "✅ Пати создана!")
        party_menu_callback(call)
    else:
        bot.answer_callback_query(call.id, result_msg)

# ХЕНДЛЕР ДЛЯ ПРИГЛАШЕНИЯ ДРУГА
@bot.callback_query_handler(func=lambda call: call.data == 'invite_friend')
@safe_handler
def invite_friend_callback(call):
    user_id = call.from_user.id
    
    invite_text = "👥 Приглашение друга\n\n"
    invite_text += "Чтобы пригласить друга в пати, отправьте его Telegram ID.\n\n"
    invite_text += "💡 Как найти ID друга:\n"
    invite_text += "1. Попросите друга написать @userinfobot\n"
    invite_text += "2. Он получит свой ID\n"
    invite_text += "3. Отправьте его сюда"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(telebot.types.InlineKeyboardButton('🔙 Назад', callback_data='party_menu'))
    
    try:
        success = safe_edit_message(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id,
            text=invite_text, 
            reply_markup=markup
        )
        if not success:
            bot.send_message(call.message.chat.id, invite_text, reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения: {e}")
        bot.send_message(call.message.chat.id, invite_text, reply_markup=markup)
    
    user_states[user_id] = 'waiting_friend_id'

# ОБРАБОТЧИК ДЛЯ ВВОДА ID ДРУГА
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_friend_id')
@safe_handler
def handle_friend_id(message):
    user_id = message.from_user.id
    
    # Если пользователь ввел /start, отменяем текущее действие
    if message.text == '/start':
        user_states.pop(user_id, None)
        show_main_menu(message.chat.id)
        return
    
    try:
        friend_id = int(message.text.strip())
        
        success, result_msg = match_bot.invite_to_party(user_id, friend_id)
        bot.send_message(message.chat.id, result_msg)
        
        user_states.pop(user_id, None)
        
        if success:
            party_menu_callback_helper(message.chat.id)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат ID! ID должен содержать только цифры. Попробуйте еще раз:")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")
        user_states.pop(user_id, None)

def party_menu_callback_helper(chat_id):
    """Вспомогательная функция для отображения меню пати"""
    try:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton('👥 Пати', callback_data='party_menu'))
        bot.send_message(chat_id, "🔙 Возврат в меню пати...", reply_markup=markup)
    except:
        pass

# ХЕНДЛЕР ДЛЯ ПРИНЯТИЯ/ОТКЛОНЕНИЯ ПРИГЛАШЕНИЯ В ПАТИ
@bot.callback_query_handler(func=lambda call: call.data.startswith(('accept_party_', 'decline_party_')))
@safe_handler
def handle_party_invite_response(call):
    user_id = call.from_user.id
    
    try:
        action = call.data.split('_')[0]  # accept или decline
        leader_id = int(call.data.split('_')[2])
        
        if action == 'accept':
            success, result_msg = match_bot.accept_party_invite(user_id, leader_id)
        else:
            success, result_msg = match_bot.decline_party_invite(user_id, leader_id)
        
        if success:
            bot.answer_callback_query(call.id, result_msg)
            
            # Обновляем сообщение
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            
            if action == 'accept':
                party_menu_callback_helper(call.message.chat.id)
        else:
            bot.answer_callback_query(call.id, result_msg)
            
    except Exception as e:
        logging.error(f"Ошибка обработки приглашения в пати: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка при обработке приглашения")

# ХЕНДЛЕР ДЛЯ ВЫХОДА ИЗ ПАТИ
@bot.callback_query_handler(func=lambda call: call.data == 'leave_party')
@safe_handler
def leave_party_callback(call):
    user_id = call.from_user.id
    
    success, result_msg = match_bot.leave_party(user_id)
    
    if success:
        bot.answer_callback_query(call.id, "✅ Вы вышли из пати")
        party_menu_callback(call)
    else:
        bot.answer_callback_query(call.id, result_msg)

# ЗАПУСК БОТА
if __name__ == "__main__":
    logging.info("🚀 Запуск бота...")
    
    # Запускаем устойчивого бота
    polling_thread = threading.Thread(target=robust_bot.poll)
    polling_thread.daemon = True
    polling_thread.start()
    
    logging.info("✅ Бот запущен и готов к работе")
    
    # Бесконечный цикл для поддержания работы
    while True:
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            logging.info("🛑 Получен сигнал завершения, останавливаю бота...")
            robust_bot.stop()
            break