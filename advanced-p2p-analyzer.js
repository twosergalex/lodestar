#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const dns = require('dns').promises;

// ================= КОНФИГУРАЦИЯ =================
const CONFIG = {
  LOG_DIR: 'p2p-sniffer-logs',
  ANALYZE_LATEST_ONLY: false,
  GEO_CACHE_FILE: '.geo_cache.json',
  ENABLE_DNS_LOOKUP: true,
  ENABLE_IP_ANALYSIS: true,
  TOP_LIMIT: 15
};

// ================= КЛАСС ГЕО-КЭША =================
class GeoCache {
  constructor(cacheFile) {
    this.cacheFile = cacheFile;
    this.cache = this.loadCache();
  }

  loadCache() {
    try {
      if (fs.existsSync(this.cacheFile)) {
        return JSON.parse(fs.readFileSync(this.cacheFile, 'utf-8'));
      }
    } catch (e) {}
    return {};
  }

  saveCache() {
    try {
      fs.writeFileSync(this.cacheFile, JSON.stringify(this.cache, null, 2));
    } catch (e) {}
  }

  get(ip) {
    return this.cache[ip];
  }

  set(ip, data) {
    this.cache[ip] = {
      ...data,
      timestamp: Date.now()
    };
    this.saveCache();
  }

  getStats() {
    const ips = Object.keys(this.cache);
    return {
      total: ips.length,
      countries: new Set(ips.map(ip => this.cache[ip]?.country).filter(Boolean)).size,
      isps: new Set(ips.map(ip => this.cache[ip]?.isp).filter(Boolean)).size
    };
  }
}

// ================= БЕЗОПАСНЫЕ УТИЛИТЫ =================
const utils = {
  formatNumber: (num) => {
    if (isNaN(num)) return '0';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  },
  
  formatDuration: (ms) => {
    const hours = Math.floor(ms / 3600000);
    const minutes = Math.floor((ms % 3600000) / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    return hours > 0 ? `${hours}ч ${minutes}м` : `${minutes}м ${seconds}с`;
  },
  
  getForkName: (forkDigest) => {
    const forks = {
      '0x74d01459': 'Goerli',
      '0x90000080': 'Sepolia',
      '0x00000000': 'Mainnet',
      '0x01000000': 'Altair',
      '0x02000000': 'Bellatrix',
      '0x03000000': 'Capella',
      '0x04000000': 'Deneb'
    };
    return forks[forkDigest] || (forkDigest || 'unknown');
  },
  
  getPeerShort: (peer) => {
    if (!peer || peer === 'unknown') return 'unknown';
    return peer.length > 20 ? peer.substring(0, 17) + '...' : peer;
  },
  
  extractIP: (address) => {
    if (!address) return null;
    const match = address.match(/\/ip4\/(\d+\.\d+\.\d+\.\d+)/);
    return match ? match[1] : null;
  },
  
  classifyIP: (ip) => {
    if (!ip) return 'unknown';
    
    if (ip.startsWith('10.') || ip.startsWith('192.168.') || ip.startsWith('172.')) {
      return 'private';
    }
    
    if (ip === '127.0.0.1' || ip === '::1') return 'localhost';
    
    const cloudPatterns = [
      { pattern: /\.amazonaws\./, name: 'AWS' },
      { pattern: /\.googleapis\./, name: 'Google Cloud' },
      { pattern: /\.azure\./, name: 'Azure' },
      { pattern: /\.digitalocean\./, name: 'DigitalOcean' },
      { pattern: /\.linode\./, name: 'Linode' },
      { pattern: /\.hetzner\./, name: 'Hetzner' }
    ];
    
    return 'public';
  },
  
  async resolvePTR(ip) {
    if (!CONFIG.ENABLE_DNS_LOOKUP) return null;
    
    try {
      const hostnames = await dns.reverse(ip);
      return hostnames[0] || null;
    } catch (e) {
      return null;
    }
  },
  
  analyzeTimeline: (logs) => {
    const timeline = {};
    logs.forEach(log => {
      const date = new Date(log.timestamp);
      const hour = date.getHours();
      const minute = date.getMinutes();
      const timeSlot = `${hour.toString().padStart(2, '0')}:${Math.floor(minute / 10) * 10}`;
      
      if (!timeline[timeSlot]) timeline[timeSlot] = { total: 0, byType: {} };
      timeline[timeSlot].total++;
      timeline[timeSlot].byType[log.type] = (timeline[timeSlot].byType[log.type] || 0) + 1;
    });
    
    return Object.entries(timeline)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([time, data]) => ({ time, ...data }));
  },
  
  calculateSessionStats: (logs) => {
    const peerSessions = {};
    
    logs.forEach(log => {
      if (!log.peer || log.peer === 'unknown') return;
      
      if (!peerSessions[log.peer]) {
        peerSessions[log.peer] = {
          peer: log.peer,
          firstSeen: new Date(log.timestamp).getTime(),
          lastSeen: new Date(log.timestamp).getTime(),
          events: 0,
          types: new Set(),
          ips: new Set()
        };
      }
      
      const session = peerSessions[log.peer];
      const logTime = new Date(log.timestamp).getTime();
      
      session.lastSeen = Math.max(session.lastSeen, logTime);
      session.firstSeen = Math.min(session.firstSeen, logTime);
      session.events++;
      session.types.add(log.type);
      
      if (log.details?.address) {
        const ip = utils.extractIP(log.details.address);
        if (ip) session.ips.add(ip);
      }
    });
    
    const sessions = Object.values(peerSessions);
    const durations = sessions.map(s => s.lastSeen - s.firstSeen);
    
    return {
      totalSessions: sessions.length,
      avgDuration: durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 0,
      maxDuration: durations.length > 0 ? Math.max(...durations) : 0,
      minDuration: durations.length > 0 ? Math.min(...durations) : 0,
      avgEventsPerSession: sessions.length > 0 ? sessions.reduce((a, b) => a + b.events, 0) / sessions.length : 0,
      sessionsByDuration: sessions.map(s => ({
        peer: s.peer,
        duration: s.lastSeen - s.firstSeen,
        events: s.events,
        ips: s.ips.size
      })).sort((a, b) => b.duration - a.duration)
    };
  }
};

