# visualizer.py - ПОЛНОСТЬЮ РАБОЧИЙ КОД
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def plot_peer_categories_barchart(peer_category_dict, save_path=None):
    """
    Строит группированную столбчатую диаграмму активности пиров по категориям.
    ИСПРАВЛЕНА ОШИБКА с вложенными словарями.
    """
    if not peer_category_dict:
        print("[WARNING] Нет данных для категоризированного графика")
        return
    
    print("[INFO] Подготовка данных для группированного графика...")
    
    # 1. Извлекаем данные из сложной структуры
    # peer_category_dict имеет вид: {peer_id: {'peer_id':..., 'total_events':..., 'categories': {...}}}
    
    categories_data = {}
    all_categories = set()
    
    for peer_id, peer_stats in peer_category_dict.items():
        if 'categories' in peer_stats and peer_stats['categories']:
            # Создаем запись для каждого пира
            categories_data[peer_id] = {}
            
            # Копируем данные из categories
            for category, count in peer_stats['categories'].items():
                categories_data[peer_id][category] = count
                all_categories.add(category)
            
            # Добавляем клиента, если есть
            if 'client' in peer_stats:
                categories_data[peer_id]['_client'] = peer_stats['client']
    
    if not categories_data:
        print("[ERROR] Нет данных по категориям для построения графика")
        print("[DEBUG] Структура полученных данных:", list(peer_category_dict.items())[0] if peer_category_dict else "Пусто")
        return
    
    print(f"[INFO] Найдено {len(categories_data)} пиров с {len(all_categories)} категориями")
    
    # 2. Создаем DataFrame
    import pandas as pd
    import numpy as np
    
    records = []
    for peer_id, cat_counts in categories_data.items():
        record = {'Peer ID': peer_id[:16] + '...'}
        
        # Добавляем все категории
        for category in all_categories:
            record[category] = cat_counts.get(category, 0)
        
        # Добавляем клиента
        if '_client' in cat_counts:
            record['Client'] = cat_counts['_client']
        
        records.append(record)
    
    df = pd.DataFrame(records)
    
    # 3. Если категорий слишком много, берем только самые частые
    if len(all_categories) > 8:
        # Суммируем по категориям
        category_sums = {}
        for category in all_categories:
            category_sums[category] = df[category].sum()
        
        # Берем топ-8 категорий
        top_categories = sorted(category_sums.items(), key=lambda x: x[1], reverse=True)[:8]
        top_categories = [cat for cat, _ in top_categories]
        
        print(f"[INFO] Выбрано топ-{len(top_categories)} категорий из {len(all_categories)}")
    else:
        top_categories = list(all_categories)
    
    # 4. Строим график
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # Позиции для группированных столбцов
    x = np.arange(len(df))
    width = 0.8 / len(top_categories)
    
    # Цвета для категорий
    colors = plt.cm.Set3(np.linspace(0, 1, len(top_categories)))
    
    # Рисуем столбцы для каждой категории
    bars = []
    for i, (category, color) in enumerate(zip(top_categories, colors)):
        values = df[category].fillna(0).values
        offset = width * i - width * (len(top_categories) - 1) / 2
        
        # Проверяем, что есть не нулевые значения
        if values.sum() > 0:
            bar = ax.bar(x + offset, values, width, label=category, color=color, alpha=0.8)
            bars.append(bar)
    
    # 5. Настройки графика
    ax.set_xlabel('Пиры', fontsize=12)
    ax.set_ylabel('Количество событий', fontsize=12)
    ax.set_title(f'Активность пиров по категориям (топ-{len(top_categories)})', 
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    
    # Подписи для оси X (сокращенные ID + клиент)
    peer_labels = []
    for _, row in df.iterrows():
        label = row['Peer ID']
        if 'Client' in row and pd.notna(row['Client']):
            label += f"\n({row['Client']})"
        peer_labels.append(label)
    
    ax.set_xticklabels(peer_labels, rotation=45, ha='right', fontsize=9)
    
    # Легенда
    ax.legend(title='Категория событий', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Сетка
    ax.grid(True, alpha=0.3, axis='y')
    
    # Автоматическая настройка пределов оси Y
    ax.set_ylim(0, ax.get_ylim()[1] * 1.1)
    
    plt.tight_layout()
    
    # 6. Сохранение
    if save_path:
        try:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"[SUCCESS] График категорий пиров сохранён: {save_path}")
        except Exception as e:
            print(f"[ERROR] Ошибка сохранения: {e}")
    
    plt.show()
    plt.close()
    
    # 7. Дополнительная информация в консоль
    print("[INFO] Статистика по категориям:")
    for category in top_categories:
        total = df[category].sum()
        if total > 0:
            print(f"  - {category}: {total} событий")

def setup_visuals(style='darkgrid', palette='viridis'):
    """Настраивает визуальный стиль графиков."""
    sns.set_style(style)
    sns.set_palette(palette)
    plt.rcParams['figure.figsize'] = (12, 6)
    plt.rcParams['font.size'] = 11

def plot_event_type_barchart(event_counts_dict, save_path=None):
    """Строит столбчатую диаграмму распределения типов событий."""
    if not event_counts_dict:
        print("[WARNING] Нет данных для графика типов событий")
        return
    
    # Преобразуем словарь в DataFrame
    event_df = pd.DataFrame(list(event_counts_dict.items()), 
                           columns=['Тип события', 'Количество'])
    
    # Сортируем по убыванию и берем топ-20 (или все, если меньше)
    event_df = event_df.sort_values('Количество', ascending=False).head(20)
    
    fig, ax = plt.subplots(figsize=(14, 8))
    barplot = sns.barplot(data=event_df, x='Тип события', y='Количество', ax=ax)
    
    ax.set_title('Топ-20 типов событий в логах P2P сети', fontsize=16, pad=20)
    ax.set_xlabel('Тип события', fontsize=12)
    ax.set_ylabel('Количество событий', fontsize=12)
    
    # Добавляем подписи значений
    for container in barplot.containers:
        ax.bar_label(container, fmt='%d', padding=3, fontsize=9)
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    if save_path:
        try:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"[INFO] График типов событий сохранен: {save_path}")
        except Exception as e:
            print(f"[ERROR] Не удалось сохранить график: {e}")
    
    plt.show()
    plt.close()

