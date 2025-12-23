#!/bin/bash

# Останавливаем все
echo "🛑 Останавливаем все процессы..."
pkill -f "lodestar"
sleep 5

# Убиваем процессы на портах на всякий случай
echo "🧹 Освобождаем порты..."
sudo fuser -k 9000/tcp 2>/dev/null
sudo fuser -k 9001/tcp 2>/dev/null
sudo fuser -k 9596/tcp 2>/dev/null
sudo fuser -k 9597/tcp 2>/dev/null

# Очищаем данные
echo "🗑️ Очищаем данные..."
rm -rf ./lodestar-node-1
rm -rf ./lodestar-node-2

# Проверяем порты
echo "🔍 Проверяем порты перед запуском..."
nc -z localhost 9000 && echo "❌ Порт 9000 занят" || echo "✅ Порт 9000 свободен"
nc -z localhost 9001 && echo "❌ Порт 9001 занят" || echo "✅ Порт 9001 свободен"
nc -z localhost 9596 && echo "❌ Порт 9596 занят" || echo "✅ Порт 9596 свободен"
nc -z localhost 9597 && echo "❌ Порт 9597 занят" || echo "✅ Порт 9597 свободен"

GENESIS_TIME=$(date +%s)
echo "🕒 Genesis time: $GENESIS_TIME"

echo "🚀 Запускаем ноду 1 с подробным логированием..."
./lodestar dev \
  --genesisValidators 8 \
  --startValidators 0..7 \
  --enr.ip 127.0.0.1 \
  --enr.udp 9000 \
  --dataDir ./lodestar-node-1 \
  --genesisTime $GENESIS_TIME \
  --logLevel debug \
  --reset > node1_debug.log 2>&1 &

echo "⏳ Ждем 30 секунд..."
sleep 30

echo "📡 Проверяем ноду 1..."
if curl -s http://localhost:9596/eth/v1/node/identity >/dev/null; then
  echo "✅ Нода 1 работает"
  ENR=$(curl -s http://localhost:9596/eth/v1/node/identity | jq -r '.data.enr')
  echo "📋 ENR получен"
else
  echo "❌ Нода 1 не запустилась"
  echo "Логи ноды 1:"
  tail -n 20 node1_debug.log
  exit 1
fi

echo "🎯 Запускаем ноду 2 с подробным логированием..."
./lodestar dev \
  --genesisValidators 8 \
  --dataDir ./lodestar-node-2 \
  --port 9001 \
  --rest.port 9597 \
  --bootnodes "$ENR" \
  --genesisTime $GENESIS_TIME \
  --logLevel debug \
  --reset > node2_debug.log 2>&1 &

echo "⏳ Ждем 20 секунд для подключения..."
sleep 20

echo ""
echo "=== 🔍 РЕЗУЛЬТАТ ==="
PEERS1=$(curl -s http://localhost:9596/eth/v1/node/peers | jq '.data | length' 2>/dev/null || echo "ошибка")
PEERS2=$(curl -s http://localhost:9597/eth/v1/node/peers | jq '.data | length' 2>/dev/null || echo "ошибка")

echo "Пиров у ноды 1: $PEERS1"
echo "Пиров у ноды 2: $PEERS2"

echo ""
echo "📊 Ключевые логи ноды 1:"
tail -n 10 node1_debug.log | grep -E "peer|Peer|connected|Connected"

echo ""
echo "📊 Ключевые логи ноды 2:"
tail -n 10 node2_debug.log | grep -E "peer|Peer|connected|Connected|error|Error"

if [ "$PEERS1" -eq 1 ] && [ "$PEERS2" -eq 1 ]; then
  echo ""
  echo "🎉 УСПЕХ! Ноды подключены!"
else
  echo ""
  echo "❌ Проблема с подключением"
  echo "Подробные логи ноды 2 (первые ошибки):"
  grep -A 5 -B 5 "error\|Error" node2_debug.log | head -n 20
fi
