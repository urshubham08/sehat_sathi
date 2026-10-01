from html import escape

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from src.ai_chat.services import analyze_prescription_image
from src.ai_chat.services import ask_gemini


router = APIRouter(
    prefix="/ai-chat",
    tags=["AI Chat"]
)


def get_logged_in_user(request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please login first."
        )

    return user_id


@router.get("/page", response_class=HTMLResponse)
def ai_chat_page(request: Request):
    get_logged_in_user(request)

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sehat Saathi AI Assistant</title>

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <style>
            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f4f7f9;
            }

            .header {
                background: #1976d2;
                color: white;
                padding: 18px 25px;
            }

            .header h1 {
                margin: 0;
                font-size: 24px;
            }

            .header p {
                margin: 5px 0 0;
                opacity: 0.9;
            }

            .chat-container {
                max-width: 900px;
                height: calc(100vh - 100px);
                margin: 20px auto;
                background: white;
                border-radius: 14px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);

                display: flex;
                flex-direction: column;
                overflow: hidden;
            }

            .messages {
                flex: 1;
                padding: 25px;
                overflow-y: auto;
            }

            .message {
                margin-bottom: 18px;
                display: flex;
            }

            .message.user {
                justify-content: flex-end;
            }

            .message.ai {
                justify-content: flex-start;
            }

            .bubble {
                max-width: 75%;
                padding: 14px 17px;
                border-radius: 12px;
                line-height: 1.5;
                white-space: pre-wrap;
            }

            .user .bubble {
                background: #1976d2;
                color: white;
            }

            .ai .bubble {
                background: #eef3f7;
                color: #222;
            }

            .input-area {
                border-top: 1px solid #ddd;
                padding: 15px;
                display: flex;
                gap: 10px;
            }

            .input-area textarea {
                flex: 1;
                resize: none;
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 12px;
                font-family: Arial, sans-serif;
                font-size: 15px;
                min-height: 50px;
            }

            .input-area button {
                background: #1976d2;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 22px;
                cursor: pointer;
                font-size: 15px;
            }

            .input-area button:hover {
                background: #125ca3;
            }

            .input-area button:disabled {
                background: #999;
                cursor: not-allowed;
            }

            .disclaimer {
                padding: 10px 20px;
                font-size: 12px;
                color: #666;
                text-align: center;
                background: #fafafa;
            }

            @media (max-width: 600px) {
                .chat-container {
                    margin: 0;
                    height: calc(100vh - 85px);
                    border-radius: 0;
                }

                .bubble {
                    max-width: 90%;
                }

                .input-area {
                    padding: 10px;
                }

                .input-area button {
                    padding: 0 15px;
                }
            }
        </style>
    </head>

    <body>

        <div class="header">
            <h1>🩺 Sehat Saathi</h1>
            <p>Sehat ki dekhbhaal, aasaan aur smart.</p>
        </div>

        <div class="chat-container">

            <div class="messages" id="messages">

                <div class="message ai">
                    <div class="bubble">
                        Namaste! 👋

                        Main Sehat Saathi hoon.

                        Aap mujhse general health information,
                        symptoms ke basic information, medical reports
                        ko samajhne aur healthcare guidance ke baare
                        mein pooch sakte hain.

                        Main diagnosis ya prescription nahi deta.
                    </div>
                </div>

            </div>

            <div class="disclaimer">
                ⚠️ Sehat Saathi general health information provide karta hai.
                Emergency ya serious symptoms ke liye qualified doctor/
                emergency medical service se contact karein.
            </div>

            <form class="input-area" id="chatForm">

                <textarea
                    id="question"
                    placeholder="Apna health question likhiye..."
                    required
                ></textarea>

                <button type="submit" id="sendButton">
                    Send
                </button>

            </form>

        </div>

        <script>
            const form = document.getElementById("chatForm");
            const questionInput = document.getElementById("question");
            const messages = document.getElementById("messages");
            const sendButton = document.getElementById("sendButton");


            function addMessage(text, type) {

                const message = document.createElement("div");

                message.className = "message " + type;

                const bubble = document.createElement("div");

                bubble.className = "bubble";

                bubble.textContent = text;

                message.appendChild(bubble);

                messages.appendChild(message);

                messages.scrollTop = messages.scrollHeight;
            }


            form.addEventListener("submit", async function(event) {

                event.preventDefault();

                const question = questionInput.value.trim();

                if (!question) {
                    return;
                }

                addMessage(question, "user");

                questionInput.value = "";

                sendButton.disabled = true;
                sendButton.textContent = "Thinking...";


                try {

                    const response = await fetch("/ai-chat/ask", {

                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/x-www-form-urlencoded"
                        },

                        body: new URLSearchParams({
                            question: question
                        })

                    });


                    const data = await response.json();


                    if (!response.ok) {

                        addMessage(
                            data.detail ||
                            "Something went wrong.",
                            "ai"
                        );

                        return;
                    }


                    addMessage(
                        data.answer,
                        "ai"
                    );

                }

                catch (error) {

                    addMessage(
                        "Sorry, server se response nahi aa raha.",
                        "ai"
                    );

                }

                finally {

                    sendButton.disabled = false;
                    sendButton.textContent = "Send";

                    questionInput.focus();
                }

            });


            questionInput.addEventListener(
                "keydown",
                function(event) {

                    if (
                        event.key === "Enter" &&
                        !event.shiftKey
                    ) {
                        event.preventDefault();
                        form.requestSubmit();
                    }

                }
            );

        </script>

    </body>
    </html>
    """


@router.post("/ask")
def ask_question(
    request: Request,
    question: str = Form(...)
):
    get_logged_in_user(request)

    question = question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Please enter a question."
        )

    if len(question) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Question is too long. Please keep it under 2000 characters."
        )

    try:
        answer = ask_gemini(question)

        return {
            "answer": answer
        }

    except Exception as error:
        print("AI CHAT ERROR:", error)

        raise HTTPException(
            status_code=500,
            detail="AI assistant is temporarily unavailable."
        )
