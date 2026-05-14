"""
Генератор реалистичных отчётов для системы анализа эмоций
Создаёт отчёты за последние 20 рабочих дней (без сб/вс)
Каждый отчёт: 60-300 символов, соответствует отделу сотрудника
Разные эмоциональные профили: выгорающие, позитивные, нейтральные, нестабильные
"""

import sys
import os
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database.database import init_db, add_user, save_report, save_analysis_result
from backend.model.emotion_model import analyze_emotion

PASSWORD = "1234"

# =====================================================
# ПОЛЬЗОВАТЕЛИ (12 сотрудников + руководители + HR)
# =====================================================

USERS = [
    # IT отдел (4 человека)
    ("Михаил Воронов", "voronov_m", "Сотрудник", "IT"),
    ("Артем Козлов", "kozlov_a", "Сотрудник", "IT"),
    ("Екатерина Попова", "popova_e", "Сотрудник", "IT"),
    ("Дмитрий Соболев", "sobolev_d", "Сотрудник", "IT"),
    
    # Маркетинг (3 человека)
    ("Елена Светлова", "svetlova_e", "Сотрудник", "Маркетинг"),
    ("Анна Морозова", "morozova_a", "Сотрудник", "Маркетинг"),
    ("Юлия Новикова", "novikova_yu", "Сотрудник", "Маркетинг"),
    
    # Продажи (3 человека)
    ("Дмитрий Петров", "petrov_d", "Сотрудник", "Продажи"),
    ("Сергей Волков", "volkov_s", "Сотрудник", "Продажи"),
    ("Максим Лебедев", "lebedev_m", "Сотрудник", "Продажи"),
    
    # Бухгалтерия (2 человека)
    ("Ольга Соколова", "sokolova_o", "Сотрудник", "Бухгалтерия"),
    ("Мария Крылова", "krylova_m", "Сотрудник", "Бухгалтерия"),
    
    # Руководители
    ("Алексей Смирнов", "smirnov_a", "Руководитель", "IT"),
    ("Елена Белова", "belova_e", "Руководитель", "Маркетинг"),
    ("Игорь Сидоров", "sidorov_i", "Руководитель", "Продажи"),
    
    # HR
    ("Марина Иванова", "ivanova_m", "HR-администратор", "HR"),
]

# =====================================================
# ЭМОЦИОНАЛЬНЫЕ ПРОФИЛИ СОТРУДНИКОВ
# =====================================================
# Каждый профиль определяет, какие эмоции будут в отчётах
# и как они меняются со временем

EMOTIONAL_PROFILES = {
    # Выгорающие (негативный тренд)
    "kozlov_a": {
        "type": "burnout",
        "trend": "negative",
        "description": "Выгорающий сотрудник - настроение падает к концу периода"
    },
    "popova_e": {
        "type": "burnout",
        "trend": "negative", 
        "description": "Эмоциональное выгорание, хочет уволиться"
    },
    "volkov_s": {
        "type": "burnout",
        "trend": "negative",
        "description": "На грани увольнения, постоянный негатив"
    },
    
    # Всегда на позитиве
    "lebedev_m": {
        "type": "always_positive",
        "trend": "stable",
        "description": "Звезда продаж, всегда в хорошем настроении"
    },
    "voronov_m": {
        "type": "always_positive",
        "trend": "stable",
        "description": "Стабильный позитивный сотрудник"
    },
    "novikova_yu": {
        "type": "always_positive",
        "trend": "stable",
        "description": "Энергичный новичок, всё нравится"
    },
    
    # Всегда нейтральные
    "sokolova_o": {
        "type": "always_neutral",
        "trend": "stable",
        "description": "Педантичный бухгалтер, без эмоций"
    },
    "morozova_a": {
        "type": "always_neutral",
        "trend": "stable",
        "description": "Спокойная, ответственная"
    },
    
    # Нестабильные (перепады настроения)
    "petrov_d": {
        "type": "unstable",
        "trend": "fluctuating",
        "description": "То взлёты, то падения в продажах"
    },
    "krylova_m": {
        "type": "unstable",
        "trend": "fluctuating",
        "description": "Уставший бухгалтер, но бывают хорошие дни"
    },
    "sobolev_d": {
        "type": "unstable",
        "trend": "fluctuating",
        "description": "Младший разработчик, пока не определился"
    },
    
    # Стабильные с редкими отклонениями
    "svetlova_e": {
        "type": "stable",
        "trend": "positive",
        "description": "В основном позитив, редко нейтраль"
    },
}

