"""
Скрипт для подготовки данных для дообучения модели
Метки: 1 - позитивный, 0 - нейтральный, -1 - негативный
"""

import sys
import os
import csv
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database.database import get_db_connection, release_db_connection

def export_reports_for_labeling():
    """Экспортирует отчёты в CSV для ручной разметки"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Получаем все отчёты с текущими метками модели
    cursor.execute("""
        SELECT r.id, r.text, ar.emotion_label, ar.confidence, u.username, u.department
        FROM reports r
        JOIN analysis_results ar ON r.id = ar.report_id
        JOIN users u ON r.user_id = u.id
        WHERE u.role = 'Сотрудник'
        ORDER BY r.timestamp DESC
    """)
    
    reports = cursor.fetchall()
    cursor.close()
    release_db_connection(conn)
    
    # Сохраняем в CSV для ручной разметки
    output_file = f'training_data_to_label_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(['id', 'text', 'current_label', 'confidence', 'username', 'department', 'correct_label'])
        writer.writerow(['', '', '', '', '', '', 'Поставьте: 1 (позитив) / 0 (нейтраль) / -1 (негатив)'])
        writer.writerow(['', '', '', '', '', '', '==================================================='])
        
        for report in reports:
            writer.writerow([
                report[0], 
                report[1].replace('\n', ' ').replace('\r', ' '), 
                report[2], 
                round(report[3], 2),
                report[4],
                report[5],
                ''  # Поле для правильной метки (1, 0, или -1)
            ])
    
    print(f"✅ Экспортировано {len(reports)} отчётов в файл: {output_file}")
    print("\n📝 Инструкция по разметке:")
    print("   1. Откройте файл в Excel или любом редакторе CSV")
    print("   2. В колонку 'correct_label' поставьте цифру:")
    print("      - 1  → если текст позитивный (радость, удовлетворение, успех)")
    print("      - 0  → если текст нейтральный (факты, без эмоций)")
    print("      - -1 → если текст негативный (усталость, раздражение, проблемы)")
    print("   3. Для сложных случаев можно оставить пустым")
    print("   4. Сохраните файл")
    print(f"\n   5. Затем запустите: python train_model.py --data {output_file}")

if __name__ == "__main__":
    export_reports_for_labeling()