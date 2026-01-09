import pandas as pd
from collections import Counter

def analyze_temporal_patterns(df):
    """Анализ временных паттернов активности"""
    print("\n⏰ ВРЕМЕННЫЕ ПАТТЕРНЫ АКТИВНОСТИ:")
    
    if 'event_timestamp' not in df.columns:
        return
    
    df['hour_minute'] = pd.to_datetime(df['event_timestamp']).dt.strftime('%H:%M')
    
    # Активность по минутам
    activity_by_minute = df['hour_minute'].value_counts().sort_index()
    
    print("  • Пиковая активность:")
    for time, count in activity_by_minute.head(3).items():
        print(f"    {time}: {count} событий")
    
    # Отключения по времени
    goodbye_df = df[df['type'] == 'PEER_GOODBYE_RECEIVED']
    if len(goodbye_df) > 0:
        goodbye_by_time = goodbye_df['hour_minute'].value_counts()
        if len(goodbye_by_time) > 0:
            peak_goodbye = goodbye_by_time.idxmax()
            print(f"  • Пик отключений: {peak_goodbye} ({goodbye_by_time.max()} отключений)")


def analyze_connection_quality(df):
    """Анализ качества соединений по задержкам и ошибкам"""
    print("\n📶 АНАЛИЗ КАЧЕСТВА СОЕДИНЕНИЙ:")
    
    # Задержки ping
    if 'details_latencyMs' in df.columns:
        ping_latency = df[df['details_latencyMs'].notna()]['details_latencyMs']
        if len(ping_latency) > 0:
            print(f"  • Ping задержки: {ping_latency.mean():.0f} мс в среднем")
            print(f"  • Максимальная: {ping_latency.max():.0f} мс")
            print(f"  • Минимальная: {ping_latency.min():.0f} мс")
    
    # Успешные vs неудачные подключения
    dial_success = df[df['type'] == 'DIAL_SUCCESS'].shape[0]
    dial_failure = df[df['type'] == 'DIAL_FAILURE'].shape[0]
    
    if dial_success + dial_failure > 0:
        success_rate = dial_success / (dial_success + dial_failure) * 100
        print(f"  • Успешных подключений: {dial_success}")
        print(f"  • Неудачных: {dial_failure}")
        print(f"  • Успешность: {success_rate:.1f}%")
    
    # Анализ по клиентам
    if 'details_client' in df.columns:
        print("\n  📊 КАЧЕСТВО ПО КЛИЕНТАМ:")
        clients = df['details_client'].dropna().unique()
        for client in clients[:5]:  # топ-5
            client_df = df[df['details_client'] == client]
            if len(client_df) > 10:
                errors = client_df[client_df['type'] == 'DIAL_FAILURE'].shape[0]
                total_dials = client_df[client_df['type'].str.contains('DIAL')].shape[0]
                if total_dials > 0:
                    error_rate = errors / total_dials * 100
                    print(f"    • {client}: {error_rate:.1f}% ошибок ({errors}/{total_dials})")


def identify_validators(df):
    """Пытается определить валидаторов по активности"""
    print("\n🎯 ПОПЫТКА ОПРЕДЕЛИТЬ ВАЛИДАТОРОВ:")
    
    # 1. По отправке агрегатов
    aggregator_peers = df[
        (df['type'] == 'BEACON_AGGREGATE_AND_PROOF_RECEIVED') & 
        (df['peer'] != 'unknown')
    ]['peer'].unique()
    
    if len(aggregator_peers) > 0:
        print(f"  • По агрегатам: {len(aggregator_peers)} возможных валидаторов")
        for peer in aggregator_peers[:5]:
            client = df[df['peer'] == peer]['details_client'].mode()
            client = client.iloc[0] if not client.empty else 'unknown'
            print(f"    - {peer[:20]}... ({client})")
    
    # 2. По активности в slot
    if 'details_slot' in df.columns:
        slot_activity = df[df['details_slot'].notna()].groupby('peer')['details_slot'].nunique()
        active_in_slots = slot_activity[slot_activity > 1]
        if len(active_in_slots) > 0:
            print(f"  • По активности в слотах: {len(active_in_slots)} пиров")
    
    # 3. По частоте heartbeat сообщений
    heartbeat_msgs = ['HEARTBEAT_SCORING', 'HEARTBEAT_DISCOVERY_NEEDED']
    heartbeat_peers = df[df['type'].isin(heartbeat_msgs)]['peer'].unique()
    if len(heartbeat_peers) > 0:
        print(f"  • По heartbeat: {len(heartbeat_peers)} пиров")