# =====================================================
# БИБЛИОТЕКИ ОТЧЁТОВ ПО ОТДЕЛАМ
# =====================================================

# Шаблоны для IT
IT_TASKS = [
    "разрабатывал новый функционал для модуля {module}",
    "исправлял баги в {module}",
    "проводил код-ревью пулл-реквестов",
    "оптимизировал запросы к базе данных",
    "настраивал CI/CD пайплайны",
    "писал юнит-тесты для {module}",
    "документировал API для {module}",
    "рефакторил легаси-код в {module}",
    "помогал стажёру разобраться с {tech}",
    "разбирался с {tech}",
    "дебажил проблему с {issue}",
    "настраивал мониторинг и алерты",
    "проводил нагрузочное тестирование",
    "мигрировал данные из старой системы",
    "настраивал Docker-контейнеры для {module}",
]

IT_MODULES = ["авторизации", "платежей", "отчётности", "API", "админки", "фронтенда", "бэкенда"]
IT_TECH = ["Docker", "Kubernetes", "FastAPI", "React", "PostgreSQL", "Redis", "Kafka", "gRPC"]
IT_ISSUES = ["падением производительности", "утечкой памяти", "некорректными данными", "таймаутами"]

# Шаблоны для Маркетинга
MARKETING_TASKS = [
    "запускал рекламную кампанию в {platform}",
    "анализировал эффективность каналов",
    "готовил контент для {channel}",
    "настраивал таргетинг на {audience}",
    "проводил A/B тесты креативов",
    "оптимизировал рекламные объявления",
    "составлял отчёт по {metric}",
    "общался с подрядчиками по {project}",
    "готовил презентацию для руководства",
    "проводил исследование аудитории",
    "настраивал CRM-систему",
    "запускал email-рассылку на {count} адресов",
]

MARKETING_PLATFORMS = ["Яндекс.Директ", "VK Рекламе", "Telegram Ads", "MyTarget"]
MARKETING_CHANNELS = ["Telegram-канал", "VK-паблик", "YouTube", "Instagram*", "Дзене"]
MARKETING_AUDIENCE = ["лиды", "теплая аудитория", "бывшие клиенты", "похожие сегменты"]
MARKETING_METRICS = ["CTR", "CPL", "ROI", "конверсии", "охвату"]
MARKETING_PROJECTS = ["дизайну", "видеопродакшну", "копирайтингу", "разработке сайта"]

# Шаблоны для Продаж
SALES_TASKS = [
    "провёл {count} встреч с клиентами",
    "сделал {count} холодных звонков",
    "готовил коммерческое предложение для {client}",
    "провёл презентацию продукта",
    "обрабатывал возражения клиента",
    "закрыл сделку на {amount}",
    "вёл переговоры по {deal}",
    "готовил договор для {client}",
    "участвовал в тендере",
    "проводил демо продукта",
    "отрабатывал базу отказников",
]

SALES_CLIENTS = ["крупного застройщика", "производственной компании", "IT-компании", "розничной сети", "дистрибьютора"]
SALES_DEALS = ["крупному контракту", "долгосрочному соглашению", "пилотному проекту"]
SALES_AMOUNTS = ["500 000 ₽", "1 200 000 ₽", "2 500 000 ₽", "5 000 000 ₽", "мелкую сделку"]

# Шаблоны для Бухгалтерии
ACCOUNTING_TASKS = [
    "занимался сверкой счетов с контрагентами",
    "готовил платёжные поручения",
    "составлял авансовые отчёты",
    "проверял первичную документацию",
    "работал с {doc}",
    "закрывал отчётный период",
    "готовил отчётность для налоговой",
    "отвечал на запросы ФНС",
    "проводил инвентаризацию",
    "начислял зарплату сотрудникам",
    "готовил справки по запросу",
]

