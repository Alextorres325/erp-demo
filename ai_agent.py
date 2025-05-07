import openai
import os
import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ask_ai(prompt):
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "system",
                "content": (
                    "Eres Thot AI, un asistente de ERP para registrar órdenes de compra.\n"
                    "Tu trabajo es guiar al usuario paso a paso para recopilar los siguientes campos:\n"
                    "- request_by\n"
                    "- request_date (formato YYYY-MM-DD)\n"
                    "- approval_to\n"
                    "- supplier\n"
                    "- area\n"
                    "- category\n"
                    "- products: lista con product, quantity, unit_cost, tax, total\n\n"
                    "Cuando el usuario diga algo como 'sí', 'confirmado' o 'está bien', y ya tengas toda la información,\n"
                    "RESPONDE ÚNICAMENTE con el JSON final, sin ningún texto adicional, sin saludo y sin explicación.\n\n"
                    "Ejemplo de formato de salida:\n"
                    "{\n"
                    "  \"request_by\": \"Laura Perez\",\n"
                    "  \"request_date\": \"2025-05-05\",\n"
                    "  \"approval_to\": \"Rafael Flores\",\n"
                    "  \"supplier\": \"Hershey\",\n"
                    "  \"area\": \"Recursos Humanos\",\n"
                    "  \"category\": \"Alimentos\",\n"
                    "  \"products\": [\n"
                    "    {\"product\": \"Chocolates\", \"quantity\": 10, \"unit_cost\": 30.0, \"tax\": \"IVA 16%\", \"total\": 348.0}\n"
                    "  ]\n"
                    "}\n\n"
                    "No agregues explicaciones, emojis, ni texto fuera del JSON. Si falta información, continúa preguntando."
                )
            }
        ]

    st.session_state.chat_history.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=st.session_state.chat_history,
            temperature=0.4
        )
        reply = response.choices[0].message.content.strip()

        # ✅ Manejar JSON que puede usar "productos" en vez de "products"
        try:
            parsed_json = json.loads(reply)
            if "productos" in parsed_json and "products" not in parsed_json:
                parsed_json["products"] = parsed_json.pop("productos")
            return parsed_json
        except json.JSONDecodeError:
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            return reply

    except Exception as e:
        return f"Error con la IA: {e}"