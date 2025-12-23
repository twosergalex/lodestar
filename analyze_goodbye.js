#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

console.log('🔍 АНАЛИЗ GOODBYE СООБЩЕНИЙ');
console.log('='.repeat(60));

// 1. Находим последний файл логов
const logDir = 'p2p-sniffer-logs';
const files = fs.readdirSync(logDir)
  .filter(f => f.startsWith('p2p-') && f.endsWith('.jsonl'))
  .sort();

if (files.length === 0) {
  console.log('❌ Нет файлов логов');
  process.exit(1);
}

const latestFile = files[files.length - 1];
console.log(`📁 Анализируем файл: ${latestFile}\n`);

// 2. Загружаем логи
const filePath = path.join(logDir, latestFile);
const content = fs.readFileSync(filePath, 'utf-8');
const logs = content.split('\n')
  .filter(line => line.trim())
  .map(line => {
    try {
      return JSON.parse(line);
    } catch (e) {
      return null;
    }
  })
  .filter(log => log !== null);

console.log(`📊 Всего событий в файле: ${logs.length}`);

// 3. Фильтруем GOODBYE события
const goodbyeLogs = logs.filter(log => 
  log.type === 'PEER_GOODBYE_RECEIVED' || 
  log.type === 'PEER_GOODBYE_SENT'
);

console.log(`📤 Найдено GOODBYE событий: ${goodbyeLogs.length}`);

if (goodbyeLogs.length === 0) {
  console.log('✅ GOODBYE сообщений нет - это хорошо!');
  process.exit(0);
}

// 4. Анализируем причины (если есть детали)
console.log('\n🎯 АНАЛИЗ ПРИЧИН ОТКЛЮЧЕНИЯ:');
console.log('-'.repeat(60));

const reasons = {
  received: {},  // Нам отправили GOODBYE
  sent: {}       // Мы отправили GOODBYE
};

// Известные коды ошибок Ethereum
const ERROR_CODES = {
  '0': 'CLIENT_SHUTDOWN',
  '1': 'IRRELEVANT_NETWORK',
  '2': 'ERROR_FAULT',
  '3': 'TOO_MANY_PEERS',
  '129': 'CLIENT_HAS_TOO_MANY_PEERS',
  '130': 'RESTARTED_CLIENT',
  '131': 'WRONG_NETWORK',
  '132': 'SYNC_TIMEOUT',
  '133': 'BANNED',
  '134': 'INCOMPATIBLE_VERSION'
};

goodbyeLogs.forEach(log => {
  const category = log.type === 'PEER_GOODBYE_RECEIVED' ? 'received' : 'sent';
  const details = log.details || {};
  
  // Определяем причину
  let reason = 'UNKNOWN';
  
  if (details.reasonText) {
    reason = details.reasonText;
  } else if (details.reasonCode !== undefined) {
    const code = details.reasonCode.toString();
    reason = ERROR_CODES[code] || `Код ${code}`;
  } else if (details.reason) {
    reason = details.reason;
  } else {
    // Пробуем извлечь из других полей
    const allDetails = JSON.stringify(details).toLowerCase();
    if (allDetails.includes('shutdown')) reason = 'SHUTDOWN';
    else if (allDetails.includes('ban')) reason = 'BANNED';
    else if (allDetails.includes('timeout')) reason = 'TIMEOUT';
    else if (allDetails.includes('sync')) reason = 'SYNC_ISSUE';
    else if (allDetails.includes('too many')) reason = 'TOO_MANY_PEERS';
  }
  
  // Считаем
  if (!reasons[category][reason]) {
    reasons[category][reason] = {
      count: 0,
      peers: new Set(),
      examples: []
    };
  }
  
  const reasonEntry = reasons[category][reason];
  reasonEntry.count++;
  if (log.peer) reasonEntry.peers.add(log.peer);
  
  // Сохраняем пример (первые 3)
  if (reasonEntry.examples.length < 3) {
    reasonEntry.examples.push({
      peer: log.peer?.substring(0, 20) + (log.peer?.length > 20 ? '...' : ''),
      timestamp: log.timestamp,
      details: details
    });
  }
});

// 5. Выводим статистику по полученным GOODBYE
console.log('\n📥 GOODBYE, КОТОРЫЕ НАМ ОТПРАВИЛИ:');
console.log('-'.repeat(40));

const receivedReasons = Object.entries(reasons.received)
  .sort(([,a], [,b]) => b.count - a.count);