def plot_peer_activity_treemap(peer_activity_dict, save_path_html=None):
    """
    Строит интерактивную карту активности пиров.
    УСТРАНЕНЫ ВСЕ ОШИБКИ:
    1. Фильтрация 'unknown' и некорректных данных
    2. Корректное создание DataFrame
    3. Сохранение с CDN + локальная версия
    4. Подробные сообщения об ошибках
    """
    print("=== НАЧАЛО ПОСТРОЕНИЯ TREEMAP ===")
    
    # 1. ПРОВЕРКА ВХОДНЫХ ДАННЫХ
    if not peer_activity_dict:
        print("[ERROR] Словарь peer_activity_dict ПУСТ!")
        return
    
    # 2. ФИЛЬТРАЦИЯ: убираем 'unknown' и некорректные данные
    filtered_dict = {}
    invalid_keys = []
    
    for peer_id, activity in peer_activity_dict.items():
        # Проверяем, что это реальный Peer ID (начинается с '16Uiu2')
        if isinstance(peer_id, str) and peer_id.startswith('16Uiu2'):
            # Проверяем, что активность - положительное число
            if isinstance(activity, (int, float)) and activity > 0:
                filtered_dict[peer_id] = activity
            else:
                invalid_keys.append((peer_id, f"Некорректная активность: {activity}"))
        else:
            invalid_keys.append((peer_id, "Не похож на Peer ID"))
    
    print(f"[INFO] После фильтрации: {len(filtered_dict)} валидных пиров из {len(peer_activity_dict)}")
    
    if invalid_keys and len(invalid_keys) < 5:
        print(f"[DEBUG] Отфильтрованы: {invalid_keys}")
    
    # 3. ПРОВЕРКА: есть ли данные для графика
    if not filtered_dict:
        print("[ERROR] Нет валидных данных для построения графика!")
        print("[DEBUG] Исходные данные:", list(peer_activity_dict.items())[:5])
        return
    
    # 4. СОЗДАНИЕ DATAFRAME
    try:
        peer_df = pd.DataFrame(
            list(filtered_dict.items()),
            columns=['Peer ID', 'Activity']
        )
        peer_df['parent'] = 'Все пиры'
        
        print(f"[INFO] Создан DataFrame с {len(peer_df)} строками")
        print(f"[DEBUG] Пример данных:\n{peer_df.head(3)}")
        
    except Exception as e:
        print(f"[ERROR] Ошибка создания DataFrame: {e}")
        return
    
    # 5. ПОСТРОЕНИЕ ГРАФИКА
    try:
        fig = px.treemap(
            peer_df,
            path=['parent', 'Peer ID'],
            values='Activity',
            title=f'Активность пиров (топ-{len(peer_df)})',
            color='Activity',
            color_continuous_scale='Blues',
            hover_data={'Activity': ':.0f', 'Peer ID': True}
        )
        
        # Настройка отображения
        fig.update_traces(
            textinfo="label+value",
            texttemplate='<b>%{label}</b><br>%{value} событий',
            hovertemplate=(
                '<b>%{label}</b><br>'
                'Активность: <b>%{value}</b> событий<br>'
                '<extra></extra>'
            )
        )
        
        fig.update_layout(
            margin=dict(t=50, l=25, r=25, b=25),
            title_font_size=16
        )
        
    except Exception as e:
        print(f"[ERROR] Ошибка построения графика Plotly: {e}")
        return
    
    # 6. СОХРАНЕНИЕ ФАЙЛА
    if save_path_html:
        try:
            save_path_html = str(save_path_html)
            
            # ВАРИАНТ 1: CDN (нужен интернет, маленький файл ~10KB)
            fig.write_html(
                save_path_html,
                full_html=True,
                include_plotlyjs='cdn',  # Библиотека грузится из интернета
                auto_open=False
            )
            
            # ВАРИАНТ 2: Локальная версия (работает без интернета)
            offline_path = save_path_html.replace('.html', '_offline.html')
            fig.write_html(
                offline_path,
                full_html=True,
                include_plotlyjs=True,  # Библиотека встроена в файл (~3MB)
                auto_open=False
            )
            
            print(f"[SUCCESS] График успешно сохранен!")
            print(f"         CDN-версия (нужен интернет): {save_path_html}")
            print(f"         Локальная версия (без интернета): {offline_path}")
            print(f"         Размеры: CDN ~10KB, Локальная ~3MB")
            
        except Exception as e:
            print(f"[ERROR] Ошибка сохранения HTML: {e}")
            # Пробуем сохранить простым способом
            try:
                with open(save_path_html, 'w', encoding='utf-8') as f:
                    f.write('<html><body><h2>Ошибка создания графика</h2>')
                    f.write(f'<p>{str(e)}</p></body></html>')
            except:
                pass
            return
    
    print("=== ЗАВЕРШЕНО ПОСТРОЕНИЕ TREEMAP ===")

