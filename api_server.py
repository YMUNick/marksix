#!/usr/bin/env python3
"""
香港六合彩 API 後端 (Mark Six API Server)
==========================================
Flask API serving historical data, statistics, and AI predictions.

Endpoints:
  GET /api/results     → 全部歷史資料
  GET /api/recent      → 最近10期
  GET /api/frequency   → 數字出現頻率
  GET /api/stats       → 奇偶 / 大小統計
  GET /api/hot         → 最近20期出現次數
  GET /api/predict     → AI預測結果
  GET /api/heatmap     → 熱力圖數據
  GET /api/gaps        → 間隔分析

Usage:
  pip install flask flask-cors
  python3 api_server.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# ============================================================
# Load data
# ============================================================
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'marksix_data.json')

def load_data():
    """Load the pre-computed data from JSON."""
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

# Cache data in memory
_data = None
def get_data():
    global _data
    if _data is None:
        _data = load_data()
    return _data

# ============================================================
# API Endpoints
# ============================================================

@app.route('/')
def index():
    """API documentation."""
    return jsonify({
        "name": "Hong Kong Mark Six Analytics API",
        "version": "1.0.0",
        "endpoints": {
            "/api/results": "全部歷史資料 (可用 ?limit=N&offset=M 分頁)",
            "/api/recent": "最近10期開獎記錄",
            "/api/frequency": "號碼出現頻率 (1-49)",
            "/api/stats": "奇偶 / 大小分布統計",
            "/api/hot": "最近20期出現次數",
            "/api/predict": "AI預測結果 (3種模型)",
            "/api/heatmap": "熱力圖數據",
            "/api/gaps": "號碼間隔分析",
            "/api/meta": "資料庫元數據",
        }
    })

@app.route('/api/results')
def get_results():
    """Return all historical draws with pagination support."""
    data = get_data()
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', default=0, type=int)
    
    draws = data['draws']
    
    if limit:
        draws = draws[offset:offset + limit]
    
    return jsonify({
        "total": len(data['draws']),
        "offset": offset,
        "limit": limit,
        "results": draws
    })

@app.route('/api/recent')
def get_recent():
    """Return most recent 10 draws."""
    data = get_data()
    n = request.args.get('n', default=10, type=int)
    n = min(n, 50)  # Cap at 50
    return jsonify({
        "count": n,
        "results": data['draws'][-n:]
    })

@app.route('/api/frequency')
def get_frequency():
    """Return frequency statistics for numbers 1-49."""
    data = get_data()
    return jsonify({
        "total_draws": data['meta']['total_draws'],
        "main_numbers": data['stats']['frequency'],
        "special_numbers": data['stats']['special_frequency'],
    })

@app.route('/api/stats')
def get_stats():
    """Return odd/even and high/low distribution."""
    data = get_data()
    return jsonify({
        "total_draws": data['meta']['total_draws'],
        "odd_even": data['stats']['odd_even'],
        "high_low": data['stats']['high_low'],
        "consecutive_pairs": data['stats']['consecutive_pairs'],
    })

@app.route('/api/hot')
def get_hot():
    """Return hot/cold numbers from recent 20 draws."""
    data = get_data()
    return jsonify({
        "period": "recent_20",
        "numbers": data['stats']['hot_cold_20']
    })

@app.route('/api/predict')
def get_predict():
    """Return AI prediction results from all models."""
    data = get_data()
    model_id = request.args.get('model')
    
    if model_id:
        # Filter to specific model
        model = next(
            (m for m in data['predictions']['models'] if m['model_id'] == model_id),
            None
        )
        if model is None:
            return jsonify({"error": f"Model '{model_id}' not found"}), 404
        return jsonify({
            "model": model,
            "disclaimer": data['predictions']['disclaimer']
        })
    
    return jsonify(data['predictions'])

@app.route('/api/heatmap')
def get_heatmap():
    """Return heatmap data for numbers 1-49."""
    data = get_data()
    return jsonify({
        "total_draws": data['meta']['total_draws'],
        "heatmap": data['stats']['heatmap']
    })

@app.route('/api/gaps')
def get_gaps():
    """Return gap analysis (draws since last appearance)."""
    data = get_data()
    return jsonify({
        "total_draws": data['meta']['total_draws'],
        "gaps": data['stats']['gaps']
    })

@app.route('/api/meta')
def get_meta():
    """Return metadata about the database."""
    data = get_data()
    return jsonify(data['meta'])

# ============================================================
# CSV Export
# ============================================================
@app.route('/api/export/csv')
def export_csv():
    """Export all draws as CSV."""
    data = get_data()
    import io
    output = io.StringIO()
    output.write("draw_id,draw_date,day_of_week,num1,num2,num3,num4,num5,num6,special_number\n")
    for d in data['draws']:
        nums = d['numbers']
        output.write(f"{d['draw_id']},{d['draw_date']},{d['day_of_week']},{nums[0]},{nums[1]},{nums[2]},{nums[3]},{nums[4]},{nums[5]},{d['special_number']}\n")
    
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=marksix_results.csv"}
    )

# ============================================================
# Main
# ============================================================
if __name__ == '__main__':
    print("🎲 Mark Six Analytics API Server")
    print("=" * 40)
    print("📡 http://localhost:5000")
    print("📡 http://localhost:5000/api/predict")
    print("=" * 40)
    app.run(host='0.0.0.0', port=5000, debug=True)
