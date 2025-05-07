import streamlit as st
from datetime import date
import re
import json
from db_operations import save_purchase_order

REQUIRED_FIELDS = ["request_by", "request_date", "approval_to", "supplier", "area", "category", "products"]

def handle_command(ai_response: str | dict) -> str:
    state = st.session_state
    if "pending_order" not in state:
        state.pending_order = {}

    order = state.pending_order

    # ✅ Si la IA respondió en JSON (como dict), intentamos registrar la orden directamente
    if isinstance(ai_response, dict):
        try:
            print("JSON recibido:", ai_response)

            # Mapear "productos" -> "products" si es necesario
            if "products" not in ai_response and "productos" in ai_response:
                ai_response["products"] = ai_response.pop("productos")

            # Convertir fecha si viene como string
            if isinstance(ai_response.get("request_date"), str):
                ai_response["request_date"] = date.fromisoformat(ai_response["request_date"])

            # Convertir unit_cost y total si son strings con "$"
            for product in ai_response.get("products", []):
                for key in ["unit_cost", "total"]:
                    if isinstance(product.get(key), str):
                        product[key] = float(product[key].replace("$", "").replace(",", "").strip())

            save_purchase_order(
                request_by=ai_response["request_by"],
                request_date=ai_response["request_date"],
                approval_to=ai_response["approval_to"],
                supplier=ai_response["supplier"],
                area=ai_response["area"],
                category=ai_response["category"],
                product_entries=ai_response["products"]
            )

            del state.pending_order
            print("Orden registrada desde JSON")
            return "Orden registrada exitosamente. Puedes verla en la pestaña *Purchases*."

        except Exception as e:
            print("❌ Error al guardar desde JSON:", e)
            return f"Ocurrió un error al guardar la orden: {e}"

    # ✅ Si es texto, usar flujo guiado
    if isinstance(ai_response, str):
        print("📩 Respuesta de IA (texto):", ai_response)
        message = ai_response.strip().lower()

        if "orden de compra" in message or "comprar" in message:
            order.clear()
            order["intent"] = "purchase"
            order["products"] = []
            return "Perfecto. ¿Quién solicita la compra?"

        if order.get("intent") == "purchase":

            if "request_by" not in order:
                order["request_by"] = ai_response
                return "¿Cuál es la fecha de solicitud? (aaaa-mm-dd)"

            if "request_date" not in order:
                try:
                    order["request_date"] = date.fromisoformat(ai_response.strip())
                    return "¿Quién debe aprobar esta solicitud?"
                except Exception:
                    return "Fecha inválida. Usa el formato: 2025-05-05"

            if "approval_to" not in order:
                order["approval_to"] = ai_response
                return "¿Quién es el proveedor?"

            if "supplier" not in order:
                order["supplier"] = ai_response
                return "¿A qué área pertenece esta compra?"

            if "area" not in order:
                order["area"] = ai_response
                return "¿Cuál es la categoría de la compra?"

            if "category" not in order:
                order["category"] = ai_response
                return "Describe el primer producto: *(ej. 3 mesas por 1200 pesos con IVA 16%)*"

            # ✅ Producto nuevo o fin de productos
            if "products" in order:
                if message.strip() == "no":
                    if is_order_complete(order):
                        try:
                            if isinstance(order["request_date"], str):
                                order["request_date"] = date.fromisoformat(order["request_date"])

                            save_purchase_order(
                                request_by=order["request_by"],
                                request_date=order["request_date"],
                                approval_to=order["approval_to"],
                                supplier=order["supplier"],
                                area=order["area"],
                                category=order["category"],
                                product_entries=order["products"]
                            )
                            del state.pending_order
                            print("Orden registrada paso a paso")
                            return "Orden registrada exitosamente. Puedes verla en la pestaña *Purchases*."
                        except Exception as e:
                            print("Error al guardar paso a paso:", e)
                            return f"Error al guardar la orden: {e}"
                    else:
                        return "Faltan datos para completar la orden. ¿Puedes verificar lo que falta?"

                # Agregar producto
                try:
                    product_data = extract_product_data(ai_response)
                    order["products"].append(product_data)
                    return "Producto agregado. ¿Quieres agregar otro producto? Si no, responde 'no'."
                except Exception as e:
                    return f"No entendí el producto. Usa el formato: *3 mesas por 1200 pesos con IVA 16%*. Detalle del error: {e}"

    return "No entendí la instrucción. ¿Puedes repetirla por favor?"


def extract_product_data(text: str) -> dict:
    """
    Extrae producto desde texto tipo:
    '3 mesas por 1200 pesos con IVA 16%' o variantes similares.
    """
    pattern = r'(\d+)\s+([a-zA-Záéíóúñ\s]+?)\s*(?:a|por|en)?\s*(\d+(?:\.\d+)?)\s*(?:pesos|mxn)?\s*(con\s*IVA\s*16%)?'
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        raise ValueError("Formato inválido")

    quantity = int(match.group(1))
    product = match.group(2).strip()
    unit_cost = float(match.group(3))
    tax = "IVA 16%" if match.group(5) else "0%"
    total = unit_cost * quantity * (1.16 if "16" in tax else 1.0)

    return {
        "product": product,
        "quantity": quantity,
        "unit_cost": unit_cost,
        "tax": tax,
        "total": total
    }


def is_order_complete(order: dict) -> bool:
    missing = [f for f in REQUIRED_FIELDS if f not in order or not order[f]]
    if missing:
        print("Campos faltantes:", missing)
    return not missing