def analyze_connection_limits(df):
    """Анализ лимитов подключений"""
    print("\n🔢 АНАЛИЗ ЛИМИТОВ ПОДКЛЮЧЕНИЙ:")
    
    # 1. Goodbye с кодом 129
    goodbye_129 = df[
        (df['type'] == 'PEER_GOODBYE_RECEIVED') & 
        (df['details_reasonCode'] == 129)
    ]
    
    if len(goodbye_129) > 0:
        print(f"  • Отказов из-за лимитов: {len(goodbye_129)}")
        
        # Кто отказывает
        print("  • Клиенты, которые отказывают:")
        for client, count in goodbye_129['details_client'].value_counts().items():
            print(f"    - {client}: {count} отказов")
        
        # Временное распределение
        if 'event_timestamp' in goodbye_129.columns:
            goodbye_129['hour_min'] = pd.to_datetime(goodbye_129['event_timestamp']).dt.strftime('%H:%M')
            peak_time = goodbye_129['hour_min'].mode()
            if not peak_time.empty:
                print(f"  • Пиковое время отказов: {peak_time.iloc[0]}")
    
    # 2. Анализ DIAL_FAILURE
    dial_failures = df[df['type'] == 'DIAL_FAILURE']
    if len(dial_failures) > 0:
        print(f"  • Неудачных попыток подключения: {len(dial_failures)}")
        
        # Причины ошибок
        if 'details_error' in dial_failures.columns:
            errors = dial_failures['details_error'].str[:50].value_counts().head(5)
            print("  • Топ причин ошибок:")
            for error, count in errors.items():
                print(f"    - {error}: {count}")
                
                
def analyze_protocol_messages(df):
    """Анализирует сообщения по протоколам Ethereum 2.0"""
    protocols = {
        'ping': ['RPC_OUT_REQUEST', 'RPC_IN_REQUEST', 'RPC_OUT_RESPONSE', 
                'PEER_PING_SENT', 'PEER_PING_RECEIVED', 'PROTOCOL_NEGOTIATED'],
        'status': ['RPC_OUT_REQUEST', 'RPC_IN_REQUEST', 'RPC_OUT_RESPONSE', 'PEER_STATUS'],
        'metadata': ['RPC_OUT_REQUEST', 'RPC_IN_REQUEST', 'RPC_OUT_RESPONSE', 'PEER_METADATA'],
        'goodbye': ['RPC_OUT_REQUEST', 'RPC_IN_REQUEST', 'RPC_OUT_RESPONSE', 'PEER_GOODBYE_RECEIVED'],
        'gossip': ['BEACON_BLOCK_RECEIVED', 'BEACON_AGGREGATE_AND_PROOF_RECEIVED',
                  'DATA_COLUMN_SIDECAR_RECEIVED'],
        'discovery': ['DIAL_ATTEMPT_START', 'DIAL_SUCCESS', 'DIAL_FAILURE',
                     'DISCOVERY_DIAL_DECISION', 'DISCOVERY_ENR_FOUND']
    }
    
    print("\n📡 АНАЛИЗ СООБЩЕНИЙ ПО ПРОТОКОЛАМ:")
    for protocol, events in protocols.items():
        count = df[df['type'].isin(events)].shape[0]
        if count > 0:
            print(f"  {protocol.upper()}: {count} сообщений")
    
    # Какие пиры какие протоколы используют
    if 'peer' in df.columns:
        print("\n👥 ПРОТОКОЛЫ ПО ПИРАМ (топ-5):")
        for peer in df['peer'].value_counts().head(5).index:
            peer_df = df[df['peer'] == peer]
            print(f"\n  {peer[:20]}...")
            for protocol, events in protocols.items():
                proto_count = peer_df[peer_df['type'].isin(events)].shape[0]
                if proto_count > 0:
                    print(f"    • {protocol}: {proto_count}")