def plot_timeline_of_events(df, time_column='event_timestamp', 
                           event_column='type', top_events=8, save_path=None):
    """
    Строит временную шкалу событий.
    ИСПРАВЛЕНА РАБОТА С ВРЕМЕНЕМ И ФИЛЬТРАЦИЯ.
    """
    print(f"[INFO] Строим временную шкалу из {len(df)} событий...")
    
    # 1. ПРОВЕРКА КОЛОНОК
    if time_column not in df.columns:
        print(f"[ERROR] Колонка '{time_column}' не найдена в данных!")
        print(f"[DEBUG] Доступные колонки: {list(df.columns)[:15]}...")
        return
    
    if event_column not in df.columns:
        print(f"[ERROR] Колонка '{event_column}' не найдена!")
        return
    
    # 2. КОПИРОВАНИЕ И ФИЛЬТРАЦИЯ
    plot_df = df[[time_column, event_column]].copy()
    plot_df = plot_df.dropna(subset=[time_column, event_column])
    
    if plot_df.empty:
        print("[WARNING] Нет данных после очистки")
        return
    
    print(f"[INFO] Осталось {len(plot_df)} событий для графика")
    
    # 3. ВЫБОР ТОП-СОБЫТИЙ
    top_event_types = plot_df[event_column].value_counts().head(top_events)
    top_event_list = top_event_types.index.tolist()
    
    plot_df = plot_df[plot_df[event_column].isin(top_event_list)]
    
    if plot_df.empty:
        print("[WARNING] Нет данных после фильтрации по топ-событиям")
        return
    
    print(f"[INFO] Строим шкалу для {len(top_event_list)} типов событий")
    print(f"[DEBUG] Топ-события: {top_event_list}")
    
    # 4. СОЗДАНИЕ ГРАФИКА
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # Создаем цветовую карту для событий
    colors = plt.cm.tab20c(np.linspace(0, 1, len(top_event_list)))
    
    for i, (event_type, color) in enumerate(zip(top_event_list, colors)):
        event_data = plot_df[plot_df[event_column] == event_type]
        
        if len(event_data) > 1000:  # Если много точек, делаем выборку
            event_data = event_data.sample(n=1000, random_state=42)
        
        ax.scatter(
            event_data[time_column],
            [i] * len(event_data),
            label=f'{event_type} ({len(event_data)})',
            alpha=0.6,
            s=30,
            marker='o',
            color=color,
            edgecolors='black',
            linewidth=0.5
        )
    
    # 5. НАСТРОЙКА ОТОБРАЖЕНИЯ
    ax.set_yticks(range(len(top_event_list)))
    ax.set_yticklabels([f'{e} ({c})' for e, c in zip(top_event_list, top_event_types)])
    
    ax.set_xlabel('Время', fontsize=12)
    ax.set_ylabel('Тип события (количество)', fontsize=12)
    ax.set_title(f'Временная шкала топ-{len(top_event_list)} событий', 
                 fontsize=16, fontweight='bold', pad=20)
    
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Форматирование времени на оси X
    plt.xticks(rotation=30, ha='right')
    
    # Автонастройка формата даты
    fig.autofmt_xdate()
    
    plt.tight_layout()
    
    # 6. СОХРАНЕНИЕ
    if save_path:
        try:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"[INFO] Временная шкала сохранена: {save_path}")
        except Exception as e:
            print(f"[ERROR] Не удалось сохранить шкалу: {e}")
    
    plt.show()
    plt.close()
    print("[INFO] Построение временной шкалы завершено.")

