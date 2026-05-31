import sqlite3
import os

# Define path to the same store.db file in the current directory
DB_PATH = os.path.join(os.path.dirname(__file__), "store.db")

def get_average_rating(product_id: int) -> dict:
    """
    Calculates the average rating and total review count for a single product ID.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = """
        SELECT AVG(rating), COUNT(rating) 
        FROM reviews 
        WHERE product_id = ?
    """
    cursor.execute(query, (product_id,))
    row = cursor.fetchone()
    conn.close()
    
    # If there are no reviews, row[0] (AVG) will be None
    avg_rating = round(row[0], 2) if row[0] is not None else 0.0
    review_count = row[1] if row[1] is not None else 0
    
    return {
        "product_id": product_id,
        "average_rating": avg_rating,
        "total_reviews": review_count
    }


def get_reviews_for_products(product_ids: list) -> dict:
    """
    Retrieves all review details (reviewer, rating, and text) for a list of product IDs.
    This structured data is perfectly optimized to pass directly into your LLM agent's context.
    """
    if not product_ids:
        return {}
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Generate placeholders (?, ?, ...) based on the number of IDs passed in
    placeholders = ",".join(["?"] * len(product_ids))
    query = f"""
        SELECT r.product_id, p.name, r.rating, r.reviewer_name, r.review_text 
        FROM reviews r
        JOIN products p ON r.product_id = p.id
        WHERE r.product_id IN ({placeholders})
    """
    
    cursor.execute(query, tuple(product_ids))
    rows = cursor.fetchall()
    conn.close()
    
    # Organize the results cleanly by product_id
    results = {}
    for pid in product_ids:
        results[pid] = {
            "product_name": None,
            "reviews": []
        }
        
    for row in rows:
        pid, p_name, rating, reviewer, text = row
        results[pid]["product_name"] = p_name
        results[pid]["reviews"].append({
            "reviewer": reviewer,
            "rating": rating,
            "text": text
        })
        
    return results


# --- MAIN TEST BLOCK ---
if __name__ == "__main__":
    print("="*60)
    print("🧪 TESTING REVIEWS API CONNECTION")
    print("="*60)
    print(f"Target Database Path: {DB_PATH}\n")
    
    # Ensure the DB file exists before running tests
    if not os.path.exists(DB_PATH):
        print("❌ Error: 'store.db' not found. Please run 'setup_db.py' first to create it.")
    else:
        # 1. Test Single Product Average Rating (Testing Honey ID 1: Organic Raw Honey)
        test_single_id = 1
        print(f"1. Fetching average rating for Product ID {test_single_id}...")
        avg_data = get_average_rating(test_single_id)
        print(f"   Result: {avg_data}\n")
        
        # 2. Test Batch Product Reviews for Agent Context (Testing IDs 1, 9, and 23)
        # ID 1 = Honey, ID 9 = Olive Oil, ID 23 = Ethiopian Coffee
        test_batch_ids = [1, 9, 23]
        print(f"2. Fetching detailed reviews for Product IDs {test_batch_ids}...")
        batch_reviews = get_reviews_for_products(test_batch_ids)
        
        # Nicely print the dictionary structure to check its payload
        for pid, data in batch_reviews.items():
            print(f"\n📦 Product ID {pid}: {data['product_name']}")
            if not data["reviews"]:
                print("   (No reviews found)")
            for review in data["reviews"]:
                print(f"   ⭐ {review['rating']} | {review['reviewer']}: \"{review['text']}\"")
                
    print("\n" + "="*60)
    print("🏁 TEST COMPLETE")
    print("="*60)