def link_validator_events(df):
    """
    Связывает события валидаторов, даже когда peer='unknown'.
    Ищет совпадения по slot, aggregatorIndex, времени.
    """
    if df.empty:
        return df
    
    print("\n🔗 ПОПЫТКА СВЯЗАТЬ ВАЛИДАТОРСКИЕ СОБЫТИЯ...")
    
    # 1. Создаем копию данных
    df_linked = df.copy()
    
    # 2. Находим ВСЕ события, связанные с валидаторами
    validator_events = [
        'BEACON_AGGREGATE_AND_PROOF_RECEIVED',
        'VALIDATOR_IDENTIFIED_AGGREGATOR', 
        'VALIDATOR_IDENTIFIED_PROPOSER',
        'VALIDATOR_IDENTIFIED_SYNC_AGGREGATOR'
    ]
    
    # 3. Собираем все события валидаторов
    all_validator_data = df_linked[df_linked['type'].isin(validator_events)]
    
    if all_validator_data.empty:
        print("   ℹ️ Нет данных о валидаторах для связи")
        return df_linked
    
    print(f"   Найдено {len(all_validator_data)} валидаторских событий")
    
    # 4. Группируем по времени (окно 100 мс)
    df_linked['timestamp_dt'] = pd.to_datetime(df_linked['event_timestamp'])
    
    # 5. Для каждого события с peer='unknown' ищем ближайшее по времени с известным peer
    unknown_events = df_linked[
        (df_linked['type'] == 'BEACON_AGGREGATE_AND_PROOF_RECEIVED') & 
        (df_linked['peer'] == 'unknown')
    ]
    
    known_validators = df_linked[
        (df_linked['type'] == 'VALIDATOR_IDENTIFIED_PROPOSER') & 
        (df_linked['peer'] != 'unknown')
    ]
    
    print(f"   • Событий с unknown peer: {len(unknown_events)}")
    print(f"   • Событий с известным peer: {len(known_validators)}")
    
    # 6. Простой алгоритм связи (для начала)
    linked_count = 0
    
    for idx, unknown_row in unknown_events.iterrows():
        # Ищем ближайшее по времени событие с известным peer
        unknown_time = pd.to_datetime(unknown_row['event_timestamp'])
        
        # Разница во времени не более 1 секунды
        time_diff = abs((known_validators['timestamp_dt'] - unknown_time).dt.total_seconds())
        
        # Берем самое близкое по времени
        if len(time_diff) > 0 and time_diff.min() < 1.0:
            closest_idx = time_diff.idxmin()
            known_peer = known_validators.loc[closest_idx, 'peer']
            
            # Заменяем 'unknown' на найденный peer
            df_linked.at[idx, 'peer'] = known_peer
            df_linked.at[idx, 'peer_linked'] = True  # Флаг, что peer был восстановлен
            
            linked_count += 1
            
            if linked_count <= 3:  # Показываем первые 3 примера
                print(f"   ✓ Связано: {unknown_time.time()} → peer={known_peer[:16]}...")
    
    if linked_count > 0:
        print(f"   ✅ Успешно связано {linked_count} событий!")
    else:
        print("   ⚠️ Не удалось связать события автоматически")
        print("   💡 Рекомендация: проверьте настройки логирования Lodestar")
    
    return df_linked


