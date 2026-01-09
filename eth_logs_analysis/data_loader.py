# data_loader.py
import pandas as pd
import json
import os

def load_logs(file_path):
    """Загружает JSONL файл - ПРОСТОЙ И РАБОЧИЙ ВАРИАНТ"""
    print(f"📁 Загружаю файл: {file_path}")
    
    # Проверяем файл
    if not os.path.exists(file_path):
        print(f"❌ ОШИБКА: Файл не найден: {file_path}")
        return pd.DataFrame()
    
    # Читаем построчно
    records = []
    line_count = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_count += 1
            line = line.strip()
            
            if not line:  # Пропускаем пустые строки
                continue
                
            try:
                data = json.loads(line)
                records.append(data)
            except json.JSONDecodeError:
                print(f"⚠️  Строка {line_count}: некорректный JSON, пропускаю")
                continue
    
    if not records:
        print("❌ Файл пуст или все строки некорректны")
        return pd.DataFrame()
    
    # Создаем DataFrame
    df = pd.DataFrame(records)
    print(f"✅ Загружено {len(df)} записей")
    
    # Переименовываем timestamp если есть
    if 'timestamp' in df.columns:
        df = df.rename(columns={'timestamp': 'event_timestamp'})
        print(f"📅 Колонка timestamp переименована в event_timestamp")
    
    print(f"📊 Колонки в данных: {list(df.columns)}")
    return df


def expand_details_column(df):
    """Разбирает поле details - УПРОЩЕННАЯ ВЕРСИЯ"""
    if df.empty:
        return df
    
    if 'details' not in df.columns:
        print("ℹ️  Колонки details нет в данных")
        return df
    
    # Пробуем разобрать details
    try:
        details_list = []
        for details in df['details']:
            if isinstance(details, dict):
                details_list.append(details)
            else:
                details_list.append({})
        
        # Создаем DataFrame из details
        details_df = pd.DataFrame(details_list)
        
        # Добавляем префикс к колонкам
        details_df = details_df.add_prefix('details_')
        
        # Объединяем с основным DataFrame
        df = pd.concat([df.drop(columns=['details']), details_df], axis=1)
        print(f"✅ Развернуто поле details, добавлено {len(details_df.columns)} колонок")
        
    except Exception as e:
        print(f"⚠️  Не удалось развернуть details: {e}")
    
    return df