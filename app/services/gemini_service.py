from google import genai
from google.genai import types
from flask import current_app

from .rag_service import RAGService


class GeminiService:
    @staticmethod
    def ask_assistant(message, history=None):
        """
        Send a message to the Gemini Agricultural Assistant.

        In DEMO_MODE, returns a mock response when no valid API key
        is configured.
        """

        api_key = current_app.config.get("GEMINI_API_KEY")
        demo_mode = current_app.config.get("DEMO_MODE", True)

        # ---------------------------------------------------------
        # DEMO MODE / API KEY CHECK
        # ---------------------------------------------------------
        if not api_key or api_key == "your_gemini_api_key_here":
            if demo_mode:
                return {
                    "success": True,
                    "response": (
                        "मैं AgriVision AI Demo Assistant हूँ। "
                        f"आपने पूछा: '{message}'।\n\n"
                        "Production environment में Google Gemini का "
                        "expert agricultural response प्राप्त करने के लिए "
                        "GEMINI_API_KEY configure करें।"
                    ),
                }

            return {
                "success": False,
                "error": "Gemini API key is not configured.",
            }

        try:
            # -----------------------------------------------------
            # GEMINI CLIENT
            # -----------------------------------------------------
            client = genai.Client(api_key=api_key)

            model_name = current_app.config.get(
                "GEMINI_MODEL",
                "gemini-2.5-flash",
            )

            # -----------------------------------------------------
            # RAG CONTEXT
            # -----------------------------------------------------
            rag_context = RAGService.search(message)

            # -----------------------------------------------------
            # SYSTEM INSTRUCTION
            # -----------------------------------------------------
            system_instruction = """
आप AgriVision AI हैं, एक expert agricultural assistant
जो किसानों की सहायता करने के लिए बनाया गया है।

आपका उद्देश्य:
- फसल रोगों की जानकारी देना
- फसल की उपज बेहतर करने में सहायता करना
- खेती से संबंधित practical advice देना
- farming best practices समझाना
- किसानों को सुरक्षित और actionable guidance देना

महत्वपूर्ण नियम:

1. हमेशा हिंदी (हिंदी भाषा) में उत्तर दें।
2. कभी भी अंग्रेज़ी में पूरा उत्तर न दें।
3. Technical agricultural terms आवश्यक होने पर English में
   लिख सकते हैं, लेकिन explanation हिंदी में होना चाहिए।
4. उत्तर concise और mobile-friendly रखें।
5. किसान को practical steps दें।
6. यदि diagnosis निश्चित नहीं है तो uncertainty स्पष्ट बताएं।
7. गंभीर crop disease या बड़े आर्थिक नुकसान की स्थिति में
   local agriculture expert / कृषि अधिकारी से संपर्क करने की सलाह दें।
8. बिना पर्याप्त जानकारी के निश्चित diagnosis न दें।

FORMAT THE RESPONSE FOR A MOBILE CHAT UI:

- Use ### for major sections.
- Do not use # or ## unless absolutely necessary.
- Use **bold** for labels such as लाभ, उद्देश्य, विशेषता, पात्रता.
- Use bullet lists for multiple points.
- Use numbered lists for sequential steps.
- Use --- only when separating major sections.
- Keep paragraphs short.
- Do not use code blocks for normal agricultural information.
- Do not return JSON unless the user explicitly asks for JSON.
- Do not use excessive Markdown formatting.
"""

            # -----------------------------------------------------
            # ADD RAG CONTEXT
            # -----------------------------------------------------
            if rag_context:
                system_instruction += f"""

स्थानीय कृषि संदर्भ:

नीचे दिए गए स्थानीय agricultural policies और guidelines
का उपयोग केवल तभी करें जब वे user के प्रश्न से संबंधित हों:

--- BEGIN LOCAL CONTEXT ---
{rag_context}
--- END LOCAL CONTEXT ---
"""

            # -----------------------------------------------------
            # CONVERT DATABASE HISTORY TO GEMINI HISTORY
            # -----------------------------------------------------
            gemini_history = []

            if history:
                for msg in history:
                    role = "user" if msg.role == "user" else "model"

                    gemini_history.append(
                        types.Content(
                            role=role,
                            parts=[
                                types.Part.from_text(
                                    text=msg.content
                                )
                            ],
                        )
                    )

            # -----------------------------------------------------
            # CREATE CHAT
            # -----------------------------------------------------
            chat = client.chats.create(
                model=model_name,
                history=gemini_history,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                ),
            )

            # -----------------------------------------------------
            # SEND USER MESSAGE
            # -----------------------------------------------------
            response = chat.send_message(
                message=message
            )

            # -----------------------------------------------------
            # RESPONSE
            # -----------------------------------------------------
            return {
                "success": True,
                "response": response.text,
            }

        except Exception as e:
            current_app.logger.exception(
                "Gemini assistant error"
            )

            return {
                "success": False,
                "error": str(e),
            }