def analyze_disconnections(df, mode='detailed', max_top_clients=10, include_temporal=True):
    """
    Унифицированная функция анализа отключений пиров.
    
    Параметры:
    ----------
    df : pandas.DataFrame
        DataFrame с логами P2P-сети
    mode : str, optional
        Режим анализа: 'detailed' или 'basic'
    max_top_clients : int, optional
        Максимальное количество клиентов для вывода в топе
    include_temporal : bool, optional
        Включать ли анализ временных паттернов
    
    Возвращает:
    -----------
    pandas.DataFrame
        DataFrame с отфильтрованными событиями отключений
    """
    
    # Фильтруем события отключения
    if 'type' not in df.columns:
        print("ОШИБКА: В DataFrame нет колонки 'type'")
        return pd.DataFrame()
    
    disconnections = df[df['type'] == 'PEER_GOODBYE_RECEIVED'].copy()
    
    print(f"=== АНАЛИЗ ОТКЛЮЧЕНИЙ ({len(disconnections)} событий) ===")
    
    if len(disconnections) == 0:
        print("Нет событий отключения")
        return disconnections
    
    # ========== 1. ПОИСК КОЛОНОК ==========
    
    reason_code_col = None
    reason_text_col = None
    
    # Ищем колонки
    for col in df.columns:
        col_lower = col.lower()
        if 'reason' in col_lower:
            if 'code' in col_lower or col_lower.endswith('code'):
                reason_code_col = col
            elif 'text' in col_lower or col_lower.endswith('text'):
                reason_text_col = col
    
    print(f"Найдена колонка кода: {reason_code_col}")
    print(f"Найдена колонка текста: {reason_text_col}")
    
    # ========== 2. БАЗОВЫЙ РЕЖИМ ==========
    
    if mode == 'basic':
        print(f"\n📊 БАЗОВАЯ СТАТИСТИКА:")
        print(f"  • Всего отключений: {len(disconnections)}")
        
        if 'peer' in disconnections.columns:
            print(f"  • Уникальных пиров: {disconnections['peer'].nunique()}")
        
        if 'details_client' in disconnections.columns:
            client_stats = disconnections['details_client'].value_counts().head(max_top_clients)
            if len(client_stats) > 0:
                print(f"  • Топ клиентов по отключениям:")
                for client, count in client_stats.items():
                    print(f"    {client}: {count} раз")
        
        return disconnections
    
    # ========== 3. ДЕТАЛЬНЫЙ АНАЛИЗ КОДОВ ==========
    
    if reason_code_col and reason_code_col in disconnections.columns:
        # Убираем NaN и конвертируем в int если возможно
        codes_series = disconnections[reason_code_col].dropna()
        
        if len(codes_series) > 0:
            # Пробуем конвертировать в int
            try:
                codes_series = codes_series.astype(int)
            except:
                pass
            
            code_counts = codes_series.value_counts()
            total_codes = code_counts.sum()
            
            print("\n🔍 КОДЫ ПРИЧИН ОТКЛЮЧЕНИЙ:")
            
            # Расшифровка кодов
            CODE_MEANINGS = {
                129: "СЛИШКОМ МНОГО ПИРОВ (лимит подключений!)",
                3: "Внутренняя ошибка клиента",
                1: "Клиент выключается/перезагружается",
                2: "Нерелевантная сеть (несовместимость)",
                128: "Неизвестная причина",
                0: "Не указана (пустой код)"
            }
            
            for code, count in code_counts.items():
                # Получаем текст причины
                reason_text = "N/A"
                if reason_text_col and reason_text_col in disconnections.columns:
                    matching_rows = disconnections[disconnections[reason_code_col] == code]
                    if len(matching_rows) > 0:
                        text_val = matching_rows.iloc[0].get(reason_text_col)
                        if pd.notna(text_val):
                            reason_text = str(text_val)[:100]  # Ограничиваем длину
                
                # Расшифровка
                meaning = CODE_MEANINGS.get(code, "Неизвестный код")
                percentage = (count / total_codes) * 100 if total_codes > 0 else 0
                
                print(f"\n  Код {code}: {count} раз ({percentage:.1f}%)")
                print(f"    Текст: '{reason_text}'")
                print(f"    Значение: {meaning}")
                
                # Особый анализ для кода 129
                if code == 129:
                    print(f"    ⚠️  ВНИМАНИЕ: Это отказы из-за переполнения!")
                    
                    # Анализ по клиентам для кода 129
                    if 'details_client' in disconnections.columns:
                        code_129_data = disconnections[disconnections[reason_code_col] == code]
                        if not code_129_data.empty:
                            client_counts = code_129_data['details_client'].value_counts().head(3)
                            if len(client_counts) > 0:
                                print(f"    Клиенты с лимитом:")
                                for client, client_count in client_counts.items():
                                    print(f"      • {client}: {client_count} отказов")
        else:
            print("\n⚠️ Колонка с кодами найдена, но все значения пустые")
    else:
        print("\n⚠️ Не найдена колонка с кодами причин отключения")
    
    # ========== 4. АНАЛИЗ КЛИЕНТОВ ==========
    
    if 'details_client' in disconnections.columns:
        client_data = disconnections['details_client'].dropna()
        
        if len(client_data) > 0:
            client_stats = client_data.value_counts()
            total_clients = len(client_stats)
            
            print(f"\n👥 АНАЛИЗ ПО КЛИЕНТАМ:")
            print(f"  Всего уникальных клиентов: {total_clients}")
            
            if total_clients > 0:
                print(f"  Топ клиентов по отключениям:")
                for i, (client, count) in enumerate(client_stats.head(max_top_clients).items(), 1):
                    percentage = (count / len(disconnections)) * 100
                    print(f"    {i}. {client}: {count} раз ({percentage:.1f}%)")
    
    # ========== 5. ВРЕМЕННОЙ АНАЛИЗ ==========
    
    if include_temporal and 'event_timestamp' in disconnections.columns:
        try:
            # Создаем копию для временного анализа
            temp_df = disconnections.copy()
            temp_df['hour'] = pd.to_datetime(temp_df['event_timestamp'], errors='coerce').dt.hour
            
            # Убираем NaN
            hour_data = temp_df['hour'].dropna()
            
            if len(hour_data) > 0:
                hour_stats = hour_data.value_counts().sort_index()
                
                print(f"\n⏰ РАСПРЕДЕЛЕНИЕ ПО ЧАСАМ:")
                if len(hour_stats) > 0:
                    max_count = hour_stats.max()
                    for hour in sorted(hour_stats.index):
                        count = hour_stats[hour]
                        bar_len = int((count / max_count) * 20) if max_count > 0 else 0
                        bar = '█' * bar_len
                        print(f"  {int(hour):02}:00: {bar} {int(count)}")
                else:
                    print("  Нет данных для построения распределения")
        except Exception as e:
            print(f"\n⚠️ Ошибка при анализе времени: {str(e)[:100]}")
    
    # ========== 6. ИТОГОВЫЕ ВЫВОДЫ ==========
    
    print(f"\n{'='*50}")
    print("ИТОГИ:")
    print(f"• Всего отключений: {len(disconnections)}")
    
    if 'peer' in disconnections.columns:
        unique_peers = disconnections['peer'].nunique()
        print(f"• Уникальных пиров: {unique_peers}")
    
    # Проверка на код 129
    if reason_code_col and reason_code_col in disconnections.columns:
        code_129_count = (disconnections[reason_code_col] == 129).sum()
        if code_129_count > 0:
            print(f"• ⚠️  КРИТИЧЕСКИХ отключений (код 129): {code_129_count}")
            print(f"  Рекомендация: проверьте настройки max_peers")
    
    return disconnections