ACCOUNTING_DOCS = ["счетами-фактурами", "актами выполненных работ", "накладными", "УПД"]

# =====================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ГЕНЕРАЦИИ ТЕКСТОВ
# =====================================================

def random_from_list(lst):
    return random.choice(lst)

def generate_report_for_it(emotional_state):
    """Генерирует отчёт для IT-сотрудника"""
    task = random_from_list(IT_TASKS)
    task = task.format(
        module=random_from_list(IT_MODULES),
        tech=random_from_list(IT_TECH),
        issue=random_from_list(IT_ISSUES)
    )
    
    if emotional_state == "positive":
        templates = [
            f"Отличный день! {task}. Всё получилось гладко, доволен результатом. Команда отлично сработала, спасибо коллегам за помощь. Чувствую удовлетворение от проделанной работы.",
            f"Сегодня продуктивно поработал: {task}. Задачу закрыл раньше срока, успел ещё помочь коллеге с его задачей. Настроение бодрое, готов к новым вызовам.",
            f"Хороший день. {task}. Технологии работают как часы, багов не нашёл. Документацию подтянул, код стал чище. Завтра планирую заняться следующим модулем.",
        ]
    elif emotional_state == "negative":
        templates = [
            f"Ужасный день. {task}. Всё валится из рук, ничего не работает. Чувствую, что выгораю на этой работе. Постоянные дедлайны и срочные задачи выматывают. Нет сил совсем.",
            f"Не могу больше. {task}. Опять правки от заказчика в третий раз. Кажется, они сами не знают, чего хотят. Безысходность какая-то. Думаю об увольнении.",
            f"Сил нет. {task}. Сломался пайплайн, потратил полдня на дебаг чужого кода. Свои задачи даже не начинал. Руководитель недоволен, а я не справляюсь.",
        ]
    else:  # neutral
        templates = [
            f"Обычный рабочий день. {task}. Работал в штатном режиме, без авралов. Задачи выполнил в срок, но ничего выдающегося. Завтра продолжу.",
            f"Спокойно поработал. {task}. Плановые задачи закрыл, с коллегами обсудил следующие шаги. В целом день прошёл продуктивно, без происшествий.",
            f"Ничего особенного. {task}. Сделал то, что планировал. К вечеру немного устал, но в целом нормально. Завтра займусь следующим спринтом.",
        ]
    return random_from_list(templates)

def generate_report_for_marketing(emotional_state):
    """Генерирует отчёт для маркетолога"""
    task = random_from_list(MARKETING_TASKS)
    task = task.format(
        platform=random_from_list(MARKETING_PLATFORMS),
        channel=random_from_list(MARKETING_CHANNELS),
        audience=random_from_list(MARKETING_AUDIENCE),
        metric=random_from_list(MARKETING_METRICS),
        project=random_from_list(MARKETING_PROJECTS),
        count=random.randint(5000, 50000)
    )
    
    if emotional_state == "positive":
        templates = [
            f"Отличные результаты! {task}. CTR вырос на 15%, ROI показывает положительную динамику. Команда сработала отлично, все довольны. Особенно радует, что клиенты положительно отреагировали на новый креатив.",
            f"Успешный день! {task}. Перевыполнила план по лидам, получила хорошие отзывы от руководства. Запустили новую кампанию - охват уже 50 тысяч. Очень вдохновляет!",
            f"Замечательный день! {task}. Всё получилось даже лучше, чем ожидала. Коллеги помогли с дизайном, подрядчики не подвели. Настроение отличное, люблю свою работу!",
        ]
    elif emotional_state == "negative":
        templates = [
            f"Провальный день. {task}. Ничего не получается, кампании не работают, бюджет слит. Клиенты недовольны, руководитель давит. Чувствую, что выгораю на этой работе.",
            f"Ужасно. {task}. Опять правки от заказчика в десятый раз. Бесполезная трата времени. Подрядчики сорвали дедлайн, пришлось всё переделывать самой. Ситуация безнадёжная.",
            f"Сил нет. {task}. Весь день в переписках и согласованиях, никакого креатива. Устала морально, ничего не хочется делать. Думаю о смене работы, надоело это всё.",
        ]
    else:
        templates = [
            f"Обычный день. {task}. Плановые задачи выполнила. Ничего особенного, рутина. Работа как работа, без эмоций. Завтра продолжу в том же духе.",
            f"Спокойно поработала. {task}. Всё по плану, без срывов. Согласовали бюджет на следующий месяц. День прошёл продуктивно, но ничего выдающегося.",
            f"Ничего особенного. {task}. Сделала текущие задачи, ответила на письма. К вечеру устала, но в целом нормально. Завтра займусь новым проектом.",
        ]
    return random_from_list(templates)

