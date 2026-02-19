from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import csv
import os
from datetime import datetime, timedelta
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

DATA_FILE = 'mood_data.csv'

class MoodTracker:
    def __init__(self):
        self.initialize_file()
    
    def initialize_file(self):
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['date', 'mood', 'productivity', 'note'])
    
    def validate_date(self, date_str):
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def validate_productivity(self, productivity):
        try:
            score = int(productivity)
            return 1 <= score <= 10
        except ValueError:
            return False
    
    def validate_mood(self, mood):
        valid_moods = ['happy', 'sad', 'angry', 'anxious', 'calm', 'excited', 'tired', 'neutral']
        return mood.lower() in valid_moods
    
    def load_all_logs(self):
        logs = []
        try:
            with open(DATA_FILE, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    row['productivity'] = int(row['productivity'])
                    logs.append(row)
            return logs
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"Error loading logs: {e}")
            return []
    
    def save_log(self, log_data):
        try:
            with open(DATA_FILE, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    log_data['date'],
                    log_data['mood'],
                    log_data['productivity'],
                    log_data['note']
                ])
            return True
        except Exception as e:
            print(f"Error saving log: {e}")
            return False
    
    def save_all_logs(self, logs):
        try:
            with open(DATA_FILE, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['date', 'mood', 'productivity', 'note'])
                for log in logs:
                    writer.writerow([
                        log['date'],
                        log['mood'],
                        log['productivity'],
                        log['note']
                    ])
            return True
        except Exception as e:
            print(f"Error saving logs: {e}")
            return False
    
    def get_summary(self):
        logs = self.load_all_logs()
        
        if not logs:
            return {"error": "No data available"}
        
        productivity_scores = [log['productivity'] for log in logs]
        moods = [log['mood'] for log in logs]
        
        avg_productivity = sum(productivity_scores) / len(productivity_scores)
        most_common_mood = max(set(moods), key=moods.count)
        
        # Mood distribution
        mood_count = {}
        for mood in moods:
            mood_count[mood] = mood_count.get(mood, 0) + 1
        
        mood_distribution = {mood: count for mood, count in mood_count.items()}
        
        # Weekly analysis
        day_productivity = {}
        for log in logs:
            date_obj = datetime.strptime(log['date'], '%Y-%m-%d')
            day_name = date_obj.strftime('%A')
            
            if day_name not in day_productivity:
                day_productivity[day_name] = []
            day_productivity[day_name].append(log['productivity'])
        
        avg_by_day = {day: sum(scores)/len(scores) for day, scores in day_productivity.items()}
        most_productive_day = max(avg_by_day.items(), key=lambda x: x[1]) if avg_by_day else ("No data", 0)
        
        return {
            "total_entries": len(logs),
            "average_productivity": round(avg_productivity, 2),
            "most_common_mood": most_common_mood,
            "mood_distribution": mood_distribution,
            "most_productive_day": most_productive_day[0],
            "most_productive_day_score": round(most_productive_day[1], 2)
        }
    
    def get_insights(self):
        logs = self.load_all_logs()
        
        if not logs:
            return {"error": "No data available"}
        
        # Recent logs (last 7 days)
        recent_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        recent_logs = [log for log in logs if log['date'] >= recent_date]
        
        if not recent_logs:
            return {"error": "No recent data available"}
        
        recent_productivity = [log['productivity'] for log in recent_logs]
        recent_moods = [log['mood'] for log in recent_logs]
        
        avg_recent_productivity = sum(recent_productivity) / len(recent_productivity)
        
        # Generate suggestions
        suggestions = []
        if avg_recent_productivity >= 8:
            suggestions.append("🎉 Excellent! You're doing great! Keep up the fantastic work!")
        elif avg_recent_productivity >= 6:
            suggestions.append("👍 Good job! You're maintaining solid productivity.")
        elif avg_recent_productivity >= 4:
            suggestions.append("💡 Not bad! Try breaking tasks into smaller chunks to improve focus.")
        else:
            suggestions.extend([
                "🔍 Let's improve! Consider these tips:",
                "Start with the most important task first",
                "Take regular breaks using Pomodoro technique",
                "Minimize distractions during work hours"
            ])
        
        # Mood-based suggestions
        negative_moods = ['sad', 'angry', 'anxious', 'tired']
        negative_count = sum(1 for mood in recent_moods if mood in negative_moods)
        
        if negative_count > len(recent_moods) * 0.5:
            suggestions.extend([
                "😔 You've had some tough days. Remember to:",
                "Take time for self-care activities",
                "Talk to friends or family",
                "Practice mindfulness or meditation"
            ])
        
        return {
            "average_recent_productivity": round(avg_recent_productivity, 2),
            "suggestions": suggestions
        }

tracker = MoodTracker()

# API Routes
@app.route('/api/logs', methods=['GET'])
def get_logs():
    logs = tracker.load_all_logs()
    return jsonify(logs)

@app.route('/api/logs', methods=['POST'])
def add_log():
    data = request.json
    
    # Validation
    if not tracker.validate_date(data.get('date', '')):
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    if not tracker.validate_mood(data.get('mood', '')):
        return jsonify({"error": "Invalid mood"}), 400
    
    if not tracker.validate_productivity(data.get('productivity', '')):
        return jsonify({"error": "Invalid productivity score. Must be 1-10"}), 400
    
    log_data = {
        'date': data['date'],
        'mood': data['mood'],
        'productivity': int(data['productivity']),
        'note': data.get('note', '')
    }
    
    if tracker.save_log(log_data):
        return jsonify({"message": "Log added successfully"})
    else:
        return jsonify({"error": "Failed to save log"}), 500

@app.route('/api/logs/<int:log_index>', methods=['PUT'])
def edit_log(log_index):
    logs = tracker.load_all_logs()
    
    if log_index < 0 or log_index >= len(logs):
        return jsonify({"error": "Invalid log index"}), 400
    
    data = request.json
    
    # Validation
    if not tracker.validate_date(data.get('date', '')):
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    if not tracker.validate_mood(data.get('mood', '')):
        return jsonify({"error": "Invalid mood"}), 400
    
    if not tracker.validate_productivity(data.get('productivity', '')):
        return jsonify({"error": "Invalid productivity score. Must be 1-10"}), 400
    
    logs[log_index] = {
        'date': data['date'],
        'mood': data['mood'],
        'productivity': int(data['productivity']),
        'note': data.get('note', '')
    }
    
    if tracker.save_all_logs(logs):
        return jsonify({"message": "Log updated successfully"})
    else:
        return jsonify({"error": "Failed to update log"}), 500

@app.route('/api/logs/<int:log_index>', methods=['DELETE'])
def delete_log(log_index):
    logs = tracker.load_all_logs()
    
    if log_index < 0 or log_index >= len(logs):
        return jsonify({"error": "Invalid log index"}), 400
    
    deleted_log = logs.pop(log_index)
    
    if tracker.save_all_logs(logs):
        return jsonify({"message": f"Log for {deleted_log['date']} deleted successfully"})
    else:
        return jsonify({"error": "Failed to delete log"}), 500

@app.route('/api/summary', methods=['GET'])
def get_summary():
    summary = tracker.get_summary()
    return jsonify(summary)

@app.route('/api/insights', methods=['GET'])
def get_insights():
    insights = tracker.get_insights()
    return jsonify(insights)

@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)