#!/usr/bin/env python3
"""
Advanced Ethical Hacking Telegram Bot with Gemini AI Integration
Developer: Ziaul Islam
Version: 1.0.0
"""

import logging
import json
import asyncio
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

# ============ Configuration ============

@dataclass
class Config:
    """Bot configuration settings"""
    TELEGRAM_TOKEN: str = "8650093915:AAGLx6R_T2e_H7huN5EFz7wuW8J09tqlWVo"
    GEMINI_API_KEY: str = "AIzaSyC8AsK7fpjvXlDjXqYsfT88WGmn5ySSOls"
    GEMINI_URL: str = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    MAX_HISTORY: int = 10
    SESSION_TIMEOUT: int = 3600  # 1 hour

config = Config()

# ============ Logging Setup ============

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ Data Models ============

class AnalysisType(Enum):
    """Types of ethical hacking analysis"""
    VULNERABILITY = "vulnerability_assessment"
    PENETRATION_TEST = "penetration_test"
    SOCIAL_ENGINEERING = "social_engineering"
    NETWORK_SECURITY = "network_security"
    WEB_SECURITY = "web_security"
    MOBILE_SECURITY = "mobile_security"
    CLOUD_SECURITY = "cloud_security"
    OSINT = "osint"
    FORENSICS = "digital_forensics"
    MALWARE_ANALYSIS = "malware_analysis"

class ChatSession:
    """Manage individual chat sessions"""
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.history: List[Dict] = []
        self.session_type: Optional[AnalysisType] = None
        self.last_activity = datetime.now()
        self.context = {}
        
    def add_message(self, role: str, content: str):
        """Add message to history"""
        self.history.append({"role": role, "content": content})
        if len(self.history) > config.MAX_HISTORY * 2:
            self.history = self.history[-config.MAX_HISTORY * 2:]
        self.last_activity = datetime.now()
    
    def get_context(self) -> str:
        """Get formatted context for Gemini"""
        return "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in self.history[-config.MAX_HISTORY:]
        ])

# ============ Session Manager ============

class SessionManager:
    """Manage all active chat sessions"""
    def __init__(self):
        self.sessions: Dict[int, ChatSession] = {}
        
    def get_session(self, user_id: int) -> ChatSession:
        """Get or create session for user"""
        if user_id not in self.sessions:
            self.sessions[user_id] = ChatSession(user_id)
        return self.sessions[user_id]
    
    def cleanup(self):
        """Remove expired sessions"""
        current_time = datetime.now()
        expired = [
            uid for uid, session in self.sessions.items()
            if (current_time - session.last_activity).seconds > config.SESSION_TIMEOUT
        ]
        for uid in expired:
            del self.sessions[uid]

session_manager = SessionManager()

# ============ Gemini AI Integration ============

