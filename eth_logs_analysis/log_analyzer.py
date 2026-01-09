# eth_logs_analysis/log_analyzer.py
#!/usr/bin/env python3
"""
Главный модуль анализатора логов Ethereum P2P сети.
"""

import sys
import os
import json
import warnings
warnings.filterwarnings('ignore')

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импорт конфигурации - ИЗМЕНЕНО
from config import setup_config

# Импорт собственных модулей
from data_loader import load_logs, expand_details_column
from analyzer import (
    analyze_basic_stats,
    analyze_event_type_distribution,
    analyze_client_distribution,
    analyze_peer_activity,
    analyze_peer_activity_by_category,
    analyze_disconnections,
    analyze_validator_events_detailed,
    link_validator_events,
     analyze_protocol_messages,        
    identify_validators,              
    analyze_connection_limits,
    analyze_connection_quality,
    analyze_temporal_patterns,
            
)
from visualizer import (
    setup_visuals,
    plot_event_type_barchart,
    plot_peer_activity_treemap,
    plot_timeline_of_events,
    plot_peer_categories_barchart,
)

def main():
    """Главная функция, которая выполняет весь пайплайн анализа."""
    
    # --- ИНИЦИАЛИЗАЦИЯ КОНФИГА ---
    CONFIG = setup_config()
    
    print("=" * 60)
    print("ЗАПУСК АНАЛИЗА ЛОГОВ ETHEREUM P2P СЕТИ")
    print("=" * 60)

    # --- 1. ЗАГРУЗКА ДАННЫХ ---
    print("\n1. ЗАГРУЗКА ДАННЫХ...")
    
    # Вариант 1: Используйте путь из конфига
    df = load_logs(CONFIG['LOG_FILE_PATH'])
    
    # Вариант 2: Если не работает, раскомментируйте эту строку и укажите путь прямо:
    # df = load_logs("p2p-2026-01-07.jsonl")
    
    if df.empty:
        print("❌ Нет данных для анализа!")
        return
    
    df = expand_details_column(df)
    print(f"   Загружено {len(df)} записей, колонок: {len(df.columns)}")
    
    # --- 2. БАЗОВЫЙ АНАЛИЗ ---
    print("\n2. БАЗОВЫЙ АНАЛИЗ...")
    
    # 2.1 Основная статистика
    stats = analyze_basic_stats(df)
    print(f"   * Всего записей: {stats['total_entries']}")
    print(f"   * Уникальных пиров: {stats['unique_peers']}")
    print(f"   * Уникальных типов событий: {stats['unique_event_types']}")
    print(f"   * Временной диапазон: {stats['time_range']}")
    
    # 2.2 Распределение типов событий
    event_dist = analyze_event_type_distribution(df)
    print(f"   * Распределение событий: {len(event_dist)} типов")
    
    # 2.3 Клиенты в сети
    client_dist = analyze_client_distribution(df)
    print(f"   * Обнаружено клиентов: {len(client_dist)}")
    if client_dist:
        print(f"     {', '.join([f'{k}: {v}' for k, v in client_dist.items()])}")
    
    # --- 3. УГЛУБЛЕННЫЙ АНАЛИЗ ПИРОВ ---
    print("\n3. УГЛУБЛЕННЫЙ АНАЛИЗ АКТИВНОСТИ ПИРОВ...")
    
    # 3.1 Общая активность
    top_peers = analyze_peer_activity(df, top_n=CONFIG['TOP_PEERS_TO_ANALYZE'])
    print(f"   * Топ-{CONFIG['TOP_PEERS_TO_ANALYZE']} активных пиров")
    
    # 3.2 Анализ по категориям
    peer_categories = analyze_peer_activity_by_category(df, top_n=CONFIG['TOP_PEERS_TO_ANALYZE'])
    print(f"   * Анализ по категориям: {len(peer_categories)} пиров")
    
    # --- 4. ВИЗУАЛИЗАЦИЯ ---
    print("\n4. ПОСТРОЕНИЕ ГРАФИКОВ...")
    setup_visuals(style=CONFIG['PLOT_STYLE'], palette=CONFIG['COLOR_PALETTE'])
    
    # 4.1 График распределения типов событий
    plot_event_type_barchart(
        event_dist,
        save_path=CONFIG['OUTPUT_PATH'] / 'event_type_distribution.png'
    )
    
    # 4.2 Treemap активности пиров
    print("\n   Построение интерактивной карты активности...")
    plot_peer_activity_treemap(
        top_peers,
        save_path_html=CONFIG['OUTPUT_PATH'] / 'peer_activity_treemap.html'
    )
    
    # 4.3 Группированный график по категориям
    print("\n   Построение группированного графика по категориям...")
    if peer_categories:
        plot_peer_categories_barchart(
            peer_categories,
            save_path=CONFIG['OUTPUT_PATH'] / 'peer_categories_analysis.png'
        )
    
    # 4.4 Временная шкала событий
    print("\n   Построение временной шкалы...")
    plot_timeline_of_events(
        df,
        time_column='event_timestamp',
        save_path=CONFIG['OUTPUT_PATH'] / 'event_timeline.png'
    )
    
        # --- 5. ДОПОЛНИТЕЛЬНЫЙ АНАЛИЗ ---
    print("\n5. ДОПОЛНИТЕЛЬНЫЙ АНАЛИЗ ДЛЯ ИССЛЕДОВАНИЯ...")
    
    # 5.0 НОВЫЙ: Анализ протоколов
    print("\n   [НОВЫЙ] Анализ сообщений по протоколам...")
    analyze_protocol_messages(df)
    
    # 5.1 НОВЫЙ: Идентификация валидаторов
    print("\n   [НОВЫЙ] Попытка идентифицировать валидаторов...")
    identify_validators(df)
    
    # 5.2 НОВЫЙ: Анализ лимитов подключений
    print("\n   [НОВЫЙ] Детальный анализ лимитов подключений...")
    analyze_connection_limits(df)
    
    # 5.3 Старый код: Анализ валидаторской активности
    print("\n   * Обработка валидаторских событий...")
    try:
        df = link_validator_events(df)
        print("   * Анализ валидаторских сообщений...")
        validator_events = df[df['type'] == 'BEACON_AGGREGATE_AND_PROOF_RECEIVED']
        print(f"     - Агрегатов получено: {len(validator_events)}")
        analyze_validator_events_detailed(df)
    except Exception as e:
        print(f"   ⚠️  Ошибка в анализе валидаторов: {e}")
    
    # 5.4 Старый код: Анализ причин отключений
    print("\n   * Анализ отключений пиров...")
    goodbye_events = df[df['type'] == 'PEER_GOODBYE_RECEIVED']
    if len(goodbye_events) > 0:
        print(f"     - Отключений: {len(goodbye_events)}")
        analyze_disconnections(df, mode='detailed', max_top_clients=10, include_temporal=True)
    
    # --- 6. СОХРАНЕНИЕ РЕЗУЛЬТАТОВ ---
    print("\n6. СОХРАНЕНИЕ РЕЗУЛЬТАТОВ...")
    
    # 6.1 Основные данные
    csv_save_path = CONFIG['OUTPUT_PATH'] / 'processed_logs.csv'
    try:
        # Сохраняем ключевые колонки
        cols_to_save = ['event_timestamp', 'type', 'peer']
        details_cols = [c for c in df.columns if c.startswith('details_')]
        cols_to_save.extend(details_cols[:20])  # Первые 20 колонок из details
        
        existing_cols = [c for c in cols_to_save if c in df.columns]
        df[existing_cols].to_csv(csv_save_path, index=False, encoding='utf-8')
        print(f"   * Данные сохранены: {csv_save_path}")
        if os.path.exists(csv_save_path):
            size_mb = os.path.getsize(csv_save_path) / 1024 / 1024
            print(f"   * Размер: {size_mb:.2f} MB")
    except Exception as e:
        print(f"   ⚠️ Не удалось сохранить CSV: {e}")
    
    # 6.2 Результаты анализа
    try:
        results_path = CONFIG['OUTPUT_PATH'] / 'analysis_results.json'
        
        results = {
            'basic_stats': stats,
            'top_peers': {k: v for k, v in list(top_peers.items())[:10]},
            'client_distribution': client_dist,
            'event_types_count': len(event_dist),
            'peer_disconnections': len(goodbye_events) if 'goodbye_events' in locals() else 0
        }
        
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"   * Результаты анализа: {results_path}")
    except Exception as e:
        print(f"   ⚠️ Не удалось сохранить JSON: {e}")
        
        
          # --- 7. ЭКСПОРТ ДЛЯ ИССЛЕДОВАНИЯ ---
    print("\n7. ЭКСПОРТ ДАННЫХ ДЛЯ ГЛУБОКОГО АНАЛИЗА...")
    
    # Экспорт валидаторских событий
    validator_df = df[df['type'].str.contains('VALIDATOR|AGGREGATE')]
    if len(validator_df) > 0:
        validator_path = CONFIG['OUTPUT_PATH'] / 'validator_events.csv'
        validator_df.to_csv(validator_path, index=False)
        print(f"   * Валидаторские события: {validator_path}")
    
    # Экспорт отключений
    goodbye_df = df[df['type'] == 'PEER_GOODBYE_RECEIVED']
    if len(goodbye_df) > 0:
        goodbye_path = CONFIG['OUTPUT_PATH'] / 'goodbye_events.csv'
        goodbye_df.to_csv(goodbye_path, index=False)
        print(f"   * События отключения: {goodbye_path}")
    
    # Экспорт discovery событий
    discovery_df = df[df['type'].str.contains('DIAL|DISCOVERY')]
    if len(discovery_df) > 0:
        discovery_path = CONFIG['OUTPUT_PATH'] / 'discovery_events.csv'
        discovery_df.to_csv(discovery_path, index=False)
        print(f"   * Discovery события: {discovery_path}")  
    
    # --- 8. ИТОГИ ---
    print("\n" + "=" * 60)
    print("АНАЛИЗ ЗАВЕРШЕН!")
    print("=" * 60)
    
    print(f"\n📂 Результаты в папке: {CONFIG['OUTPUT_PATH']}")

if __name__ == "__main__":
    main()