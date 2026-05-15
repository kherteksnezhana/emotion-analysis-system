
# clean_users.py
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database.database import get_db_connection, release_db_connection

def clean_all_test_users():
    print("Очистка тестовых пользователей...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Список пользователей для удаления
    test_users = [
        'voronov_m', 'kozlov_a', 'popova_e',
        'svetlova_e', 'morozova_a', 'novikova_yu',
        'petrov_d', 'volkov_s', 'lebedev_m',
        'sokolova_o', 'krylova_m', 'egorova_t',
        'smirnov_a', 'belova_e', 'sidorov_i', 'ivanova_m'
    ]
    
    # Удаляем связанные данные
    for username in test_users:
        # Получаем user_id
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        if row:
            user_id = row[0]
            print(f"  Удаляем пользователя {username} (ID: {user_id})")
            
            # Удаляем результаты анализов
            cursor.execute("""
                DELETE FROM analysis_results 
                WHERE report_id IN (SELECT id FROM reports WHERE user_id = %s)
            """, (user_id,))
            
            # Удаляем отчёты
            cursor.execute("DELETE FROM reports WHERE user_id = %s", (user_id,))
            
            # Удаляем сессии
            cursor.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
            
            # Удаляем пользователя
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    
    conn.commit()
    
    # Проверяем результат
    cursor.execute("SELECT username FROM users WHERE username IN %s", (tuple(test_users),))
    remaining = cursor.fetchall()
    
    cursor.close()
    release_db_connection(conn)
    
    if not remaining:
        print("\n✓ Все тестовые пользователи удалены!")
    else:
        print(f"\n⚠️ Остались: {remaining}")

if __name__ == "__main__":
    clean_all_test_users()