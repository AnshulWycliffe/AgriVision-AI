from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from . import db
from .models import Farm, Crop, DiseaseAnalysis, YieldPrediction, Conversation, ChatMessage
from .services.disease_service import DiseaseService
from .services.yield_service import YieldPredictionService
from .services.gemini_service import GeminiService
from .services.weather_service import WeatherService

api_bp = Blueprint('api', __name__)

@api_bp.route('/farms', methods=['GET', 'POST'])
@login_required
def handle_farms():
    if request.method == 'GET':
        farms = Farm.query.filter_by(user_id=current_user.id).all()
        return jsonify({
            'success': True,
            'farms': [{
                'id': f.id,
                'name': f.name,
                'location': f.location,
                'area': f.area
            } for f in farms]
        })
        
    elif request.method == 'POST':
        data = request.form

        def _float(key):
            v = data.get(key)
            return float(v) if v and v.strip() else None

        farm = Farm(
            name=data.get('name'),
            location=data.get('location'),
            area=_float('area'),
            nitrogen=_float('nitrogen'),
            phosphorus=_float('phosphorus'),
            potassium=_float('potassium'),
            user_id=current_user.id
        )
        db.session.add(farm)
        db.session.commit()
        return jsonify({'success': True, 'farm_id': farm.id})

@api_bp.route('/farms/<int:farm_id>', methods=['PUT'])
@login_required
def update_farm(farm_id):
    farm = Farm.query.filter_by(id=farm_id, user_id=current_user.id).first()
    if not farm:
        return jsonify({'success': False, 'error': 'Farm not found'}), 404

    data = request.form

    def _float(key):
        v = data.get(key)
        return float(v) if v and v.strip() else None

    farm.name       = data.get('name', farm.name)
    farm.location   = data.get('location', farm.location)
    farm.area       = _float('area') if data.get('area') else farm.area
    farm.nitrogen   = _float('nitrogen')
    farm.phosphorus = _float('phosphorus')
    farm.potassium  = _float('potassium')

    db.session.commit()
    return jsonify({'success': True})

@api_bp.route('/crops', methods=['GET', 'POST'])
@login_required
def handle_crops():
    if request.method == 'GET':
        crops = Crop.query.filter_by(user_id=current_user.id).all()
        return jsonify({
            'success': True,
            'crops': [{
                'id': c.id,
                'name': c.name,
                'variety': c.variety,
                'farm_id': c.farm_id
            } for c in crops]
        })
        
    elif request.method == 'POST':
        data = request.form
        crop = Crop(
            name=data.get('name'),
            variety=data.get('variety'),
            farm_id=int(data.get('farm_id')),
            user_id=current_user.id
        )
        db.session.add(crop)
        db.session.commit()
        return jsonify({'success': True, 'crop_id': crop.id})

@api_bp.route('/disease/analyze', methods=['POST'])
@login_required
def analyze_disease():
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No image part"}), 400

    image_file = request.files['image']
    crop_id = request.form.get('crop_id')
    farmer_observation = request.form.get('farmer_observation', '')

    result = DiseaseService.predict(image_file, farmer_observation)

    if not result.get("success"):
        return jsonify(result)

    # ── Gemini enrichment ────────────────────────────────────────────────────
    gemini_context = result.pop('gemini_context', None)
    gemini_explanation = None
    gemini_structured = {}

    if gemini_context:
        gemini_prompt = (
            gemini_context
            + "\n\nBased on the above disease model prediction, please provide a JSON response with exactly these keys:\n"
            "{\n"
            "  \"symptoms\": [\"...\", ...],\n"
            "  \"recommendations\": [\"...\", ...],\n"
            "  \"prevention\": [\"...\", ...],\n"
            "  \"explanation\": \"...\"\n"
            "}\n"
            "All text must be in Hindi (हिंदी). "
            "Do NOT modify the confidence value. Return ONLY the JSON, no extra text."
        )
        gemini_result = GeminiService.ask_assistant(gemini_prompt, history=[])
        if gemini_result.get('success'):
            raw = gemini_result.get('response', '')
            # Strip markdown code fences if present
            import re, json as _json
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                try:
                    gemini_structured = _json.loads(match.group(0))
                except Exception:
                    gemini_structured = {}
            gemini_explanation = gemini_structured.get('explanation', raw[:500])

    result['symptoms']        = gemini_structured.get('symptoms', [])
    result['recommendations'] = gemini_structured.get('recommendations', [])
    result['prevention']      = gemini_structured.get('prevention', [])
    result['gemini_explanation'] = gemini_explanation

    # ── Persist to DB ────────────────────────────────────────────────────────
    import json as _json_store
    analysis = DiseaseAnalysis(
        user_id=current_user.id,
        crop_id=int(crop_id) if crop_id else None,
        detected_crop=result.get("crop"),
        detected_disease=result.get("disease"),
        confidence=result.get("confidence"),
        severity=result.get("severity"),
        farmer_observation=farmer_observation,
        gemini_data=_json_store.dumps(gemini_structured) if gemini_structured else None,
    )
    db.session.add(analysis)
    db.session.commit()
    result["analysis_id"] = analysis.id

    return jsonify(result)