if (receivedReasons.length === 0) {
  console.log('  Нет полученных GOODBYE');
} else {
  receivedReasons.forEach(([reason, data]) => {
    const percent = ((data.count / goodbyeLogs.filter(l => l.type === 'PEER_GOODBYE_RECEIVED').length) * 100).toFixed(1);
    console.log(`\n  🔸 ${reason}:`);
    console.log(`     Количество: ${data.count} (${percent}%)`);
    console.log(`     Уникальных пиров: ${data.peers.size}`);
    
    // Примеры
    if (data.examples.length > 0) {
      console.log(`     Примеры пиров:`);
      data.examples.forEach(example => {
        console.log(`       - ${example.peer} в ${example.timestamp}`);
      });
    }
  });
}

// 6. Выводим статистику по отправленным GOODBYE
console.log('\n📤 GOODBYE, КОТОРЫЕ МЫ ОТПРАВИЛИ:');
console.log('-'.repeat(40));

const sentReasons = Object.entries(reasons.sent)
  .sort(([,a], [,b]) => b.count - a.count);

if (sentReasons.length === 0) {
  console.log('  Нет отправленных GOODBYE');
} else {
  sentReasons.forEach(([reason, data]) => {
    const percent = ((data.count / goodbyeLogs.filter(l => l.type === 'PEER_GOODBYE_SENT').length) * 100).toFixed(1);
    console.log(`\n  🔹 ${reason}:`);
    console.log(`     Количество: ${data.count} (${percent}%)`);
    console.log(`     Уникальных пиров: ${data.peers.size}`);
    
    // Примеры
    if (data.examples.length > 0) {
      console.log(`     Примеры пиров:`);
      data.examples.forEach(example => {
        console.log(`       - ${example.peer} в ${example.timestamp}`);
      });
    }
  });
}

// 7. Анализ временных паттернов
console.log('\n⏰ ВРЕМЕННЫЕ ПАТТЕРНЫ:');
console.log('-'.repeat(40));

if (goodbyeLogs.length > 0) {
  // Группируем по часам
  const hourly = {};
  goodbyeLogs.forEach(log => {
    const hour = new Date(log.timestamp).getHours();
    const hourStr = `${hour.toString().padStart(2, '0')}:00`;
    
    if (!hourly[hourStr]) hourly[hourStr] = 0;
    hourly[hourStr]++;
  });
  
  // Сортируем по времени
  const sortedHours = Object.entries(hourly)
    .sort(([a], [b]) => a.localeCompare(b));
  
  console.log('  GOODBYE по часам:');
  sortedHours.forEach(([hour, count]) => {
    const bar = '█'.repeat(Math.round(count / 2));
    console.log(`    ${hour}: ${count.toString().padStart(3)} ${bar}`);
  });
  
  // Периодичность
  const timestamps = goodbyeLogs.map(l => new Date(l.timestamp).getTime()).sort((a, b) => a - b);
  if (timestamps.length > 1) {
    const intervals = [];
    for (let i = 1; i < timestamps.length; i++) {
      intervals.push(timestamps[i] - timestamps[i-1]);
    }
    
    const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length / 1000;
    console.log(`\n  Средний интервал между GOODBYE: ${avgInterval.toFixed(1)} секунд`);
  }
}

// 8. Анализ пиров с повторными GOODBYE
console.log('\n👥 ПИРЫ С ПОВТОРНЫМИ GOODBYE:');
console.log('-'.repeat(40));

const peerGoodbyeCount = {};
goodbyeLogs.forEach(log => {
  if (log.peer && log.peer !== 'unknown') {
    peerGoodbyeCount[log.peer] = (peerGoodbyeCount[log.peer] || 0) + 1;
  }
});

const repeatPeers = Object.entries(peerGoodbyeCount)
  .filter(([, count]) => count > 1)
  .sort(([,a], [,b]) => b - a);

if (repeatPeers.length === 0) {
  console.log('  Нет пиров с повторными GOODBYE');
} else {
  console.log(`  Найдено пиров: ${repeatPeers.length}`);
  repeatPeers.slice(0, 10).forEach(([peer, count]) => {
    const shortPeer = peer.length > 25 ? peer.substring(0, 22) + '...' : peer;
    console.log(`    ${shortPeer.padEnd(30)}: ${count} GOODBYE`);
  });
}

// 9. Проверка корреляции с другими событиями
console.log('\n🔗 КОРРЕЛЯЦИЯ С ДРУГИМИ СОБЫТИЯМИ:');
console.log('-'.repeat(40));

