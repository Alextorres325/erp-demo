import streamlit as st
import sqlite3

def get_db_connection():
    return sqlite3.connect("erp.db")

def render_purchase_orders():
    st.title("Purchase Orders")

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
    c = conn.cursor()

    # Obtener todas las órdenes de compra
    c.execute("SELECT * FROM purchase_orders ORDER BY id DESC")
    orders = c.fetchall()

    if not orders:
        st.info("No hay órdenes registradas aún.")
        return

    for order in orders:
        order_id = order["id"]
        st.subheader(f"Orden #{order_id}")
        st.markdown(f"""
        **Solicita:** {order["request_by"]}  
        **Fecha de solicitud:** {order["request_date"]}  
        **Aprueba:** {order["request_approval"]}  
        **Proveedor:** {order["supplier"]}  
        **Área:** {order["area"]}  
        **Categoría:** {order["category"]}
        """)

        # Obtener productos de esta orden
        c.execute("""
            SELECT product, quantity, unit_cost, taxes, total
            FROM purchase_items
            WHERE order_id = ?
        """, (order_id,))
        products = c.fetchall()

        if products:
            st.markdown("**Productos:**")
            st.table([
                {
                    "Producto": p["product"],
                    "Cantidad": p["quantity"],
                    "Costo Unitario": f"${p['unit_cost']:.2f}",
                    "Impuesto": p["taxes"],
                    "Total": f"${p['total']:.2f}"
                }
                for p in products
            ])
        else:
            st.warning("No hay productos registrados en esta orden.")

    conn.close()