def analyze_peer_activity_by_category(df, top_n=20):
    """
    Анализирует активность пиров по КАТЕГОРИЯМ событий.
    ВКЛЮЧАЕТ анализ валидаторской активности.
    """
    # Проверка необходимых колонок
    required_cols = ['type', 'peer']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"ОШИБКА: Отсутствуют колонки: {missing_cols}")
        return {}
    
    # Категории событий
    categories = {
        'validator': ['BEACON_AGGREGATE_AND_PROOF_RECEIVED'],
        'block_propagation': ['BEACON_BLOCK_RECEIVED', 'DATA_COLUMN_SIDECAR_RECEIVED'],
        'p2p_connection': ['PEER_CONNECT', 'PEER_DISCONNECT', 'PEER_TCP_CONNECTED'],
        'discovery': ['DISCOVERY_ENR_FOUND', 'DISCOVERY_DIAL_DECISION'],
        'rpc': ['RPC_IN_REQUEST', 'RPC_OUT_REQUEST', 'RPC_OUT_RESPONSE', 'RPC_ERROR'],
        'status': ['PEER_STATUS', 'PEER_PING_SENT', 'PEER_PING_RECEIVED'],
        'metadata': ['PEER_METADATA', 'PROTOCOL_NEGOTIATED'],
        'goodbye': ['PEER_GOODBYE_RECEIVED']
    }
    
    # 1. Фильтруем unknown пиров
    valid_df = df[df['peer'] != 'unknown'].copy()
    valid_df = valid_df.dropna(subset=['peer'])
    
    # 2. Анализ валидаторских событий
    validator_events = df[df['type'] == 'BEACON_AGGREGATE_AND_PROOF_RECEIVED']
    print(f"[VALIDATOR] Всего агрегатов: {len(validator_events)}")
    
    known_validators = validator_events[validator_events['peer'] != 'unknown']
    print(f"[VALIDATOR] От известных пиров: {len(known_validators)}")
    
    # 3. Топ активных пиров
    if len(valid_df) == 0:
        print("[INFO] Нет данных об известных пирах")
        return {}
    
    top_peers = valid_df['peer'].value_counts().head(top_n).index
    results = {}
    
    for peer in top_peers:
        peer_data = valid_df[valid_df['peer'] == peer]
        
        # Считаем по категориям
        cat_counts = {}
        for cat_name, event_types in categories.items():
            count = peer_data[peer_data['type'].isin(event_types)].shape[0]
            if count > 0:
                cat_counts[cat_name] = count
        
        # Валидаторские события для этого пира
        validator_count = validator_events[validator_events['peer'] == peer].shape[0]
        if validator_count > 0:
            cat_counts['validator_direct'] = validator_count
        
        # Клиент
        client = 'unknown'
        if 'details_client' in peer_data.columns:
            clients = peer_data['details_client'].dropna().unique()
            if len(clients) > 0:
                client = clients[0]
        
        results[peer] = {
            'total_events': len(peer_data),
            'categories': cat_counts,
            'client': client
        }
    
    print(f"[INFO] Проанализировано {len(results)} пиров")
    
    # 4. Топ отправителей агрегатов
    if len(known_validators) > 0:
        print(f"\n[VALIDATOR ANALYSIS]")
        print("Топ отправителей агрегатов:")
        for peer, count in known_validators['peer'].value_counts().head(5).items():
            print(f"  {peer[:20]}...: {count} агрегатов")
    
    return results