class GeminiAI:
    """Advanced Gemini AI integration for ethical hacking"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.system_prompts = {
            AnalysisType.VULNERABILITY: """
                You are an expert ethical hacker specializing in vulnerability assessment.
                Analyze the target system and provide:
                1. Potential security vulnerabilities
                2. Risk severity levels (Critical/High/Medium/Low)
                3. Recommended security measures
                4. Exploitation vectors
                5. Mitigation strategies
            """,
            AnalysisType.PENETRATION_TEST: """
                Act as a senior penetration tester. Provide:
                1. Testing methodology
                2. Potential attack vectors
                3. Exploitation techniques
                4. Post-exploitation analysis
                5. Remediation steps
                6. Security hardening guidelines
            """,
            AnalysisType.SOCIAL_ENGINEERING: """
                As a social engineering expert, analyze:
                1. Potential attack vectors (phishing, vishing, etc.)
                2. Human psychology aspects
                3. Defense mechanisms
                4. Awareness training recommendations
                5. Security policy improvements
            """,
            AnalysisType.NETWORK_SECURITY: """
                Network security expert analysis:
                1. Network architecture vulnerabilities
                2. Protocol weaknesses
                3. Firewall and IDS/IPS bypass techniques
                4. Secure network design principles
                5. Advanced threat detection strategies
            """,
            AnalysisType.WEB_SECURITY: """
                Web application security expert:
                1. OWASP Top 10 vulnerabilities
                2. Attack vectors (XSS, SQLi, CSRF, etc.)
                3. Secure coding practices
                4. WAF configuration recommendations
                5. Input validation and sanitization
            """,
            AnalysisType.MOBILE_SECURITY: """
                Mobile security specialist:
                1. App security assessment
                2. Platform-specific vulnerabilities (iOS/Android)
                3. Binary protection mechanisms
                4. Data storage security
                5. Network communication security
            """,
            AnalysisType.CLOUD_SECURITY: """
                Cloud security architect:
                1. Cloud infrastructure vulnerabilities
                2. IAM misconfigurations
                3. Storage security issues
                4. Serverless application security
                5. Compliance requirements (GDPR, HIPAA, etc.)
            """,
            AnalysisType.OSINT: """
                OSINT expert providing:
                1. Information gathering techniques
                2. Social media intelligence
                3. Domain and IP intelligence
                4. Dark web monitoring
                5. Threat intelligence integration
                6. Privacy protection strategies
            """,
            AnalysisType.FORENSICS: """
                Digital forensics specialist:
                1. Evidence collection methods
                2. Chain of custody procedures
                3. Malware analysis techniques
                4. Timeline reconstruction
                5. Anti-forensics detection
                6. Reporting and documentation
            """,
            AnalysisType.MALWARE_ANALYSIS: """
                Malware analysis expert:
                1. Static analysis techniques
                2. Dynamic analysis methods
                3. Behavioral analysis
                4. Network traffic analysis
                5. Reverse engineering strategies
                6. Indicator of Compromise (IOC) extraction
            """
        }
    
    def create_prompt(self, session_type: AnalysisType, user_input: str, context: str) -> str:
        """Create structured prompt for Gemini"""
        system_prompt = self.system_prompts.get(
            session_type,
            "You are an advanced ethical hacking AI assistant."
        )
        
        prompt = f"""
        {system_prompt}
        
        Previous Context:
        {context}
        
        User Query: {user_input}
        
        Provide a comprehensive, structured, and actionable response following ethical hacking guidelines.
        Include practical examples, code snippets where relevant, and security recommendations.
        Ensure all suggestions are legal and ethical.
        """
        return prompt
    
    def analyze(self, prompt: str) -> Dict[str, Any]:
        """Send request to Gemini API"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
            
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 2048,
                },
                "safetySettings": [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
            }
            
            response = requests.post(
                config.GEMINI_URL,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    return {
                        'success': True,
                        'text': result['candidates'][0]['content']['parts'][0]['text'],
                        'raw': result
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No valid response from Gemini'
                    }
            else:
                return {
                    'success': False,
                    'error': f'API Error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return {
                'success': False,
                'error': f'Error: {str(e)}'
            }

gemini_ai = GeminiAI(config.GEMINI_API_KEY)

# ============ Bot Handlers ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    welcome_text = f"""
🔐 **Advanced Ethical Hacking AI Bot**
*Developer: Ziaul Islam*

Welcome {user.first_name}! 👋

I'm an AI-powered ethical hacking assistant using Google's Gemini AI.

**Features:**
🔍 Vulnerability Assessment
🛡️ Penetration Testing
📱 Mobile Security
🌐 Web Security
☁️ Cloud Security
🔎 OSINT Analysis
🔬 Malware Analysis
📊 Digital Forensics

**Commands:**
/help - Show this help message
/analyze - Start a new security analysis
/report - Generate detailed security report
/session - View session information
/clear - Clear session history

Select an analysis type from the menu below to begin! 🚀
    """
    
    keyboard = [
        [
            InlineKeyboardButton("🔍 Vulnerability Assessment", callback_data="va"),
            InlineKeyboardButton("🛡️ Penetration Testing", callback_data="pt")
        ],
        [
            InlineKeyboardButton("🌐 Web Security", callback_data="ws"),
            InlineKeyboardButton("📱 Mobile Security", callback_data="ms")
        ],
        [
            InlineKeyboardButton("☁️ Cloud Security", callback_data="cs"),
            InlineKeyboardButton("🔎 OSINT", callback_data="os")
        ],
        [
            InlineKeyboardButton("🔬 Malware Analysis", callback_data="ma"),
            InlineKeyboardButton("📊 Digital Forensics", callback_data="df")
        ],
        [
            InlineKeyboardButton("🔄 New Session", callback_data="new"),
            InlineKeyboardButton("📋 Generate Report", callback_data="report")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def handle_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle analysis type selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = session_manager.get_session(user_id)
    
    # Map callback data to AnalysisType
    type_map = {
        'va': AnalysisType.VULNERABILITY,
        'pt': AnalysisType.PENETRATION_TEST,
        'ws': AnalysisType.WEB_SECURITY,
        'ms': AnalysisType.MOBILE_SECURITY,
        'cs': AnalysisType.CLOUD_SECURITY,
        'os': AnalysisType.OSINT,
        'ma': AnalysisType.MALWARE_ANALYSIS,
        'df': AnalysisType.FORENSICS,
        'se': AnalysisType.SOCIAL_ENGINEERING,
        'ns': AnalysisType.NETWORK_SECURITY
    }
    
    if query.data == 'new':
        session.session_type = None
        session.history = []
        await query.edit_message_text(
            "🔄 **New Session Started**\n\n"
            "Select an analysis type from the menu to begin.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if query.data == 'report':
        await generate_report(update, context)
        return
    
    analysis_type = type_map.get(query.data)
    if analysis_type:
        session.session_type = analysis_type
        session.add_message("system", f"Started {analysis_type.value} analysis")
        
        await query.edit_message_text(
            f"✅ **{analysis_type.value.replace('_', ' ').title()} Analysis Mode**\n\n"
            f"Send me details about the target system or specific questions.\n\n"
            f"*Example queries:*\n"
            f"• Analyze a web application for OWASP Top 10 vulnerabilities\n"
            f"• Perform OSINT on a domain or IP address\n"
            f"• Assess cloud infrastructure security\n"
            f"• Identify social engineering attack vectors\n\n"
            f"Type /help for more options.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await query.edit_message_text(
            "⚠️ Invalid selection. Please try again.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    session = session_manager.get_session(user_id)
    
    if not session.session_type:
        await update.message.reply_text(
            "⚠️ Please select an analysis type first using the menu below.",
            reply_markup=await get_analysis_menu()
        )
        return
    
    # Add user message to history
    session.add_message("user", user_message)
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Create prompt for Gemini
    context_text = session.get_context()
    prompt = gemini_ai.create_prompt(
        session.session_type,
        user_message,
        context_text
    )
    
    # Get AI response
    response = gemini_ai.analyze(prompt)
    
    if response['success']:
        ai_response = response['text']
        session.add_message("assistant", ai_response)
        
        # Format response
        formatted_response = f"""
🧠 **AI Analysis Result**

{ai_response}

---
*Session: {session.session_type.value.replace('_', ' ').title()}*
*Messages: {len(session.history)//2}*
        """
        
        # Split long messages if needed
        if len(formatted_response) > 4096:
            parts = [formatted_response[i:i+4000] for i in range(0, len(formatted_response), 4000)]
            for part in parts:
                await update.message.reply_text(
                    part,
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await update.message.reply_text(
                formatted_response,
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        error_message = f"""
❌ **Error**

{response.get('error', 'Unknown error occurred')}

Please try again or /clear to reset the session.
        """
        await update.message.reply_text(
            error_message,
            parse_mode=ParseMode.MARKDOWN
        )

async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a comprehensive security report"""
    user_id = update.effective_user.id
    session = session_manager.get_session(user_id)
    
    if not session.history:
        await update.message.reply_text(
            "⚠️ No analysis history found. Start an analysis first!"
        )
        return
    
    # Create report prompt
    report_prompt = f"""
    Generate a comprehensive ethical hacking report based on the following analysis history.
    Include:
    1. Executive Summary
    2. Findings and Vulnerabilities
    3. Risk Assessment
    4. Recommended Actions
    5. Implementation Timeline
    
    Analysis History:
    {session.get_context()}
    
    Format the report professionally with sections, priorities, and actionable recommendations.
    """
    
    response = gemini_ai.analyze(report_prompt)
    
    if response['success']:
        report = f"""
📋 **SECURITY ANALYSIS REPORT**
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*User: {update.effective_user.first_name}*
*Session Type: {session.session_type.value if session.session_type else 'General'}*

---

{response['text']}

---
*This report is for educational purposes only.*
*Always ensure you have proper authorization for security testing.*
        """
        
        await update.message.reply_text(
            report[:4000],  # Telegram limit
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Send as document if too long
        if len(report) > 4000:
            with open("report.txt", "w") as f:
                f.write(report)
            await update.message.reply_document(
                document=open("report.txt", "rb"),
                filename=f"security_report_{datetime.now().strftime('%Y%m%d')}.txt"
            )
    else:
        await update.message.reply_text("Failed to generate report. Please try again.")

async def get_analysis_menu():
    """Create analysis selection menu"""
    keyboard = [
        [
            InlineKeyboardButton("🔍 Vulnerability", callback_data="va"),
            InlineKeyboardButton("🛡️ Pen Testing", callback_data="pt")
        ],
        [
            InlineKeyboardButton("🌐 Web Security", callback_data="ws"),
            InlineKeyboardButton("📱 Mobile", callback_data="ms")
        ],
        [
            InlineKeyboardButton("☁️ Cloud", callback_data="cs"),
            InlineKeyboardButton("🔎 OSINT", callback_data="os")
        ],
        [
            InlineKeyboardButton("🔬 Malware", callback_data="ma"),
            InlineKeyboardButton("📊 Forensics", callback_data="df")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🔐 **Ethical Hacking Bot Help**

**Available Commands:**
/start - Initialize the bot
/help - Show this help
/analyze - Show analysis menu
/report - Generate security report
/session - View session info
/clear - Clear history

**Analysis Types:**
• Vulnerability Assessment - Find system weaknesses
• Penetration Testing - Simulate attacks
• Web Security - Web app security
• Mobile Security - Mobile platform security
• Cloud Security - Cloud infrastructure
• OSINT - Open source intelligence
• Malware Analysis - Malware examination
• Digital Forensics - Incident investigation

**Tips:**
• Be specific in your queries
• Provide context about the target
• Ask for examples and code
• Request step-by-step guidance

**Security Notice:**
⚠️ This bot is for educational purposes only.
Always follow legal and ethical guidelines.
Do not test systems without proper authorization.
    """
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command"""
    user_id = update.effective_user.id
    session = session_manager.get_session(user_id)
    session.history = []
    session.session_type = None
    
    await update.message.reply_text(
        "🧹 **Session Cleared**\n\n"
        "All history has been cleared. Start fresh with /start",
        parse_mode=ParseMode.MARKDOWN
    )

async def session_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /session command"""
    user_id = update.effective_user.id
    session = session_manager.get_session(user_id)
    
    info = f"""
📊 **Session Information**
• Type: {session.session_type.value if session.session_type else 'None'}
• Messages: {len(session.history)//2}
• Last Activity: {session.last_activity.strftime('%H:%M:%S')}
• Session Duration: {int((datetime.now() - session.last_activity).seconds)} seconds
    """
    await update.message.reply_text(info)

# ============ Main Application ============

def main() -> None:
    """Start the bot"""
    try:
        # Create application
        application = Application.builder().token(config.TELEGRAM_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("session", session_command))
        
        # Callback query handler
        application.add_handler(CallbackQueryHandler(handle_analysis))
        
        # Message handler for user input
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                handle_message
            )
        )

        # Start bot
        logger.info("Starting Ethical Hacking Bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        raise

if __name__ == '__main__':
    main()