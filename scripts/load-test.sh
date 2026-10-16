#!/bin/sh
URL=${1:-http://127.0.0.1:8080}; HOST=${2:-pantry.local}
end=$(( $(date +%s) + ${3:-120} ))
while [ "$(date +%s)" -lt "$end" ]; do
  curl -s -o /dev/null -H "Host: $HOST" "$URL/api/items"
  curl -s -o /dev/null -H "Host: $HOST" "$URL/api/items/stats"
  curl -s -o /dev/null -H "Host: $HOST" "$URL/api/items/999"
done
