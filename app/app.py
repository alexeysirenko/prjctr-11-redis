import time
import random
import math
from flask import Flask, request, jsonify
import redis
from redis.sentinel import Sentinel

app = Flask(__name__)

SENTINEL_HOSTS = [("sentinel-1", 26379), ("sentinel-2", 26379), ("sentinel-3", 26379)]
MASTER_NAME = "mymaster"

sentinel = Sentinel(SENTINEL_HOSTS, socket_timeout=0.1)
redis_client = sentinel.master_for(MASTER_NAME, socket_timeout=0.1, decode_responses=True)

BETA = 1  

def cache_read(key):
    data = redis_client.hgetall(key)
    if not data:
        return None, None, None
    return data.get("value"), float(data.get("delta", 0)), float(data.get("expiry", 0))

def cache_write(key, value, delta, ttl):
    expiry = time.time() + ttl
    redis_client.hmset(key, {"value": value, "delta": delta, "expiry": expiry})
    redis_client.expire(key, ttl)

def recompute_value():
    time.sleep(random.uniform(0.1, 0.3))  
    return f"computed_value_{random.randint(1, 1000)}"

@app.route("/cache/<key>", methods=["GET"])
def get_cache(key):
    ttl = 30  
    value, delta, expiry = cache_read(key)

    if not value or (time.time() - delta * BETA * math.log(random.uniform(0, 1))) >= expiry:
        start = time.time()
        value = recompute_value()
        delta = time.time() - start
        cache_write(key, value, delta, ttl)

    return jsonify({"key": key, "value": value})

@app.route("/cache", methods=["POST"])
def set_cache():
    data = request.json
    key = data.get("key")
    value = data.get("value")
    ttl = int(data.get("ttl", 30))

    if not key or not value:
        return jsonify({"error": "Missing key or value"}), 400

    cache_write(key, value, 0, ttl)
    return jsonify({"message": f"Stored {key} in Redis with TTL {ttl}s"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
