# 📁 config.py

import argparse
from pathlib import Path
import sys

def setup_config():
    """Настройка конфигурации с аргументами командной строки."""
    
    # 1. Парсим аргументы
    parser = argparse.ArgumentParser(
        description='Анализатор логов Ethereum P2P сети',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s logs/mylog.jsonl                    # Анализ конкретного файла
  %(prog)s --top-peers 20 --output my_results  # Свои настройки
  %(prog)s --help                              # Справка
        """
    )
    
    # 2. Добавляем аргументы
    parser.add_argument(
        'log_file',
        type=str,
        help='Путь к лог-файлу (обязательный)'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='output',
        help='Папка для результатов (по умолчанию: output)'
    )
    
    parser.add_argument(
        '--top-peers', '-t',
        type=int,
        default=15,
        help='Сколько топ-пиров анализировать (по умолчанию: 15)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Подробный вывод (debug режим)'
    )
    
    # 3. Парсим аргументы
    args = parser.parse_args()
    
    # 4. Создаем конфигурацию
    config = {
        'LOG_FILE_PATH': Path(args.log_file),
        'OUTPUT_PATH': Path(args.output),
        'TOP_PEERS_TO_ANALYZE': args.top_peers,
        'VERBOSE': args.verbose,
        'PROJECT_ROOT': Path(__file__).parent,
        
        # Настройки графиков (оставляем как есть)
        'PLOT_STYLE': 'darkgrid',
        'COLOR_PALETTE': 'viridis'
    }
    
    # 5. Проверяем существование файла
    if not config['LOG_FILE_PATH'].exists():
        print(f"❌ ОШИБКА: Файл не найден: {config['LOG_FILE_PATH']}")
        print(f"   Текущая папка: {Path('.').absolute()}")
        sys.exit(1)
    
    # 6. Создаем папку для результатов
    config['OUTPUT_PATH'].mkdir(exist_ok=True)
    
    # 7. Информация о запуске
    if config['VERBOSE']:
        print(f"📁 Конфигурация загружена:")
        print(f"   Лог-файл: {config['LOG_FILE_PATH']}")
        print(f"   Папка результатов: {config['OUTPUT_PATH']}")
        print(f"   Топ пиров: {config['TOP_PEERS_TO_ANALYZE']}")
    
    return config

if __name__ == "__main__":
    CONFIG = setup_config()
    print("Конфиг создан, но этот файл не для запуска!")
    print("Запускайте: python log_analyzer.py ваш_лог.jsonl")
else:
    CONFIG = None