// ================= АНАЛИЗАТОРЫ =================
const analyzers = {
  analyzeNetworkEvents: (logs) => {
    const eventsByType = {};
    const peerConnections = new Set();
    const connectionDirections = { inbound: 0, outbound: 0 };
    
    logs.forEach(log => {
      eventsByType[log.type] = (eventsByType[log.type] || 0) + 1;
      
      if (log.type === 'PEER_TCP_CONNECTED' && log.details) {
        if (log.peer) peerConnections.add(log.peer);
        if (log.details.direction) {
          connectionDirections[log.details.direction] = 
            (connectionDirections[log.details.direction] || 0) + 1;
        }
      }
    });
    
    return {
      totalEvents: logs.length,
      uniqueEventTypes: Object.keys(eventsByType).length,
      eventsByType,
      uniquePeersConnected: peerConnections.size,
      connectionDirections
    };
  },
  
  analyzeStatusAndSync: (logs) => {
    const statusLogs = logs.filter(l => l.type === 'PEER_STATUS');
    if (statusLogs.length === 0) return null;
    
    const forks = {};
    const clients = {};
    const slots = [];
    const epochs = [];
    
    statusLogs.forEach(log => {
      if (!log.details) return;
      
      const d = log.details;
      
      if (d.forkDigest) {
        forks[d.forkDigest] = (forks[d.forkDigest] || 0) + 1;
      }
      
      if (d.client) {
        clients[d.client] = (clients[d.client] || 0) + 1;
      }
      
      const slot = parseInt(d.headSlot);
      const epoch = parseInt(d.finalizedEpoch);
      if (!isNaN(slot)) slots.push(slot);
      if (!isNaN(epoch)) epochs.push(epoch);
    });
    
    const sortedSlots = slots.sort((a, b) => a - b);
    const sortedEpochs = epochs.sort((a, b) => a - b);
    
    return {
      totalStatuses: statusLogs.length,
      forks: Object.entries(forks)
        .sort(([,a], [,b]) => b - a)
        .map(([fork, count]) => ({
          fork,
          name: utils.getForkName(fork),
          count,
          percent: ((count / statusLogs.length) * 100).toFixed(1)
        })),
      clients: Object.entries(clients)
        .sort(([,a], [,b]) => b - a)
        .slice(0, CONFIG.TOP_LIMIT),
      slotStats: {
        min: sortedSlots.length > 0 ? sortedSlots[0] : 0,
        max: sortedSlots.length > 0 ? sortedSlots[sortedSlots.length - 1] : 0,
        avg: slots.length > 0 ? Math.round(slots.reduce((a, b) => a + b, 0) / slots.length) : 0,
        median: sortedSlots.length > 0 ? sortedSlots[Math.floor(sortedSlots.length / 2)] : 0
      },
      epochStats: {
        min: sortedEpochs.length > 0 ? sortedEpochs[0] : 0,
        max: sortedEpochs.length > 0 ? sortedEpochs[sortedEpochs.length - 1] : 0,
        avg: epochs.length > 0 ? Math.round(epochs.reduce((a, b) => a + b, 0) / epochs.length) : 0
      },
      syncHealth: {
        zeroSlots: slots.filter(s => s === 0).length,
        stalePeers: slots.filter(s => sortedSlots.length > 0 && s < sortedSlots[sortedSlots.length - 1] - 1000).length
      }
    };
  },
  
  analyzeErrors: (logs) => {
    const errorKeywords = ['ERROR', 'FAIL', 'TIMEOUT', 'REJECT', 'INVALID', 'MALFORMED'];
    const suspiciousTypes = ['PEER_GOODBYE_RECEIVED', 'PEER_BANNED', 'PEER_DROPPED'];
    
    const errorLogs = logs.filter(log => {
      if (errorKeywords.some(keyword => 
        log.type.includes(keyword) || 
        (log.details && JSON.stringify(log.details).includes(keyword))
      )) return true;
      
      if (suspiciousTypes.includes(log.type)) return true;
      
      if (log.details && (
        (log.details.reasonCode && log.details.reasonCode !== '0') ||
        log.details.error ||
        log.details.failure
      )) return true;
      
      return false;
    });
    
    const errorsByType = {};
    const errorsByPeer = {};
    
    errorLogs.forEach(log => {
      errorsByType[log.type] = (errorsByType[log.type] || 0) + 1;
      
      if (log.peer && log.peer !== 'unknown') {
        errorsByPeer[log.peer] = (errorsByPeer[log.peer] || 0) + 1;
      }
    });
    
    const goodbyeLogs = logs.filter(l => l.type === 'PEER_GOODBYE_RECEIVED');
    const goodbyeReasons = {};
    
    goodbyeLogs.forEach(log => {
      if (log.details?.reasonCode) {
        const reason = log.details.reasonText || `Код ${log.details.reasonCode}`;
        goodbyeReasons[reason] = (goodbyeReasons[reason] || 0) + 1;
      }
    });
    
    return {
      totalErrors: errorLogs.length,
      errorRate: logs.length > 0 ? ((errorLogs.length / logs.length) * 100).toFixed(2) : '0',
      errorsByType: Object.entries(errorsByType).sort(([,a], [,b]) => b - a),
      topErrorPeers: Object.entries(errorsByPeer).sort(([,a], [,b]) => b - a).slice(0, 10),
      goodbyeAnalysis: {
        total: goodbyeLogs.length,
        reasons: Object.entries(goodbyeReasons).sort(([,a], [,b]) => b - a)
      }
    };
  },
  
  analyzeIPs: async (logs, geoCache) => {
    if (!CONFIG.ENABLE_IP_ANALYSIS) return null;
    
    const ipMap = new Map();
    const uniqueIPs = new Set();
    
    logs.forEach(log => {
      if (log.details?.address) {
        const ip = utils.extractIP(log.details.address);
        if (ip) {
          uniqueIPs.add(ip);
          
          if (!ipMap.has(ip)) {
            ipMap.set(ip, {
              ip,
              count: 0,
              firstSeen: null,
              lastSeen: null,
              peers: new Set(),
              eventTypes: new Set(),
              ports: new Set()
            });
          }
          
          const record = ipMap.get(ip);
          record.count++;
          if (log.peer) record.peers.add(log.peer);
          record.eventTypes.add(log.type);
          
          const timestamp = new Date(log.timestamp).getTime();
          if (!record.firstSeen || timestamp < record.firstSeen) record.firstSeen = timestamp;
          if (!record.lastSeen || timestamp > record.lastSeen) record.lastSeen = timestamp;
          
          const portMatch = log.details.address.match(/tcp\/(\d+)/);
          if (portMatch) record.ports.add(portMatch[1]);
        }
      }
    });
    
    const classifications = {
      total: uniqueIPs.size,
      byType: {}
    };
    
    for (const ip of uniqueIPs) {
      const type = utils.classifyIP(ip);
      classifications.byType[type] = (classifications.byType[type] || 0) + 1;
      
      if (CONFIG.ENABLE_DNS_LOOKUP) {
        const ptr = await utils.resolvePTR(ip);
        if (ptr) {
          const record = ipMap.get(ip);
          if (record) record.hostname = ptr;
        }
      }
    }
    
    const topIPs = Array.from(ipMap.values())
      .sort((a, b) => b.count - a.count)
      .slice(0, CONFIG.TOP_LIMIT)
      .map(record => ({
        ip: record.ip,
        count: record.count,
        hostname: record.hostname || 'N/A',
        peers: record.peers.size,
        eventTypes: record.eventTypes.size,
        ports: Array.from(record.ports).slice(0, 3).join(', '),
        duration: record.firstSeen && record.lastSeen ? 
          utils.formatDuration(record.lastSeen - record.firstSeen) : 'N/A'
      }));
    
    return {
      uniqueIPs: uniqueIPs.size,
      classifications,
      topIPs,
      ipStats: {
        avgEventsPerIP: uniqueIPs.size > 0 ? logs.length / uniqueIPs.size : 0,
        maxEventsPerIP: topIPs.length > 0 ? topIPs[0].count : 0
      }
    };
  },
  
  analyzePerformance: (logs) => {
    const pingLogs = logs.filter(l => l.type === 'PEER_PING_ROUNDTRIP');
    const latencies = pingLogs.map(l => l.details?.latencyMs).filter(Boolean);
    
    if (latencies.length === 0) return null;
    
    const sortedLatencies = latencies.sort((a, b) => a - b);
    const avgLatency = latencies.reduce((a, b) => a + b, 0) / latencies.length;
    
    return {
      totalPings: pingLogs.length,
      latencyStats: {
        min: sortedLatencies[0],
        max: sortedLatencies[sortedLatencies.length - 1],
        avg: Math.round(avgLatency),
        median: sortedLatencies[Math.floor(sortedLatencies.length / 2)],
        p95: sortedLatencies[Math.floor(sortedLatencies.length * 0.95)]
      },
      successRate: {
        successful: pingLogs.filter(l => l.details?.success !== false).length,
        failed: pingLogs.filter(l => l.details?.success === false).length,
        rate: pingLogs.length > 0 ? 
          ((pingLogs.filter(l => l.details?.success !== false).length / pingLogs.length) * 100).toFixed(1) : '0'
      }
    };
  },
  
  analyzeTemporalPatterns: (logs) => {
    if (logs.length < 10) return null;
    
    const timeline = utils.analyzeTimeline(logs);
    const sessionStats = utils.calculateSessionStats(logs);
    
    const peakPeriods = timeline
      .filter(period => period.total > 10)
      .sort((a, b) => b.total - a.total)
      .slice(0, 5);
    
    const hourlyDistribution = {};
    logs.forEach(log => {
      const hour = new Date(log.timestamp).getHours();
      if (!hourlyDistribution[hour]) {
        hourlyDistribution[hour] = { total: 0, byType: {} };
      }
      hourlyDistribution[hour].total++;
      hourlyDistribution[hour].byType[log.type] = 
        (hourlyDistribution[hour].byType[log.type] || 0) + 1;
    });
    
    return {
      timeline: timeline.slice(0, 20),
      peakPeriods,
      hourlyDistribution: Object.entries(hourlyDistribution)
        .map(([hour, data]) => ({ hour: parseInt(hour), ...data }))
        .sort((a, b) => a.hour - b.hour),
      sessionStats: {
        ...sessionStats,
        longestSessions: sessionStats.sessionsByDuration.slice(0, 5)
      },
      eventRate: {
        eventsPerMinute: timeline.length > 0 ? logs.length / (timeline.length * 10) : 0,
        peakRate: peakPeriods.length > 0 ? peakPeriods[0].total / 10 : 0
      }
    };
  },
  
  analyzeAttestations: (logs) => {
    const attestationLogs = logs.filter(l => l.type === 'BEACON_ATTESTATION_RECEIVED');
    if (attestationLogs.length === 0) return null;
    
    const attestationsByPeer = {};
    const slotDistribution = {};
    
    attestationLogs.forEach(log => {
      if (log.peer && log.peer !== 'unknown') {
        attestationsByPeer[log.peer] = (attestationsByPeer[log.peer] || 0) + 1;
      }
      
      if (log.details?.slot) {
        const slot = parseInt(log.details.slot);
        if (!isNaN(slot)) {
          const slotGroup = Math.floor(slot / 100) * 100;
          slotDistribution[slotGroup] = (slotDistribution[slotGroup] || 0) + 1;
        }
      }
    });
    
    const sortedPeers = Object.entries(attestationsByPeer).sort(([,a], [,b]) => b - a);
    
    return {
      totalAttestations: attestationLogs.length,
      uniquePeers: Object.keys(attestationsByPeer).length,
      topAttestingPeers: sortedPeers.slice(0, 10),
      suspiciousPeers: sortedPeers.filter(([,count]) => count > 10),
      slotDistribution: Object.entries(slotDistribution)
        .sort(([a], [b]) => parseInt(a) - parseInt(b))
        .slice(0, 10)
    };
  }
};