def analyze_basic_stats(df):
    """Считает базовую статистику."""
    stats = {
        'total_entries': len(df),
        'unique_peers': df['peer'].nunique() if 'peer' in df.columns else 0,
        'unique_event_types': df['type'].nunique() if 'type' in df.columns else 0
    }
    
    # Поиск временной колонки
    time_columns = ['event_timestamp', 'timestamp', 'time', 'created_at']
    time_col = next((col for col in time_columns if col in df.columns), None)
    
    if time_col:
        try:
            min_time = df[time_col].min()
            max_time = df[time_col].max()
            stats['time_range'] = f"{min_time} - {max_time}"
            stats['time_column'] = time_col
        except:
            stats['time_range'] = "Ошибка чтения времени"
    else:
        stats['time_range'] = "Не найдена колонка с временем"
    
    return stats


def analyze_event_type_distribution(df):
    """Считает частоту каждого типа события (type)."""
    if 'type' not in df.columns:
        print("[WARNING] Нет колонки 'type'")
        return {}
    
    return df['type'].value_counts().to_dict()


def analyze_client_distribution(df):
    """Определяет, какие клиенты (Lighthouse, Prysm) встречаются в логах."""
    
    def normalize_client_name(value):
        """Нормализует название клиента."""
        if pd.isna(value):
            return None
        
        value = str(value).strip().lower()
        
        # Удаляем версию и дополнительную информацию
        if '/' in value:
            value = value.split('/')[0]
        if 'v' in value and value.index('v') > 0:
            value = value.split('v')[0]
        
        # Стандартизация названий
        name_mapping = {
            'lighthouse': 'Lighthouse',
            'prysm': 'Prysm',
            'teku': 'Teku',
            'nimbus': 'Nimbus',
            'lodestar': 'Lodestar',
            'grandine': 'Grandine'
        }
        
        return name_mapping.get(value, value.title())
    
    # Ищем колонки с информацией о клиентах
    client_columns = []
    for col in df.columns:
        col_lower = col.lower()
        if 'client' in col_lower and not any(x in col_lower for x in ['_id', '_secret', '_token']):
            client_columns.append(col)
    
    # Собираем и нормализуем клиентов
    all_clients = []
    for col in client_columns:
        normalized = df[col].apply(normalize_client_name).dropna()
        all_clients.extend(normalized.tolist())
    
    # Подсчет
    if all_clients:
        client_counter = Counter(all_clients)
        return dict(client_counter.most_common())
    
    return {}


def analyze_peer_activity(df, top_n=20):
    """Находит самых активных пиров по количеству событий."""
    if 'peer' not in df.columns:
        print("[WARNING] Нет колонки 'peer'")
        return {}
    
    return df['peer'].value_counts().head(top_n).to_dict()