def plot_message_categories(df, save_path=None):
    """
    ДОПОЛНИТЕЛЬНАЯ ФУНКЦИЯ для вашего исследования:
    Группирует сообщения по категориям (P2P, RPC, Gossip и т.д.)
    """
    if df.empty:
        return
    
    # Определяем категории
    categories = {
        'P2P соединения': ['PEER_CONNECT', 'PEER_DISCONNECT', 'PEER_TCP_CONNECTED',
                          'PEER_TCP_DISCONNECTED', 'PEER_IDENTIFY'],
        'RPC запросы': ['RPC_OUT_REQUEST', 'RPC_IN_REQUEST', 'RPC_OUT_RESPONSE',
                       'RPC_ERROR', 'PROTOCOL_NEGOTIATED'],
        'Gossip': ['BEACON_BLOCK_RECEIVED', 'BEACON_AGGREGATE_AND_PROOF_RECEIVED',
                  'DATA_COLUMN_SIDECAR_RECEIVED'],
        'Статус/Пинг': ['PEER_STATUS', 'PEER_PING_SENT', 'PEER_PING_RECEIVED',
                       'PEER_PING_ROUNDTRIP', 'PEER_METADATA'],
        'Discovery': ['DISCOVERY_ENR_FOUND', 'DISCOVERY_DIAL_DECISION',
                     'DISCOVERY_START', 'HEARTBEAT_DISCOVERY_NEEDED'],
        'Прочее': ['PEER_GOODBYE_RECEIVED', 'HEARTBEAT_SCORING']
    }
    
    # Считаем количество по категориям
    category_counts = {}
    for category, events in categories.items():
        count = df[df['type'].isin(events)].shape[0]
        if count > 0:
            category_counts[category] = count
    
    if not category_counts:
        return
    
    # Строим график
    cat_df = pd.DataFrame(list(category_counts.items()),
                         columns=['Категория', 'Количество'])
    cat_df = cat_df.sort_values('Количество', ascending=False)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(cat_df['Категория'], cat_df['Количество'], color='steelblue')
    
    ax.set_title('Распределение сообщений по категориям', fontsize=16, pad=20)
    ax.set_ylabel('Количество событий', fontsize=12)
    ax.set_xlabel('Категория', fontsize=12)
    
    # Добавляем подписи
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{int(height):,}', ha='center', va='bottom', fontsize=10)
    
    plt.xticks(rotation=15, ha='right')
    plt.tight_layout()
    
    if save_path:
        try:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"[INFO] График категорий сохранен: {save_path}")
        except Exception as e:
            print(f"[ERROR] Не удалось сохранить график категорий: {e}")
    
    plt.show()
    plt.close()

# Тестирование модуля
if __name__ == "__main__":
    print("Тестирование модуля visualizer.py...")
    
    # Создаем тестовые данные
    test_events = {
        'PEER_CONNECT': 1500,
        'RPC_OUT_REQUEST': 1200,
        'BEACON_BLOCK_RECEIVED': 800,
        'PEER_PING_SENT': 700,
        'DISCOVERY_ENR_FOUND': 600
    }
    
    test_peers = {
        '16Uiu2HAkvzo658CEjaky3cRD9wPdThcdbeDvr9E1RkjWDmZfio5Z': 2088,
        '16Uiu2HAm2AfVRhyot6vRiruZDKYsPCeLE4YYkgst84D79mppirP7': 1584,
        '16Uiu2HAmFcogRNagE5ffRbyB5qKowFUYtqDHwGoC3UXGEsnqSFhr': 1250,
        '16Uiu2HAm5GmdfVwBBP1pfrvA5F7gMVa56KXp14NPv6YaxiP9fnR5': 1100,
        '16Uiu2HAmU6kCuiW5AeMqY4kkUf7qBng4TctLgQ5oVZ6yHb7KWU9k': 950
    }
    
    setup_visuals()
    
    # Тест 1: График типов событий
    print("\n1. Тест графика типов событий...")
    plot_event_type_barchart(test_events)
    
    # Тест 2: Treemap активности пиров
    print("\n2. Тест treemap активности пиров...")
    plot_peer_activity_treemap(test_peers, 'test_treemap.html')
    
    print("\nТестирование завершено!")