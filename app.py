from db_operations import create_users_table, create_purchase_tables, save_purchase_order
create_users_table()
create_purchase_tables()

import streamlit as st
from ai_agent import ask_ai
from erp_logic import handle_command
from user_auth import add_user, verify_user
import sqlite3
from datetime import datetime

# Estilos
with open("style.css", "r") as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Inicialización de sesión
if "username" not in st.session_state:
    st.session_state.username = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "conversation_mode" not in st.session_state:
    st.session_state.conversation_mode = "normal"
if "guided_purchase" not in st.session_state:
    st.session_state.guided_purchase = {}

# --- Login ---
def show_login_page():
    st.image("assets/logo.png", width=150, use_container_width=False)
    st.markdown('<h1 style="text-align:center;">Login</h1>', unsafe_allow_html=True)

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if verify_user(email, password):
            st.session_state.username = email
            st.success(f"Welcome back, {email}!")
            st.session_state.page = "main"
        else:
            st.error("Incorrect email or password.")

    if st.button("Create an account"):
        st.session_state.page = "create_account"

# --- Registro de cuenta ---
def show_create_account_page():
    st.markdown('<h1 style="text-align:center;">Create Account</h1>', unsafe_allow_html=True)

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Create Account"):
        if password != confirm_password:
            st.error("Passwords do not match.")
        else:
            if add_user(email, password):
                st.success("Account created! You can now log in.")
                st.session_state.page = "login"
            else:
                st.error("Email already exists.")

    if st.button("Back to Login"):
        st.session_state.page = "login"

# --- Vista para formulario manual ---
def show_purchase_form():
    st.markdown("<h1 style='text-align:center;'>New expense</h1>", unsafe_allow_html=True)

    if "purchase_items" not in st.session_state:
        st.session_state.purchase_items = [{}]

    with st.form("purchase_form", clear_on_submit=False):
        st.markdown("### Purchase Information")

        col1, col2 = st.columns(2)
        with col1:
            request_by = st.selectbox("Request by:", ["Carlos Torres", "Laura Díaz", "Ivan Alcaraz", "Rafael Flores", "Alejandro Torres"])
            request_date = st.date_input("Request date")
            approval_to = st.selectbox("Request approval to:", ["Carlos Torres", "Laura Díaz", "Ivan Alcaraz", "Rafael Flores", "Alejandro Torres"])
        with col2:
            supplier = st.selectbox("Supplier:", ["Palacio de Hierro", "Office Depot", "Otro"])
            area = st.selectbox("Area:", ["Hotel", "Restaurant", "Storage"])
            category = st.selectbox("Category:", ["Supplies", "Technology", "Furniture"])

        st.markdown("### Products")
        product_entries = []

        for i in range(len(st.session_state.purchase_items)):
            cols = st.columns([3, 2, 2, 2, 2])
            product = cols[0].text_input("Product", key=f"product_{i}")
            quantity = cols[1].number_input("Quantity", min_value=1, step=1, key=f"qty_{i}")
            unit_cost = cols[2].number_input("Unit Cost", min_value=0.0, step=0.01, key=f"unit_{i}")
            tax = cols[3].selectbox("Tax", ["IVA 16%", "0%", "Exempt"], key=f"tax_{i}")
            total = quantity * unit_cost * (1.16 if tax == "IVA 16%" else 1)
            cols[4].markdown(f"<div style='padding-top: 10px;'>${total:,.2f}</div>", unsafe_allow_html=True)

            product_entries.append({
                "product": product,
                "quantity": quantity,
                "unit_cost": unit_cost,
                "tax": tax,
                "total": total
            })

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Save order")
        with col2:
            add_product = st.form_submit_button("Add product")

    if submitted:
        save_purchase_order(request_by, request_date, approval_to, supplier, area, category, product_entries)
        st.success("Purchase order saved successfully!")
        st.session_state.purchase_items = [{}]

    elif add_product:
        st.session_state.purchase_items.append({})

# --- Vista de órdenes anteriores desde SQLite ---
def render_purchase_orders():
    st.title("Purchase Orders")

    conn = sqlite3.connect("erp.db")
    c = conn.cursor()

    c.execute("SELECT * FROM purchase_orders ORDER BY id DESC")
    orders = c.fetchall()

    if not orders:
        st.info("No hay órdenes registradas aún.")
        return

    for order in orders:
        order_id, _, request_by, request_date, approval, supplier, area, category = order
        st.subheader(f"Orden #{order_id}")
        st.markdown(f"""
        **Solicitante:** {request_by}  
        **Fecha:** {request_date}  
        **Aprobador:** {approval}  
        **Proveedor:** {supplier}  
        **Área:** {area}  
        **Categoría:** {category}  
        """)

        c.execute("SELECT product, quantity, unit_cost, taxes, total FROM purchase_items WHERE order_id = ?", (order_id,))
        items = c.fetchall()

        st.table([{
            "Producto": i[0],
            "Cantidad": i[1],
            "Precio Unitario": i[2],
            "Impuesto": i[3],
            "Total": i[4]
        } for i in items])

    conn.close()