def generate_report_for_sales(emotional_state):
    """Генерирует отчёт для продажника"""
    task = random_from_list(SALES_TASKS)
    task = task.format(
        count=random.randint(5, 30),
        client=random_from_list(SALES_CLIENTS),
        amount=random_from_list(SALES_AMOUNTS),
        deal=random_from_list(SALES_DEALS)
    )
    
    if emotional_state == "positive":
        templates = [
            f"Отличный день в продажах! {task}. Клиенты довольны, сделки закрываются. Перевыполнил план на 20%. Настроение бодрое, чувствую прилив энергии. Премия будет хорошей!",
            f"Замечательный день! {task}. Закрыл крупную сделку, клиент подписал договор. Команда поддержала, руководитель похвалил. Лучший день за эту неделю!",
            f"Прорыв! {task}. Наконец-то дозвонился до ЛПР в крупной компании, назначили встречу. Чувствую, что месяц будет успешным. Горжусь собой!",
        ]
    elif emotional_state == "negative":
        templates = [
            f"Провальный день. {task}. План опять не выполнен, клиенты отказываются, руководитель давит. Нет сил совсем, выгораю на этой работе. Думаю об увольнении.",
            f"Ужасно. {task}. Клиент ушёл к конкурентам на последней минуте. Потратил две недели - и всё зря. Безысходность какая-то. Не понимаю, зачем всё это.",
            f"Сил нет. {task}. Постоянные отказы, холодные звонки без результата. Не выспался, работать не могу. Чувствую себя никчемным. Похоже, продажи не моё.",
        ]
    else:
        templates = [
            f"Обычный день в продажах. {task}. План выполнил на 70%, ничего особенного. Клиенты есть, но крупных сделок не было. Спокойно, без эмоций.",
            f"Нормально поработал. {task}. Несколько встреч, пара предоплат. Ничего выдающегося, но и провалов нет. Работа как работа.",
            f"Средний день. {task}. Сделал плановые звонки, пару назначенных встреч. К вечеру устал, но результат есть. Завтра продолжу.",
        ]
    return random_from_list(templates)

def generate_report_for_accounting(emotional_state):
    """Генерирует отчёт для бухгалтера"""
    task = random_from_list(ACCOUNTING_TASKS)
    task = task.format(doc=random_from_list(ACCOUNTING_DOCS))
    
    if emotional_state == "positive":
        templates = [
            f"Хороший день! {task}. Всё сошлось, ошибок не нашла. Закрыла месяц без проблем. Довольна результатом, можно выдохнуть.",
            f"Отлично поработала! {task}. Сдала отчётность раньше срока, налоговая приняла без замечаний. Коллеги помогли, за что им спасибо.",
            f"Продуктивный день! {task}. Разобрала завалы, систематизировала документы. Теперь порядок. Настроение хорошее, работа спорится.",
        ]
    elif emotional_state == "negative":
        templates = [
            f"Кошмарный день. {task}. Опять правки от налоговой в третий раз. Бесконечные отчёты выматывают. Глаза слипаются, сил нет. Выгораю на этой работе.",
            f"Ужасно. {task}. Обнаружила ошибку в отчёте за прошлый квартал. Теперь переделывать всё заново. Страшно идти к начальнику. Безысходность.",
            f"Сил нет. {task}. Опять аврал перед отчётностью. Сижу до ночи, не успеваю. Устала как собака. Хочу в отпуск, но не дают.",
        ]
    else:
        templates = [
            f"Обычный день. {task}. Рутина, сверки, платежки. Всё по плану, без происшествий. К вечеру устала, но в целом нормально.",
            f"Спокойно поработала. {task}. Плановые задачи выполнила. Ничего особенного. День прошёл незаметно.",
            f"Ничего особенного. {task}. Сделала текучку, ответила на запросы. Всё в штатном режиме. Завтра продолжу.",
        ]
    return random_from_list(templates)

