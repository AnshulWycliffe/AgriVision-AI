import os
import re

translations = {
    'AgriVision AI': 'एग्रीविज़न एआई',
    'Home': 'होम',
    'Farms': 'खेत',
    'Crops': 'फसलें',
    'Scan': 'स्कैन',
    'Yield': 'उपज',
    'AI': 'एआई',
    'Dashboard': 'डैशबोर्ड',
    'Login': 'लॉगिन',
    'Register': 'रजिस्टर करें',
    'Email Address': 'ईमेल पता',
    'Password': 'पासवर्ड',
    'Sign In': 'साइन इन करें',
    "Don't have an account?": 'क्या आपके पास खाता नहीं है?',
    'Sign Up': 'साइन अप करें',
    'Full Name': 'पूरा नाम',
    'Create Account': 'खाता बनाएं',
    'Already have an account?': 'पहले से ही एक खाता है?',
    'Welcome back,': 'वापसी पर स्वागत है,',
    'Logout': 'लॉगआउट',
    'Weather Details': 'मौसम विवरण',
    'Add Farm': 'खेत जोड़ें',
    'Add New Farm': 'नया खेत जोड़ें',
    'Farm Name': 'खेत का नाम',
    'Area (Acres)': 'क्षेत्रफल (एकड़)',
    'Location': 'स्थान',
    'Save Farm': 'खेत सहेजें',
    'Add Crop': 'फसल जोड़ें',
    'Crop Name': 'फसल का नाम',
    'Planting Date': 'रोपण की तिथि',
    'Save Crop': 'फसल सहेजें',
    'Crop Scanner': 'फसल स्कैनर',
    'Upload or take a photo of your crop to detect diseases': 'बीमारियों का पता लगाने के लिए अपनी फसल की फोटो अपलोड करें या खींचें',
    'Describe Symptoms (Optional)': 'लक्षणों का वर्णन करें (वैकल्पिक)',
    'Analyze Crop': 'फसल का विश्लेषण करें',
    'AI Assistant': 'एआई सहायक',
    'Ask AI...': 'एआई से पूछें...',
    "Hello! I'm your AgriVision AI Assistant. How can I help you with your farm today?": 'नमस्ते! मैं आपका एग्रीविज़न एआई सहायक हूं। आज मैं आपके खेत में कैसे मदद कर सकता हूं?',
    'Listening...': 'सुन रहा है...',
    'Disease Analysis Result': 'रोग विश्लेषण परिणाम',
    'Crop:': 'फसल:',
    'Confidence:': 'आत्मविश्वास:',
    'Severity:': 'गंभीरता:',
    'Symptoms': 'लक्षण',
    'Recommendations': 'सिफारिशें',
    'Prevention': 'निवारण',
    'Yield Prediction': 'उपज भविष्यवाणी',
    'Predict Yield': 'उपज की भविष्यवाणी करें',
    'Expected Yield': 'अपेक्षित उपज',
    'History': 'इतिहास',
    'Disease Scan History': 'रोग स्कैन इतिहास',
    'Yield Prediction History': 'उपज भविष्यवाणी इतिहास'
}

def translate_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for en, hi in translations.items():
        content = content.replace(hi, en)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

template_dir = 'app/templates'
for root, dirs, files in os.walk(template_dir):
    for file in files:
        if file.endswith('.html'):
            translate_file(os.path.join(root, file))

print('Translation complete.')
