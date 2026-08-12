from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from .models import Farm, Crop, DiseaseAnalysis, YieldPrediction, Conversation, ChatMessage
from .services.weather_service import WeatherService
from .services.news_service import NewsService
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    farms_count = Farm.query.filter_by(user_id=current_user.id).count()
    crops_count = Crop.query.filter_by(user_id=current_user.id).count()
    recent_analysis = DiseaseAnalysis.query.filter_by(user_id=current_user.id).order_by(DiseaseAnalysis.date.desc()).first()
    recent_yield = YieldPrediction.query.filter_by(user_id=current_user.id).order_by(YieldPrediction.date.desc()).first()
    
    farm = (
        Farm.query
        .filter_by(user_id=current_user.id)
        .first()
    )

    weather = None

    if farm and farm.location:
        weather = WeatherService.get_weather(
            farm.location
        )

    # Fetch latest Indian agricultural news
    news_items = NewsService.get_agri_news(limit=5)

    return render_template('dashboard.html', 
                           farms_count=farms_count, 
                           crops_count=crops_count,
                           recent_analysis=recent_analysis,
                           recent_yield=recent_yield,
                           farm=farm,
                           weather=weather,
                           news_items=news_items)

@main_bp.route('/farms')
@login_required
def farms():
    user_farms = Farm.query.filter_by(user_id=current_user.id).all()
    return render_template('farms.html', farms=user_farms)

@main_bp.route('/crops')
@login_required
def crops():
    user_crops = Crop.query.filter_by(user_id=current_user.id).all()
    user_farms = Farm.query.filter_by(user_id=current_user.id).all()
    return render_template('crops.html', crops=user_crops, farms=user_farms)

@main_bp.route('/scan')
@login_required
def scan():
    user_crops = Crop.query.filter_by(user_id=current_user.id).all()
    return render_template('scan.html', crops=user_crops)

@main_bp.route('/disease-result/<int:analysis_id>')
@login_required
def disease_result(analysis_id):
    analysis = DiseaseAnalysis.query.get_or_404(analysis_id)
    if analysis.user_id != current_user.id:
        return redirect(url_for('main.dashboard'))

    gd = analysis.gemini_parsed   # {} if not stored

    result = {
        "crop":              analysis.crop_display,
        "disease":           analysis.detected_disease or "Unknown",
        "confidence":        analysis.confidence or 0.0,
        "severity":          analysis.severity,
        "symptoms":          gd.get("symptoms", []),
        "recommendations":   gd.get("recommendations", []),
        "prevention":        gd.get("prevention", []),
        "gemini_explanation": gd.get("explanation", ""),
        "top_predictions":   [],
        "status":            "success",
    }

    return render_template('disease_result.html', analysis=analysis, result=result)


@main_bp.route('/yield')
@login_required
def yield_prediction():
    user_crops = Crop.query.filter_by(user_id=current_user.id).all()
    user_farms = Farm.query.filter_by(user_id=current_user.id).all()
    recent_analyses = DiseaseAnalysis.query.filter_by(user_id=current_user.id).order_by(DiseaseAnalysis.date.desc()).limit(5).all()
    return render_template('yield.html', crops=user_crops, farms=user_farms, recent_analyses=recent_analyses)

@main_bp.route('/history')
@login_required
def history():
    disease_history = DiseaseAnalysis.query.filter_by(user_id=current_user.id).order_by(DiseaseAnalysis.date.desc()).all()
    yield_history = YieldPrediction.query.filter_by(user_id=current_user.id).order_by(YieldPrediction.date.desc()).all()
    
    return render_template('history.html', 
                           disease_history=disease_history, 
                           yield_history=yield_history)

@main_bp.route('/assistant')
@login_required
def assistant():
    # Get the latest conversation if exists
    conversation = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.start_time.desc()).first()
    chat_history = []
    
    if conversation:
        chat_history = ChatMessage.query.filter_by(conversation_id=conversation.id).order_by(ChatMessage.timestamp.asc()).all()
        
    return render_template('assistant.html', chat_history=chat_history, conversation_id=conversation.id if conversation else '')


