#!/bin/bash
# demo_stream.sh - Script de demo para el video del dashboard
# Uso: ./demo_stream.sh <API_URL>
# Ejemplo: ./demo_stream.sh https://valorant-vote-api-xxxxx-ue.a.run.app

API_URL="${1:-http://localhost:8080}"
echo "=== Demo Streaming - Valorant Charity Vote ==="
echo "API: $API_URL"
echo ""

# 1. Generar votos aleatorios
echo ">>> Generando votos..."
for i in $(seq 1 15); do
  PLAYER="streamer-$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 6 | head -1)"
  SKIN=$(( (RANDOM % 2) + 1 ))
  CHARITY=$(( (RANDOM % 5) + 1 ))

  RESULT=$(curl -s -X POST "$API_URL/api/vote" \
    -H "Content-Type: application/json" \
    -d "{\"player_id\": \"$PLAYER\", \"skin_id\": $SKIN, \"charity_id\": $CHARITY}")

  echo "  Voto $i: skin=$SKIN charity=$CHARITY → $(echo $RESULT | grep -o '"message":"[^"]*"' | cut -d'"' -f4)"
  sleep 0.3
done

echo ""

# 2. Mostrar resultados
echo ">>> Resultados de votación:"
curl -s "$API_URL/api/vote/results" | python3 -m json.tool
echo ""

# 3. Activar compras automáticas
echo ">>> Activando compras automáticas..."
curl -s -X POST "$API_URL/api/auto-purchase/start"
echo ""

# 4. Esperar y generar más votos
echo ">>> Esperando 10 segundos mientras se generan compras..."
sleep 10

echo ""
echo ">>> Generando más votos..."
for i in $(seq 1 10); do
  PLAYER="viewer-$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 6 | head -1)"
  SKIN=$(( (RANDOM % 2) + 1 ))
  CHARITY=$(( (RANDOM % 5) + 1 ))

  curl -s -X POST "$API_URL/api/vote" \
    -H "Content-Type: application/json" \
    -d "{\"player_id\": \"$PLAYER\", \"skin_id\": $SKIN, \"charity_id\": $CHARITY}" > /dev/null
  echo "  Voto $i enviado"
  sleep 0.2
done

echo ""

# 5. Dashboard final
echo ">>> Dashboard final:"
curl -s "$API_URL/api/dashboard" | python3 -m json.tool
echo ""
echo "=== Demo completada ==="