# =====================================================
# ГЕНЕРАТОР ЭМОЦИОНАЛЬНОГО СОСТОЯНИЯ ПО ПРОФИЛЮ
# =====================================================

def get_emotional_state(profile_type, day_index, total_days=20):
    """
    Возвращает эмоциональное состояние для конкретного дня
    day_index: от 0 (первый день) до total_days-1 (последний день)
    """
    if profile_type == "always_positive":
        return "positive"
    
    elif profile_type == "always_neutral":
        return "neutral"
    
    elif profile_type == "burnout":
        # Негативный тренд: позитив в начале, негатив в конце
        if day_index < 5:
            return "positive"
        elif day_index < 10:
            return random.choice(["neutral", "neutral", "negative"])
        else:
            return "negative"
    
    elif profile_type == "unstable":
        # Случайные перепады
        rand = random.random()
        if rand < 0.4:
            return "positive"
        elif rand < 0.7:
            return "neutral"
        else:
            return "negative"
    
    elif profile_type == "stable":
        # В основном позитив, редко нейтраль
        if random.random() < 0.8:
            return "positive"
        else:
            return "neutral"
    
    else:
        # Дефолтный профиль: смешанный
        rand = random.random()
        if rand < 0.4:
            return "positive"
        elif rand < 0.7:
            return "neutral"
        else:
            return "negative"

# =====================================================
# ОСНОВНЫЕ ФУНКЦИИ
# =====================================================

def get_last_working_days(count=20):
    """Возвращает список последних count рабочих дней"""
    working_days = []
    current_date = datetime.now().replace(hour=15, minute=30, second=0) - timedelta(days=1)
    
    while len(working_days) < count:
        if current_date.weekday() not in [5, 6]:  # не сб и не вс
            working_days.append(current_date)
        current_date -= timedelta(days=1)
    
    working_days.reverse()
    return working_days

def create_users():
    """Создаёт всех пользователей"""
    print("Инициализация базы данных...")
    init_db()
    
    print("\nСоздание пользователей...")
    created = []
    for full_name, username, role, department in USERS:
        user_id = add_user(full_name, username, PASSWORD, role, department)
        if user_id:
            print(f"  ✓ {username} ({role}, {department})")
            created.append(username)
        else:
            print(f"  ✗ {username} - уже существует")
    return created

def clean_existing_reports(username):
    """Удаляет старые отчёты пользователя"""
    from backend.database.database import get_db_connection, release_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()
    
    if row:
        user_id = row[0]
        cursor.execute("DELETE FROM analysis_results WHERE report_id IN (SELECT id FROM reports WHERE user_id = %s)", (user_id,))
        cursor.execute("DELETE FROM reports WHERE user_id = %s", (user_id,))
        conn.commit()
    
    cursor.close()
    release_db_connection(conn)

def update_report_date(report_id, new_date):
    """Обновляет дату отчёта"""
    from backend.database.database import get_db_connection, release_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE reports SET timestamp = %s WHERE id = %s", (new_date, report_id))
    cursor.execute("UPDATE analysis_results SET timestamp = %s WHERE report_id = %s", (new_date, report_id))
    conn.commit()
    
    cursor.close()
    release_db_connection(conn)

