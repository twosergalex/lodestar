#!/bin/bash

# Останавливаем старые ноды
echo "🛑 Останавливаем старые процессы Lodestar..."
pkill -f "lodestar dev" 2>/dev/null
sleep 3

# Очищаем старые данные
echo "🧹 Очищаем старые данные..."
rm -rf ./lodestar-node-1
rm -rf ./lodestar-node-2

echo "🚀 Запускаем ноду 1..."
./lodestar dev \
  --genesisValidators 8 \
  --startValidators 0..7 \
  --enr.ip 127.0.0.1 \
  --enr.udp 9000 \
  --dataDir ./lodestar-node-1 \
  --reset > node1.log 2>&1 &

echo "⏳ Ждем 15 секунд для инициализации ноды 1..."
sleep 15

echo "📡 Получаем ENR ноды 1..."
ENR=$(curl -s http://localhost:9596/eth/v1/node/identity | jq -r '.data.enr')

if [ -z "$ENR" ]; then
  echo "❌ Ошибка: не удалось получить ENR. Проверьте логи ноды 1"
  tail -n 10 node1.log
  exit 1
fi

echo "✅ ENR получен: ${ENR:0:50}..."

echo "🎯 Запускаем ноду 2..."
./lodestar dev \
  --genesisValidators 8 \
  --dataDir ./lodestar-node-2 \
  --port 9001 \
  --rest.port 9597 \
  --bootnodes "$ENR" \
  --reset > node2.log 2>&1 &

echo "⏳ Ждем 10 секунд для подключения нод..."
sleep 10

echo ""
echo "=== ✅ СЕТЬ ЗАПУЩЕНА ==="
echo "📊 Логи ноды 1: tail -f node1.log"
echo "📊 Логи ноды 2: tail -f node2.log"
echo ""
echo "🔍 ПРОВЕРКА ПОДКЛЮЧЕНИЯ:"
echo "Пиров у ноды 1: $(curl -s http://localhost:9596/eth/v1/node/peers | jq '.data | length' 2>/dev/null || echo "ошибка")"
echo "Пиров у ноды 2: $(curl -s http://localhost:9597/eth/v1/node/peers | jq '.data | length' 2>/dev/null || echo "ошибка")"
echo ""
echo "💡 Для мониторинга логов используйте:"
echo "   tail -f node1.log | grep peers"
echo "   tail -f node2.log | grep peers"
