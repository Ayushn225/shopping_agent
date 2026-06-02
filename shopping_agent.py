import base64
import json
import os
import sqlite3
from typing import Optional

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from reviews_api import get_average_rating

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "store.db")

llm = ChatGroq(model="qwen/qwen3-32b", temperature=0)
vision_llm = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0)
@tool
def get_user_prefrences(user_id: str = "default_user") ->str:
    """
    Retrieve the saved shopping preferences for a user (e.g., maximum price limit, organic filter).
    Returns a JSON string containing preferences like max_price and prefers_organic.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            max_price REAL,
            prefers_organic INTEGER
        )
    """)
    conn.commit()

    cursor.execute("SELECT max_price, prefers_organic FROM user_preferences WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        # Default fallback values if they haven't saved anything yet
        return json.dumps({"max_price": None, "prefers_organic": None})
    
    return json.dumps({
        "max_price": row[0],
        "prefers_organic": bool(row[1]) if row[1] is not None else None
    })

@tool
def update_user_prefrences(
    max_price: Optional[float] = None, 
    prefers_organic: Optional[bool] = None, 
    user_id: str= "default_user",
    clear_all: bool = False,
    ) ->str:
    """
    Save, update, or clear the user's shopping preferences in the database.
    Set clear_all=True if the user wants to reset/remove their preferences.
    """

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            max_price REAL,
            prefers_organic INTEGER
        )
    """)

    cursor.execute("SELECT max_price, prefers_organic FROM user_preferences WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if clear_all:
        cursor.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return "All your personalized shopping preferences have been cleared and reset."

    # Establish fallback defaults if row is None (First-time user)
    current_max = row[0] if row is not None else None
    current_organic = row[1] if row is not None else None

    current_max = row[0] if row else None
    current_organic = row[1] if row else None

    new_max = max_price if max_price is not None else current_max
    new_organic = 1 if prefers_organic is True else (0 if prefers_organic is False else current_organic)

    cursor.execute("""
        INSERT INTO user_preferences (user_id, max_price, prefers_organic)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            max_price = excluded.max_price,
            prefers_organic = excluded.prefers_organic
    """, (user_id, new_max, new_organic))

    conn.commit()
    conn.close()
    
    return f"Preferences updated successfully: Max Price = ${new_max if new_max else 'None'}, Prefers Organic = {bool(new_organic) if new_organic is not None else 'None'}."

@tool
def search_products(query: str, max_price: Optional[float] = None, is_organic: Optional[bool] = None)->str:
    """
    Search the product database by keyword (matched against name, description, and category).
    Optionally filter by maximum price and/or organic status.
    Returns a JSON array of matching products, each with: id, name, category, price,
    description, is_organic.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sql = "SELECT id, name, category, price, description, is_organic FROM products WHERE 1=1"
    params: list = []

    if query:
        sql += " AND (name LIKE ? OR description LIKE ? OR category LIKE ?)"

        like = f"%{query}%"

        params.extend([like, like, like]) 
    
    if max_price is not None:
        sql += " AND price <= ?"
        params.append(max_price)

    if is_organic is not None:
        sql += " AND is_organic = ?"
        params.append(1 if is_organic else 0)

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    products = [
        {
            "id":          row[0],
            "name":        row[1],
            "category":    row[2],
            "price":       row[3],
            "description": row[4],
            "is_organic":  bool(row[5]),
        }
        for row in rows
    ]

    return json.dumps(products)

@tool 
def get_rating(product_id: int) -> str:
    """
    Get the average customer rating and total review count for a product by its ID.
    Returns a JSON object with: product_id, average_rating, review_count.
    """
    result = get_average_rating(product_id)
    return json.dumps(result)