def generate_reports():
    """Генерирует отчёты для всех сотрудников"""
    print("\n" + "=" * 50)
    print("Генерация отчётов для сотрудников")
    print("=" * 50)
    
    working_dates = get_last_working_days(20)
    print(f"\n📅 Даты отчётов (последние {len(working_dates)} рабочих дней):")
    for d in working_dates:
        weekday = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][d.weekday()]
        print(f"    {d.strftime('%d.%m.%Y')} ({weekday})")
    
    from backend.database.database import get_db_connection, release_db_connection
    
    # Профили для сотрудников, у которых нет специального профиля
    default_profiles = {
        "svetlova_e": "stable",
        "morozova_a": "always_neutral",
        "novikova_yu": "always_positive",
        "petrov_d": "unstable",
        "volkov_s": "burnout",
        "lebedev_m": "always_positive",
        "sokolova_o": "always_neutral",
        "krylova_m": "unstable",
        "voronov_m": "always_positive",
        "kozlov_a": "burnout",
        "popova_e": "burnout",
        "sobolev_d": "unstable",
    }
    
    for username, scenario in EMOTIONAL_PROFILES.items():
        # Пропускаем, если пользователя нет в списке USERS (но он должен быть)
        if username not in [u[1] for u in USERS]:
            continue
            
        print(f"\n📋 {scenario['description']} - {username}")
        
        clean_existing_reports(username)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, department FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        cursor.close()
        release_db_connection(conn)
        
        if not row:
            print(f"  ✗ Пользователь {username} не найден!")
            continue
        
        user_id = row[0]
        department = row[1]
        profile_type = scenario["type"]
        report_ids = []
        
        # Генерируем 20 отчётов
        for day_idx in range(20):
            if day_idx >= len(working_dates):
                break
            
            # Получаем эмоциональное состояние для этого дня
            emotion_state = get_emotional_state(profile_type, day_idx, 20)
            
            # Генерируем текст отчёта в зависимости от отдела
            if department == "IT":
                text = generate_report_for_it(emotion_state)
            elif department == "Маркетинг":
                text = generate_report_for_marketing(emotion_state)
            elif department == "Продажи":
                text = generate_report_for_sales(emotion_state)
            elif department == "Бухгалтерия":
                text = generate_report_for_accounting(emotion_state)
            else:
                text = "Обычный рабочий день. Выполнил плановые задачи."
            
            # Проверяем длину текста (60-300 символов)
            while len(text) < 60:
                text += " Работа продолжается."
            if len(text) > 300:
                text = text[:297] + "..."
            
            # Сохраняем отчёт
            report_id = save_report(user_id, text)
            if report_id:
                report_ids.append(report_id)
                analysis = analyze_emotion(text)
                
                save_analysis_result(
                    report_id,
                    analysis["display_label"],
                    analysis["score"],
                    analysis["burnout_index"],
                    str(analysis["all_scores"])
                )
        
        # Обновляем даты
        for i, report_id in enumerate(report_ids):
            if i < len(working_dates):
                report_date = working_dates[i]
                update_report_date(report_id, report_date)
                
                # Получаем эмоцию для вывода
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT emotion_label FROM analysis_results WHERE report_id = %s", (report_id,))
                emotion_row = cursor.fetchone()
                cursor.close()
                release_db_connection(conn)
                
                emotion = emotion_row[0] if emotion_row else "unknown"
                emotion_icon = "😊" if "положительное" in emotion.lower() else ("😐" if "нейтральное" in emotion.lower() else "😞")
                print(f"    [{i+1:2d}] {report_date.strftime('%d.%m.%Y')} {emotion_icon} {emotion}")
        
        print(f"    ✓ Создано {len(report_ids)} отчётов")

def main():
    print("=" * 50)
    print("Генерация реалистичных отчётов для Emotion Analysis System")
    print("=" * 50)
    
    create_users()
    generate_reports()
    
    print("\n" + "=" * 50)
    print("ГОТОВО!")
    print("=" * 50)
    print("\n📋 Данные для входа (пароль для всех: 1234):")
    print("-" * 40)
    for full_name, username, role, department in USERS:
        print(f"  • {username} - {role}, {department}")
    
    print("\n💡 Запустите сервер: python -m uvicorn backend.main:app --reload")

if __name__ == "__main__":
    main()