// Для топ-5 пиров с GOODBYE проверяем, что было перед этим
const topGoodbyePeers = Object.entries(peerGoodbyeCount)
  .sort(([,a], [,b]) => b - a)
  .slice(0, 5);

if (topGoodbyePeers.length > 0) {
  console.log('  Что происходило с топ-пирами перед GOODBYE:');
  
  topGoodbyePeers.forEach(([peer, goodbyeCount]) => {
    console.log(`\n  🔸 Пир: ${peer.substring(0, 20)}... (${goodbyeCount} GOODBYE)`);
    
    // Находим все события этого пира
    const peerEvents = logs.filter(l => l.peer === peer);
    const eventTypes = {};
    peerEvents.forEach(event => {
      eventTypes[event.type] = (eventTypes[event.type] || 0) + 1;
    });
    
    // Сортируем по количеству
    const sortedEvents = Object.entries(eventTypes)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5);
    
    sortedEvents.forEach(([type, count]) => {
      console.log(`     ${type.padEnd(25)}: ${count}`);
    });
    
    // Проверяем, были ли ошибки перед GOODBYE
    const peerGoodbyeTimes = goodbyeLogs
      .filter(l => l.peer === peer && l.type === 'PEER_GOODBYE_RECEIVED')
      .map(l => new Date(l.timestamp).getTime());
    
    if (peerGoodbyeTimes.length > 0) {
      const beforeGoodbye = peerEvents.filter(event => {
        const eventTime = new Date(event.timestamp).getTime();
        return eventTime < peerGoodbyeTimes[0] && 
               eventTime > peerGoodbyeTimes[0] - 60000; // За минуту до
      });
      
      const errorBefore = beforeGoodbye.filter(e => 
        e.type.includes('ERROR') || 
        e.type.includes('FAIL') ||
        e.type === 'PEER_PING_ROUNDTRIP'
      );
      
      if (errorBefore.length > 0) {
        console.log(`     ⚠️  Перед GOODBYE были: ${errorBefore.map(e => e.type).join(', ')}`);
      }
    }
  });
}

// 10. Вывод рекомендаций
console.log('\n📋 РЕКОМЕНДАЦИИ:');
console.log('-'.repeat(40));

const recommendations = [];

// Анализируем данные для рекомендаций
const totalGoodbye = goodbyeLogs.length;
const totalLogs = logs.length;
const goodbyeRate = (totalGoodbye / totalLogs * 100).toFixed(2);

if (goodbyeRate > 5) {
  recommendations.push(`⚠️  Высокий уровень GOODBYE (${goodbyeRate}% всех событий)`);
}

if (repeatPeers.length > 10) {
  recommendations.push(`⚠️  Много повторных GOODBYE от одних и тех же пиров (${repeatPeers.length})`);
}

const unknownReasons = Object.keys(reasons.received).filter(r => r === 'UNKNOWN').length +
                       Object.keys(reasons.sent).filter(r => r === 'UNKNOWN').length;
if (unknownReasons > 0) {
  recommendations.push(`🔍 ${unknownReasons} GOODBYE с неизвестной причиной - нужен детальный анализ`);
}

// Проверяем конкретные причины
const specificIssues = [];
Object.entries(reasons.received).forEach(([reason, data]) => {
  if (reason.includes('TOO_MANY')) {
    specificIssues.push(`📈 Пиры жалуются на "too many peers": ${data.count} раз`);
  }
  if (reason.includes('BANNED')) {
    specificIssues.push(`🚫 Нас забанили: ${data.count} раз`);
  }
  if (reason.includes('SYNC')) {
    specificIssues.push(`🔄 Проблемы синхронизации: ${data.count} раз`);
  }
});

// Формируем вывод
if (recommendations.length === 0 && specificIssues.length === 0) {
  console.log('  ✅ Уровень GOODBYE в норме, критических проблем не обнаружено');
} else {
  if (recommendations.length > 0) {
    recommendations.forEach((rec, i) => {
      console.log(`  ${i+1}. ${rec}`);
    });
  }
  
  if (specificIssues.length > 0) {
    console.log('\n  🎯 Конкретные проблемы:');
    specificIssues.forEach((issue, i) => {
      console.log(`     • ${issue}`);
    });
  }
  
  console.log('\n  💡 Действия:');
  console.log('     1. Проверьте логи Lodestar на ошибки соединений');
  console.log('     2. Убедитесь, что не исчерпаны лимиты подключений');
  console.log('     3. Мониторьте стабильность сети');
}

console.log('\n' + '='.repeat(60));
console.log('✅ Анализ GOODBYE завершен');