@tool 
def checkout(product_id: int)-> str:
    """
    Place an order for the given product ID. Saves the order to the database and returns
    a confirmation message with the order ID, product name, and price.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return f"Error: product with ID {product_id} not found."
    
    name, price = row
    cursor.execute(
        "INSERT INTO orders (product_id, product_name, price) VALUES (?, ?, ?)",
        (product_id, name, price),
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return (
        f"Order #{order_id} confirmed! '{name}' has been successfully ordered for ${price:.2f}. "
        f"Your order will arrive in 3-5 business days. Thank you for shopping with us!"
    )

@tool
def describe_product_image(image_path: str) ->str:
    """
    Analyze a product image and return its key attributes as a JSON object.
    Use this when the user uploads a photo of a product they are interested in.
    The returned attributes can be used directly with search_products.
    """

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    message = HumanMessage(content = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{image_data}"},
        },
        {
            "type": "text",
            "text":(
                "Look at this product image and extract its key attributes. "
                "Return ONLY a JSON object with these fields:\n"
                "- product_type: what kind of product it is (e.g. honey, olive oil, almonds)\n"
                "- search_query: a short keyword to search for it (e.g. 'honey', 'olive oil')\n"
                "- is_organic: true if the label says organic, false if not, null if unclear\n"
                "- description: one sentence describing the product"
            ),
        },
    ])

    response = vision_llm.invoke([message])
    return response.content

@tool
def get_order_history() ->str:
    """
    Retrieve the historical list of all past orders placed by the user from the database.
    Returns a JSON array containing details like order order_id, product_id, product_name, and price.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, product_id, product_name, price FROM orders ORDER BY id DESC")
        rows = cursor.fetchall()

        if not rows:
            return json.dumps({"message": "You haven't placed any orders yet."})
        
        orders = [
            {
                "order_id": row[0],
                "product_id": row[1],
                "product_name": row[2],
                "price": row[3]
            }
            for row in rows
        ]

        return json.dumps(orders)

    except sqlite3.OperationalError as e:
        return json.dumps({"error": f"Database error: {str(e)}. Ensure the orders table exists."})
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


agent = create_agent(
    model = llm,
    tools= [
        search_products, 
        get_rating, 
        checkout, 
        describe_product_image, 
        get_order_history,
        get_user_prefrences,
        update_user_prefrences,
        ],
    system_prompt= (
        "You are a helpful shopping assistant. Follow these rules strictly.\n\n"

        "USER PREFERENCES — when the user updates their shopping settings (e.g., 'always prefer organic', 'never show items over $20'):\n"
        "1. Call update_user_preferences with the extracted constraints.\n"
        "2. Confirm to the user that their setting has been locked into their profile.\n\n"

        "ORDER HISTORY — when the user asks about past orders (e.g., 'What have I ordered before?', 'show my history'):\n"
        "1. Call get_order_history to retrieve past transactions.\n"
        "2. Parse the returned JSON data.\n"
        "3. Present the list of past orders to the user clearly with Order IDs, Product Names, and Prices in plain text.\n"
        "4. If no orders exist, politely inform them.\n\n"

        "IMAGE SEARCH — when the user provides an image path:\n"
        "1. Call describe_product_image with the path to identify the product.\n"
        "2. Call get_user_preferences to see if they have profile filters.\n"
        "3. Use the image data combined with profile preferences to call search_products.\n"
        "4. Continue with the BROWSING flow from step 2 onwards.\n\n"

        "BROWSING — when the user describes what they want to buy:\n"
        "1. ALWAYS call get_user_preferences FIRST to check if the user has active restrictions (like organic choice or budget limits).\n"
        "2. Call search_products to find matching items. You must apply the user's stored profile filters automatically UNLESS the user explicitly overwrites them in their current text prompt.\n"
        "3. For each candidate, call get_rating to retrieve its average rating.\n"
        "4. Filter by the user's minimum rating if specified.\n"
        "5. Present qualifying products as a numbered list. For each item use this exact format "
        "   (plain text, no backticks, no code blocks, no bold, no italic):\n\n"
        "   #<number>. <name> (ID:<product_id>) — $<price> ★<rating> — <organic or non-organic>\n\n"
        "   Add a blank line between each product entry for readability. "
        "   Always include (ID:X) so you can reference it later.\n"
        "6. If only one product qualifies, still show it in the list and ask: "
        "   'Would you like to order it? Just say yes or give me the number.'\n"
        "7. Do NOT call checkout at this stage.\n\n"

        "ORDERING — when the user confirms they want to buy (e.g. 'yes', 'sure', 'go ahead', "
        "'order number 2', 'the first one', 'get me #3'):\n"
        "1. Look at your previous message to find the (ID:X) for the chosen product "
        "   (if only one was listed and the user says 'yes', use that product's ID).\n"
        "2. Call checkout with that product_id (the number from (ID:X)).\n"
        "3. Confirm the order to the user in plain text.\n\n"

        "Never place an order unless the user explicitly confirms. "
        "Never guess a product_id — always take it from the (ID:X) in your own previous message."
    ),
)

if __name__ == "__main__":
    print("--- Session 1: Setting Preferences ---")
    setup_result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": "Hey! From now on, I always prefer organic products and I never want items over $20."
        }]
    })
    print(setup_result["messages"][-1].content)
    print("\n" + "="*40 + "\n")

    print("--- Session 2: Verifying Preference Retention ---")
    query_result = agent.invoke({
        "messages": [{
            "role": "user",
            "content": "What are my preferences right now?"
        }]
    })
    print(query_result["messages"][-1].content)