// ================= ОТЧЕТ =================
class ReportGenerator {
  constructor() {
    this.sections = [];
  }
  
  addSection(title, content, level = 1) {
    this.sections.push({ title, content, level });
  }
  
  print() {
    console.log('\n' + '='.repeat(80));
    console.log('🚀 ПРОДВИНУТЫЙ P2P АНАЛИЗАТОР СЕТИ');
    console.log('='.repeat(80) + '\n');
    
    this.sections.forEach(section => {
      const indent = '  '.repeat(section.level);
      console.log(`\n${indent}${'▬'.repeat(3)} ${section.title.toUpperCase()}`);
      console.log(`${indent}${'─'.repeat(60)}`);
      
      if (typeof section.content === 'string') {
        console.log(`${indent}${section.content}`);
      } else if (Array.isArray(section.content)) {
        section.content.forEach(item => {
          if (typeof item === 'string') {
            console.log(`${indent}  ${item}`);
          }
        });
      }
    });
    
    console.log('\n' + '='.repeat(80));
    console.log('✅ Анализ завершен.');
    console.log('='.repeat(80));
  }
}

// ================= ОСНОВНАЯ ФУНКЦИЯ =================
async function main() {
  const report = new ReportGenerator();
  const geoCache = new GeoCache(CONFIG.GEO_CACHE_FILE);
  
  try {
    report.addSection('📂 Загрузка данных', 'Поиск файлов логов...', 0);
    
    const files = fs.readdirSync(CONFIG.LOG_DIR)
      .filter(f => f.startsWith('p2p-') && f.endsWith('.jsonl'))
      .sort();
    
    if (files.length === 0) {
      console.log('❌ Нет файлов логов в директории', CONFIG.LOG_DIR);
      return;
    }
    
    const filesToAnalyze = CONFIG.ANALYZE_LATEST_ONLY 
      ? [files[files.length - 1]] 
      : files;
    
    let allLogs = [];
    filesToAnalyze.forEach(file => {
      const filePath = path.join(CONFIG.LOG_DIR, file);
      const content = fs.readFileSync(filePath, 'utf-8');
      const logs = content.split('\n')
        .filter(line => line.trim())
        .map(line => {
          try {
            const log = JSON.parse(line);
            if (!log.peer) log.peer = 'unknown';
            if (!log.type) log.type = 'UNKNOWN';
            if (!log.timestamp) log.timestamp = new Date().toISOString();
            if (!log.details) log.details = {};
            return log;
          } catch (e) {
            return null;
          }
        })
        .filter(log => log !== null);
      
      allLogs = allLogs.concat(logs);
    });
    
    if (allLogs.length === 0) {
      console.log('❌ Нет валидных записей');
      return;
    }
    
    report.addSection('📈 Общая статистика', [
      `📅 Период: ${filesToAnalyze[0].replace('p2p-', '').replace('.jsonl', '')}`,
      filesToAnalyze.length > 1 ? `   до ${filesToAnalyze[filesToAnalyze.length - 1].replace('p2p-', '').replace('.jsonl', '')}` : '',
      `📊 Всего событий: ${utils.formatNumber(allLogs.length)}`,
      `📁 Файлов: ${filesToAnalyze.length}`,
      `⏳ Длительность: ${utils.formatDuration(
        new Date(allLogs[allLogs.length - 1].timestamp) - new Date(allLogs[0].timestamp)
      )}`
    ], 1);
    
    const networkAnalysis = analyzers.analyzeNetworkEvents(allLogs);
    report.addSection('🌐 Сетевая активность', [
      `Уникальных типов событий: ${networkAnalysis.uniqueEventTypes}`,
      `Подключённых пиров: ${networkAnalysis.uniquePeersConnected}`,
      `Входящих подключений: ${networkAnalysis.connectionDirections.inbound || 0}`,
      `Исходящих подключений: ${networkAnalysis.connectionDirections.outbound || 0}`
    ], 1);
    
    const topEvents = Object.entries(networkAnalysis.eventsByType)
      .sort(([,a], [,b]) => b - a)
      .slice(0, CONFIG.TOP_LIMIT)
      .map(([type, count]) => 
        `${type.padEnd(30)}: ${utils.formatNumber(count).padStart(6)} (${((count / allLogs.length) * 100).toFixed(1)}%)`
      );
    
    report.addSection('🎯 Топ событий', topEvents, 2);
    
    const statusAnalysis = analyzers.analyzeStatusAndSync(allLogs);
    if (statusAnalysis) {
      report.addSection('🔗 Состояние сети', [
        `Статусов: ${statusAnalysis.totalStatuses}`,
        `Минимальный слот: ${utils.formatNumber(statusAnalysis.slotStats.min)}`,
        `Максимальный слот: ${utils.formatNumber(statusAnalysis.slotStats.max)}`,
        `Средний слот: ${utils.formatNumber(statusAnalysis.slotStats.avg)}`,
        `Пиров с нулевым слотом: ${statusAnalysis.syncHealth.zeroSlots}`,
        `Отстающих пиров: ${statusAnalysis.syncHealth.stalePeers}`
      ], 1);
      
      const forks = statusAnalysis.forks.map(f => 
        `${f.name.padEnd(15)}: ${f.count} (${f.percent}%)`
      );
      report.addSection('Форки', forks, 2);
      
      const topClients = statusAnalysis.clients.map(([client, count]) => 
        `${client.padEnd(20)}: ${count} (${((count / statusAnalysis.totalStatuses) * 100).toFixed(1)}%)`
      );
      report.addSection('Клиенты', topClients, 2);
    }
    
    const errorAnalysis = analyzers.analyzeErrors(allLogs);
    if (errorAnalysis.totalErrors > 0) {
      report.addSection('⚠️  Ошибки', [
        `Всего ошибок: ${errorAnalysis.totalErrors}`,
        `Уровень ошибок: ${errorAnalysis.errorRate}%`,
        `GOODBYE сообщений: ${errorAnalysis.goodbyeAnalysis.total}`
      ], 1);
      
      if (errorAnalysis.errorsByType.length > 0) {
        const topErrors = errorAnalysis.errorsByType
          .slice(0, 5)
          .map(([type, count]) => `${type}: ${count}`);
        report.addSection('Типы ошибок', topErrors, 2);
      }
    } else {
      report.addSection('✅ Ошибок не обнаружено', '', 1);
    }
    
    if (CONFIG.ENABLE_IP_ANALYSIS) {
      const ipAnalysis = await analyzers.analyzeIPs(allLogs, geoCache);
      if (ipAnalysis) {
        report.addSection('🌍 IP-адреса', [
          `Уникальных IP: ${ipAnalysis.uniqueIPs}`,
          `Среднее событий на IP: ${ipAnalysis.ipStats.avgEventsPerIP.toFixed(1)}`,
          `Максимум событий с одного IP: ${ipAnalysis.ipStats.maxEventsPerIP}`
        ], 1);
        
        const ipTypes = Object.entries(ipAnalysis.classifications.byType)
          .map(([type, count]) => 
            `${type.padEnd(15)}: ${count} (${((count / ipAnalysis.uniqueIPs) * 100).toFixed(1)}%)`
          );
        report.addSection('Классификация IP', ipTypes, 2);
        
        if (ipAnalysis.topIPs.length > 0) {
          const topIPs = ipAnalysis.topIPs.map(ip => 
            `${ip.ip.padEnd(18)}: ${ip.count} событий, ${ip.peers} пиров`
          );
          report.addSection('Топ IP', topIPs, 2);
        }
      }
    }
    
    const perfAnalysis = analyzers.analyzePerformance(allLogs);
    if (perfAnalysis) {
      report.addSection('⚡ Производительность', [
        `Ping-запросов: ${perfAnalysis.totalPings}`,
        `Средняя задержка: ${perfAnalysis.latencyStats.avg} мс`,
        `Мин/Макс: ${perfAnalysis.latencyStats.min}/${perfAnalysis.latencyStats.max} мс`,
        `Успешность: ${perfAnalysis.successRate.rate}%`
      ], 1);
    }
    
    const temporalAnalysis = analyzers.analyzeTemporalPatterns(allLogs);
    if (temporalAnalysis) {
      report.addSection('⏱️  Временные паттерны', [
        `Событий в минуту: ${temporalAnalysis.eventRate.eventsPerMinute.toFixed(1)}`,
        `Пиковая активность: ${temporalAnalysis.eventRate.peakRate.toFixed(1)}/мин`,
        `Всего сессий: ${temporalAnalysis.sessionStats.totalSessions}`,
        `Средняя длительность сессии: ${utils.formatDuration(temporalAnalysis.sessionStats.avgDuration)}`
      ], 1);
      
      if (temporalAnalysis.peakPeriods.length > 0) {
        const peaks = temporalAnalysis.peakPeriods.map((period, i) => 
          `${(i + 1).toString().padStart(2)}. ${period.time}: ${period.total} событий`
        );
        report.addSection('Пиковые периоды', peaks, 2);
      }
      
      if (temporalAnalysis.sessionStats.longestSessions.length > 0) {
        const longestSessions = temporalAnalysis.sessionStats.longestSessions.map((session, i) => {
          const peerStr = utils.getPeerShort(session.peer);
          return `${(i + 1).toString().padStart(2)}. ${peerStr}: ${utils.formatDuration(session.duration)}, ${session.events} событий`;
        });
        report.addSection('Самые длинные сессии', longestSessions, 2);
      }
    }
    
    const attestationAnalysis = analyzers.analyzeAttestations(allLogs);
    if (attestationAnalysis) {
      report.addSection('🎯 Аттестации', [
        `Всего аттестаций: ${attestationAnalysis.totalAttestations}`,
        `Уникальных пиров: ${attestationAnalysis.uniquePeers}`,
        `Среднее на пир: ${(attestationAnalysis.totalAttestations / attestationAnalysis.uniquePeers).toFixed(1)}`,
        `Подозрительных пиров: ${attestationAnalysis.suspiciousPeers.length}`
      ], 1);
      
      if (attestationAnalysis.topAttestingPeers.length > 0) {
        const topAttesters = attestationAnalysis.topAttestingPeers.map(([peer, count], i) => {
          const peerStr = utils.getPeerShort(peer);
          return `${(i + 1).toString().padStart(2)}. ${peerStr}: ${count} аттестаций`;
        });
        report.addSection('Топ аттестаторов', topAttesters, 2);
      }
    }
    
    const recommendations = [];
    if (statusAnalysis?.syncHealth.zeroSlots > 0) {
      recommendations.push('⚠️  Есть пиры с headSlot=0 (не синхронизированы)');
    }
    if (errorAnalysis.totalErrors > 10) {
      recommendations.push(`⚠️  Много ошибок (${errorAnalysis.errorRate}%)`);
    }
    if (attestationAnalysis?.suspiciousPeers?.length > 0) {
      recommendations.push('⚠️  Обнаружены пиры с аномальным числом аттестаций');
    }
    if (recommendations.length === 0) {
      recommendations.push('✅ Система работает стабильно');
    }
    
    report.addSection('📋 Рекомендации', recommendations, 1);
    
    report.print();
    
  } catch (error) {
    console.error('❌ Ошибка:', error.message);
    console.error('Стек:', error.stack);
  }
}

// ================= ЗАПУСК =================
if (require.main === module) {
  main().catch(console.error);
}