@api_bp.route('/yield/predict', methods=['POST'])
@login_required
def predict_yield():
    data = request.form
    crop_id = data.get('crop_id')
    
    if not crop_id:
        return jsonify({"success": False, "error": "Crop ID is required"}), 400
        
    crop = Crop.query.get(crop_id)
    if not crop or crop.user_id != current_user.id:
        return jsonify({"success": False, "error": "Invalid crop"}), 400
        
    farm = Farm.query.get(crop.farm_id)
    if not farm or not farm.area:
        return jsonify({"success": False, "error": "Farm area is required for prediction"}), 400
        
    disease_severity = data.get('disease_severity')
    disease_analysis_id = data.get('disease_analysis_id')
    
    result = YieldPredictionService.predict(farm.area, crop.name, disease_severity)
    
    if result.get("success"):
        # Save prediction history
        prediction = YieldPrediction(
            user_id=current_user.id,
            crop_id=crop.id,
            disease_analysis_id=int(disease_analysis_id) if disease_analysis_id else None,
            predicted_yield_per_acre=result.get("yield_per_acre"),
            total_yield=result.get("total_yield"),
            unit=result.get("unit")
        )
        db.session.add(prediction)
        db.session.commit()
        result["prediction_id"] = prediction.id
        
    return jsonify(result)

@api_bp.route('/assistant/chat', methods=['POST'])
@login_required
def assistant_chat():
    data = request.json
    message = data.get('message')
    conversation_id = data.get('conversation_id')
    
    if not message:
        return jsonify({"success": False, "error": "Message is required"}), 400
        
    # Get or create conversation
    if conversation_id:
        conversation = Conversation.query.get(conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            return jsonify({"success": False, "error": "Invalid conversation"}), 400
    else:
        conversation = Conversation(user_id=current_user.id)
        db.session.add(conversation)
        db.session.commit()
        
    # Save user message
    user_msg = ChatMessage(role='user', content=message, conversation_id=conversation.id)
    db.session.add(user_msg)
    db.session.commit()
    
    # Get recent history
    history = ChatMessage.query.filter_by(conversation_id=conversation.id).order_by(ChatMessage.timestamp.asc()).all()
    
    # Exclude the very last message from history passed to gemini (as it's the current message)
    past_history = history[:-1] if len(history) > 1 else []
    
    # Call Gemini service
    result = GeminiService.ask_assistant(message, history=past_history)
    
    if result.get("success"):
        # Save AI response
        ai_msg = ChatMessage(role='ai', content=result.get("response"), conversation_id=conversation.id)
        db.session.add(ai_msg)
        db.session.commit()
        result['conversation_id'] = conversation.id
        
    return jsonify(result)

@api_bp.route('/weather', methods=['GET'])
@login_required
def get_weather():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    q = request.args.get('q')

    # If no q or lat/lon provided, try user's first farm location
    if not q and not (lat and lon):
        first_farm = Farm.query.filter_by(user_id=current_user.id).filter(Farm.location != None).first()
        if first_farm and first_farm.location:
            q = first_farm.location

    weather_data = WeatherService.get_weather(location=q, lat=lat, lon=lon)
    return jsonify(weather_data)