# --- Chat Thot AI ---
def process_user_input(user_input):
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # Activar modo guiado si el usuario menciona una compra
        if any(keyword in user_input.lower() for keyword in ["compra", "orden", "pedido"]) and st.session_state.conversation_mode == "normal":
            st.session_state.conversation_mode = "guided"
            st.session_state.guided_purchase = {}
            ai_response = "Claro, te ayudaré a hacer una orden de compra. ¿Quién solicita la compra?"
            st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
            return

        # Si está en modo guiado, avanzar paso a paso
        if st.session_state.conversation_mode == "guided":
            guided = st.session_state.guided_purchase
            if "request_by" not in guided:
                guided["request_by"] = user_input
                ai_response = "¿Cuál es la fecha de la solicitud?"
            elif "request_date" not in guided:
                guided["request_date"] = user_input
                ai_response = "¿Quién la debe aprobar?"
            elif "approval_to" not in guided:
                guided["approval_to"] = user_input
                ai_response = "¿A qué proveedor se hará la compra?"
            elif "supplier" not in guided:
                guided["supplier"] = user_input
                ai_response = "¿En qué área se utilizará?"
            elif "area" not in guided:
                guided["area"] = user_input
                ai_response = "¿Cuál es la categoría de los productos?"
            elif "category" not in guided:
                guided["category"] = user_input
                ai_response = "Perfecto. Ahora dime el nombre del producto."
            elif "products" not in guided:
                guided["products"] = [{"product": user_input}]
                ai_response = "¿Cuál es la cantidad?"
            elif "quantity" not in guided["products"][-1]:
                guided["products"][-1]["quantity"] = int(user_input)
                ai_response = "¿Cuál es el precio unitario?"
            elif "unit_cost" not in guided["products"][-1]:
                guided["products"][-1]["unit_cost"] = float(user_input)
                ai_response = "¿Qué impuesto aplica? (IVA 16%, 0%, Exempt)"
            elif "tax" not in guided["products"][-1]:
                guided["products"][-1]["tax"] = user_input
                p = guided["products"][-1]
                tax_multiplier = 1.16 if p["tax"] == "IVA 16%" else 1
                p["total"] = p["quantity"] * p["unit_cost"] * tax_multiplier
                ai_response = "¿Quieres agregar otro producto? (sí/no)"
            else:
                if user_input.lower() == "sí":
                    guided["products"].append({})
                    ai_response = "Dime el nombre del producto."
                else:
                    save_purchase_order(
                        guided["request_by"],
                        guided["request_date"],
                        guided["approval_to"],
                        guided["supplier"],
                        guided["area"],
                        guided["category"],
                        guided["products"]
                    )
                    ai_response = "¡Orden de compra registrada exitosamente! ¿Necesitas algo más?"
                    st.session_state.conversation_mode = "normal"
                    st.session_state.guided_purchase = {}

            st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
        else:
            ai_response = ask_ai(user_input)
            st.session_state.chat_history.append({"role": "assistant", "content": ai_response})

# --- Página principal ---
def show_main_page():
    menu = st.sidebar.radio("Navigation", ["Chat with Thot AI", "Sales", "Suppliers", "Purchases", "Inventory"])
    subpage = None

    if menu == "Purchases":
        subpage = st.sidebar.radio("Purchases Menu", ["Registrar orden de compra", "Ver órdenes anteriores"])

    if menu == "Chat with Thot AI":
        st.markdown('<h1 style="text-align:center;">HORUX 360</h1>', unsafe_allow_html=True)
        st.subheader("Need help? Ask Thot AI")

        user_input = st.chat_input("What do you need help with?")
        process_user_input(user_input)

        for msg in st.session_state.chat_history:
            if msg["role"] == "system":
                continue
            with st.chat_message("user" if msg["role"] == "user" else "assistant"):
                st.markdown(msg["content"])

    elif menu == "Sales":
        st.subheader("Sales Dashboard")
    elif menu == "Suppliers":
        st.subheader("Suppliers Dashboard")
    elif menu == "Purchases":
        if subpage == "Registrar orden de compra":
            show_purchase_form()
        elif subpage == "Ver órdenes anteriores":
            render_purchase_orders()
    elif menu == "Inventory":
        st.subheader("Inventory Dashboard")

# --- Flujo principal ---
if st.session_state.username is None:
    if "page" not in st.session_state or st.session_state.page == "login":
        show_login_page()
    elif st.session_state.page == "create_account":
        show_create_account_page()
else:
    show_main_page()