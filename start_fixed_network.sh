#!/bin/bash

# Останавливаем старые ноды
echo "🛑 Останавливаем старые процессы Lodestar..."
pkill -f "lodestar dev" 2>/dev/null
sleep 3

# Очищаем старые данные
echo "🧹 Очищаем старые данные..."
rm -rf ./lodestar-node-1
rm -rf ./lodestar-node-2

# Устанавливаем ОДНО время genesis для обеих нод
GENESIS_TIME=$(date +%s)
echo "🕒 Устанавливаем общее время genesis: $GENESIS_TIME"

echo "🚀 Запускаем ноду 1..."
./lodestar dev \
  --genesisValidators 8 \
  --startValidators 0..7 \
  --enr.ip 127.0.0.1 \
  --enr.udp 9000 \
  --dataDir ./lodestar-node-1 \
  --genesisTime $GENESIS_TIME \
  --reset > node1.log 2>&1 &

echo "⏳ Ждем 25 секунд для полной инициализации..."
sleep 25

echo "📡 Проверяем ноду 1..."
if curl -s http://localhost:9596/eth/v1/node/identity >/dev/null; then
  echo "✅ Нода 1 работает"
else
  echo "❌ Нода 1 не запустилась"
  echo "Логи ноды 1:"
  tail -n 10 node1.log
  exit 1
fi

echo "🔗 Получаем ENR..."
ENR=$(curl -s http://localhost:9596/eth/v1/node/identity | jq -r '.data.enr')

if [ -z "$ENR" ]; then
  echo "❌ Не удалось получить ENR"
  exit 1
fi

echo "✅ ENR получен (${#ENR} символов)"

echo "🎯 Запускаем ноду 2..."
./lodestar dev \
  --genesisValidators 8 \
  --dataDir ./lodestar-node-2 \
  --port 9001 \
  --rest.port 9597 \
  --bootnodes "$ENR" \
  --genesisTime $GENESIS_TIME \
  --reset > node2.log 2>&1 &

echo "⏳ Ждем 15 секунд для подключения..."
sleep 15

echo ""
echo "=== 🔍 РЕЗУЛЬТАТ ==="
PEERS1=$(curl -s http://localhost:9596/eth/v1/node/peers | jq '.data | length' 2>/dev/null || echo "ошибка")
PEERS2=$(curl -s http://localhost:9597/eth/v1/node/peers | jq '.data | length' 2>/dev/null || echo "ошибка")

echo "Пиров у ноды 1: $PEERS1"
echo "Пиров у ноды 2: $PEERS2"

echo ""
echo "📊 Логи ноды 1:"
tail -n 3 node1.log | grep -E "peers:|Synced"

echo "📊 Логи ноды 2:"
tail -n 3 node2.log | grep -E "peers:|Searching"

if [ "$PEERS1" -eq 1 ] && [ "$PEERS2" -eq 1 ]; then
  echo ""
  echo "🎉 УСПЕХ! Ноды подключены!"
  echo "Теперь можно добавлять сниффер"
else
  echo ""
  echo "❌ Проблема с подключением"
  echo "Подробные логи ноды 2:"
  tail -n 10 node2.log
fi
