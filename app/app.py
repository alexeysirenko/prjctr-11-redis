from flask import Flask, request, jsonify
import redis
import time

app = Flask(__name__)

# Redis Sentinel connection details
SENTINEL_HOSTS = [("sentinel-1", 26379), ("sentinel-2", 26379), ("sentinel-3", 26379)]
MASTER_NAME = "mymaster"
REDIS_PASSWORD = "supersecret"  # Set this to match your Redis setup

# Connect to Redis Sentinel
sentinel = redis.sentinel.Sentinel(SENTINEL_HOSTS, socket_timeout=0.1)

def get_redis_client():
    """Get a connection to the Redis master node (handles failover)"""
    return sentinel.master_for(MASTER_NAME, socket_timeout=0.1, decode_responses=True)

@app.route("/cache", methods=["POST"])
def set_cache():
    """Store a key-value pair in Redis with expiration"""
    data = request.json
    key = data.get("key")
    value = data.get("value")
    ttl = int(data.get("ttl", 10))  # Default TTL = 10 seconds

    if not key or not value:
        return jsonify({"error": "Missing key or value"}), 400

    redis_client = get_redis_client()
    redis_client.setex(key, ttl, value)
    return jsonify({"message": f"Stored {key} in Redis with TTL {ttl}s"})


@app.route("/cache/<key>", methods=["GET"])
def get_cache(key):
    """Retrieve a cached value from Redis"""
    redis_client = get_redis_client()
    value = redis_client.get(key)
    if value is None:
        return jsonify({"message": f"Cache miss for {key}"}), 404
    return jsonify({"key": key, "value": value})


@app.route("/test-eviction", methods=["GET"])
def test_eviction():
    """Fill Redis with test data to trigger eviction"""
    redis_client = get_redis_client()
    for i in range(1, 1000):  # Insert multiple keys to force eviction
        redis_client.set(f"key{i}", f"value{i}", ex=30)  # Set expiration
        time.sleep(0.01)  # Simulate slow inserts

    evicted_keys = redis_client.info("memory")["evicted_keys"]
    return jsonify({"evicted_keys": evicted_keys})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