def analyze_validator_events_detailed(df):
    """
    ПОДРОБНЫЙ анализ валидаторских событий для новичков.
    Помогает понять, почему peer = 'unknown' в агрегатах.
    """
    
    print("\n" + "="*60)
    print("🔍 ПОДРОБНЫЙ АНАЛИЗ ВАЛИДАТОРСКИХ СОБЫТИЙ (ДЛЯ НОВИЧКОВ)")
    print("="*60)
    
    # 1. Находим ВСЕ валидаторские события
    validator_events = df[df['type'] == 'BEACON_AGGREGATE_AND_PROOF_RECEIVED']
    
    print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"   Всего получено агрегатов: {len(validator_events)}")
    
    if len(validator_events) == 0:
        print("   ❌ Нет валидаторских событий в логах!")
        return
    
    # 2. Проверяем колонку 'peer' (самое важное!)
    print(f"\n🔎 АНАЛИЗ КОЛОНКИ 'PEER':")
    
    if 'peer' not in validator_events.columns:
        print("   ❌ Колонка 'peer' вообще отсутствует в данных!")
    else:
        # Считаем сколько 'unknown' vs нормальных peer ID
        unknown_count = (validator_events['peer'] == 'unknown').sum()
        known_count = len(validator_events) - unknown_count
        
        print(f"   • Всего записей: {len(validator_events)}")
        print(f"   • С 'unknown' peer: {unknown_count} ({unknown_count/len(validator_events)*100:.1f}%)")
        print(f"   • С известным peer: {known_count} ({known_count/len(validator_events)*100:.1f}%)")
        
        # Показываем примеры нормальных peer ID (если есть)
        if known_count > 0:
            known_peers = validator_events[validator_events['peer'] != 'unknown']\
                          ['peer'].dropna().unique()
            print(f"\n   📋 Примеры известных peer ID (первые 3):")
            for i, peer in enumerate(known_peers[:3], 1):
                print(f"     {i}. {peer[:30]}...")
    
    # 3. Смотрим, какие еще колонки есть в этих событиях
    print(f"\n📁 ДОСТУПНЫЕ КОЛОНКИ В ВАЛИДАТОРСКИХ СОБЫТИЯХ:")
    
    # Выбираем только колонки, которые есть в validator_events
    available_cols = [col for col in validator_events.columns if col in df.columns]
    
    print(f"   Всего колонок: {len(available_cols)}")
    print(f"   Первые 10 колонок: {available_cols[:10]}")
    
    # Ищем колонки, которые могут содержать информацию о пире
    peer_related_cols = []
    for col in available_cols:
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in ['peer', 'client', 'from', 'sender', 'aggregator']):
            peer_related_cols.append(col)
    
    if peer_related_cols:
        print(f"\n   🔍 Колонки, которые МОГУТ содержать информацию об отправителе:")
        for col in peer_related_cols:
            # Проверяем, есть ли в этой колонке не-NaN значения
            non_null_count = validator_events[col].notna().sum()
            if non_null_count > 0:
                print(f"     • {col}: {non_null_count} непустых значений")
                
                # Показываем пример значения
                sample = validator_events[col].dropna().iloc[0]
                print(f"       Пример: {str(sample)[:50]}...")
            else:
                print(f"     • {col}: все значения пустые")
    
    # 4. Анализируем колонку details (если она есть)
    print(f"\n📦 АНАЛИЗ КОЛОНКИ 'details' (если есть):")
    
    if 'details' in validator_events.columns:
        # Берем первую непустую запись
        first_details = validator_events['details'].dropna().iloc[0] \
                       if not validator_events['details'].dropna().empty else None
        
        if first_details:
            print(f"   Первая запись в 'details':")
            
            if isinstance(first_details, dict):
                print(f"   Это словарь с ключами: {list(first_details.keys())[:10]}")
                
                # Ищем полезные ключи
                useful_keys = []
                for key in first_details.keys():
                    key_lower = str(key).lower()
                    if any(kw in key_lower for kw in ['peer', 'from', 'aggregator', 'sender', 'client']):
                        useful_keys.append(key)
                
                if useful_keys:
                    print(f"\n   🔑 Полезные ключи в details:")
                    for key in useful_keys:
                        print(f"     • {key}: {first_details[key]}")
                else:
                    print(f"   ℹ️  В details нет очевидных ключей с информацией об отправителе")
            else:
                print(f"   ℹ️  Details не словарь, а: {type(first_details)}")
                print(f"   Значение: {str(first_details)[:100]}...")
        else:
            print(f"   ❌ Колонка 'details' есть, но все значения пустые")
    else:
        print(f"   ℹ️  Колонки 'details' нет в данных")
    
    # 5. Проверяем колонки с 'details_' префиксом (развернутые details)
    print(f"\n🔧 АНАЛИЗ РАЗВЕРНУТЫХ КОЛОНОК (details_*):")
    
    details_cols = [col for col in available_cols if col.startswith('details_')]
    
    if details_cols:
        print(f"   Найдено {len(details_cols)} колонок с префиксом 'details_'")
        
        # Ищем колонки, которые могут содержать peer информацию
        for col in details_cols[:15]:  # Показываем первые 15
            col_lower = col.lower()
            if any(kw in col_lower for kw in ['peer', 'aggregator', 'from']):
                non_null = validator_events[col].notna().sum()
                if non_null > 0:
                    # Показываем примеры значений
                    sample_values = validator_events[col].dropna().unique()[:3]
                    print(f"\n     • {col}: {non_null} непустых значений")
                    print(f"       Примеры: {sample_values}")
    
    # 6. ПРАКТИЧЕСКИЕ СОВЕТЫ
    print(f"\n" + "="*60)
    print("💡 ПРАКТИЧЕСКИЕ СОВЕТЫ ДЛЯ ИСПРАВЛЕНИЯ:")
    print("="*60)
    
    print(f"\n1. 📝 ПРОВЕРЬТЕ НАСТРОЙКИ ЛОГИРОВАНИЯ:")
    print(f"   • В Lodestar: Убедитесь, что 'LOG_PEER_IDS=true'")
    print(f"   • Уровень логов: Используйте '--logLevel=debug' или '--logLevel=verbose'")
    
    print(f"\n2. 🔧 ВАРИАНТЫ РЕШЕНИЯ:")
    
    if known_count == 0:
        print(f"   ❌ СИЛЬНАЯ ПРОБЛЕМА: 0% агрегатов с известным peer")
        print(f"   Действия:")
        print(f"   1. Обновите Lodestar до последней версии")
        print(f"   2. Проверьте конфигурационный файл")
        print(f"   3. Запустите с флагом: --logLevel=debug --logFormat=json")
    elif known_count < len(validator_events) * 0.5:
        print(f"   ⚠️  ПРОБЛЕМА: Меньше 50% агрегатов с известным peer")
        print(f"   Действия:")
        print(f"   1. Проверьте настройки логирования")
        print(f"   2. Может быть проблема с конкретными клиентами")
    else:
        print(f"   ✅ НОРМАЛЬНО: Больше 50% агрегатов с известным peer")
    
    print(f"\n3. 🐛 КАК ПРОВЕРИТЬ СЕЙЧАС:")
    print(f"   • Откройте файл processed_logs.csv")
    print(f"   • Найдите колонку 'type'")
    print(f"   • Отфильтруйте только 'BEACON_AGGREGATE_AND_PROOF_RECEIVED'")
    print(f"   • Посмотрите колонку 'peer' - что там?")
    
    print(f"\n4. 📊 БЫСТРЫЙ ТЕСТ В КОДЕ:")
    print(f"   Добавьте в main программу:")
    print(f"   '''python")
    print(f"   # Проверка первых 5 валидаторских событий")
    print(f"   validator_sample = df[df['type'] == 'BEACON_AGGREGATE_AND_PROOF_RECEIVED'].head(5)")
    print(f"   for idx, row in validator_sample.iterrows():")
    print(f"       print(f\"Событие {{idx}}:\")")
    print(f"       print(f\"  Peer: {{row.get('peer', 'NO PEER')}}\")")
    print(f"       print(f\"  Details keys: {{list(row.get('details', {{}}).keys()) if isinstance(row.get('details'), dict) else 'N/A'}}\")")
    print(f"   '''")
    
    return validator_events