"""CampusLoop: a one-screen, in-memory student-to-student marketplace demo."""
import html
import gradio as gr
from dotenv import load_dotenv

from gemma_client import ask, ask_with_image, make_chat

load_dotenv()

APP_NAME = "CampusLoop"
CATEGORIES = [
    "Books & Notes",
    "Electronics",
    "Hostel & Room",
    "Cycles & Sports",
    "Art & Stationery",
    "Other",
]
PICKUP_POINTS = ["Main Gate", "Library Entrance", "Campus Canteen", "Department Block"]

# Sample content is deliberately local demo data. No database is used.
SEED_LISTINGS = [
    {
        "id": "demo-1", "title": "Engineering Mathematics Vol. 1", "category": "Books & Notes",
        "price": 180, "condition": "Good", "seller": "Riya S.",
        "description": "Clean pages, a few pencil marks. Useful for first-year revision.",
        "pickup": "Library Entrance", "emoji": "📚", "demo": True,
    },
    {
        "id": "demo-2", "title": "Wireless Mouse", "category": "Electronics",
        "price": 250, "condition": "Like new", "seller": "Kunal M.",
        "description": "Comfortable wireless mouse. Receiver included and buttons tested.",
        "pickup": "Main Gate", "emoji": "🖱️", "demo": True,
    },
    {
        "id": "demo-3", "title": "Desk Study Lamp", "category": "Hostel & Room",
        "price": 320, "condition": "Good", "seller": "Meera P.",
        "description": "Warm and cool light modes. Works well for late study sessions.",
        "pickup": "Department Block", "emoji": "💡", "demo": True,
    },
    {
        "id": "demo-4", "title": "Acrylic Paint Set", "category": "Art & Stationery",
        "price": 140, "condition": "Good", "seller": "Dev A.",
        "description": "12 colours; most tubes are still nearly full.",
        "pickup": "Campus Canteen", "emoji": "🎨", "demo": True,
    },
    {
        "id": "demo-5", "title": "Badminton Racket", "category": "Cycles & Sports",
        "price": 400, "condition": "Used", "seller": "Aman T.",
        "description": "A practical starter racket with a cover included.",
        "pickup": "Main Gate", "emoji": "🏸", "demo": True,
    },
    {
        "id": "demo-6", "title": "DBMS Quick Notes", "category": "Books & Notes",
        "price": 70, "condition": "Good", "seller": "Sara K.",
        "description": "Short handwritten revision notes for key DBMS topics.",
        "pickup": "Library Entrance", "emoji": "📝", "demo": True,
    },
]

EMOJI_BY_CATEGORY = {
    "Books & Notes": "📚", "Electronics": "🎧", "Hostel & Room": "🪴",
    "Cycles & Sports": "🚲", "Art & Stationery": "🎨", "Other": "✨",
}


def _esc(value):
    return html.escape(str(value))


def _money(value):
    return f"₹{int(value):,}"


def render_listings(listings, query="", category="All categories"):
    """Render listing data as safe HTML; user-entered text is escaped."""
    q = (query or "").strip().lower()
    visible = [item for item in listings
               if (not q or q in item["title"].lower() or q in item["description"].lower()
                   or q in item["category"].lower())
               and (category == "All categories" or item["category"] == category)]
    if not visible:
        return '<div class="empty-state"><div class="empty-icon">🔎</div><b>No matches yet</b><p>Try a different keyword or category.</p></div>'

    cards = []
    for item in visible:
        badge = '<span class="demo-pill">DEMO LISTING</span>' if item.get("demo") else '<span class="fresh-pill">JUST ADDED</span>'
        cards.append(f"""
        <article class="listing-card">
          <div class="item-art"><span>{_esc(item.get('emoji', '✨'))}</span>{badge}</div>
          <div class="item-content">
            <div class="item-meta"><span>{_esc(item['category'])}</span><span>·</span><span>{_esc(item['condition'])}</span></div>
            <h3>{_esc(item['title'])}</h3>
            <p class="item-description">{_esc(item['description'])}</p>
            <div class="item-bottom"><div><strong>{_money(item['price'])}</strong><small>Seller: {_esc(item['seller'])}</small></div><div class="pickup">📍 {_esc(item['pickup'])}</div></div>
          </div>
        </article>
        """)
    return f'<div class="listings-grid">{"".join(cards)}</div><div class="result-count">Showing {len(visible)} campus find(s)</div>'


def update_marketplace(listings, query, category):
    return render_listings(listings, query, category)


def listing_choices(listings):
    # Store stable IDs as values; labels remain easy to understand.
    return [(f"{item['title']} · {_money(item['price'])} · {item['seller']}", item['id']) for item in listings]


def add_listing(title, category, price, condition, seller, description, pickup, listings, query, filter_category):
    if not (title or "").strip():
        return "Add a title before publishing.", listings, render_listings(listings, query, filter_category), gr.update(choices=listing_choices(listings), value=(listings[0]["id"] if listings else None))
    if not (seller or "").strip():
        return "Add a seller nickname (not a phone number or private contact detail).", listings, render_listings(listings, query, filter_category), gr.update(choices=listing_choices(listings), value=(listings[0]["id"] if listings else None))
    try:
        price_value = int(price)
    except (ValueError, TypeError):
        price_value = -1
    if price_value < 0 or price_value > 100000:
        return "Enter a price between ₹0 and ₹100,000.", listings, render_listings(listings, query, filter_category), gr.update(choices=listing_choices(listings), value=(listings[0]["id"] if listings else None))
    clean_title = title.strip()
    new_item = {
        "id": f"local-{len(listings) + 1}-{abs(hash(clean_title)) % 100000}",
        "title": clean_title[:80], "category": category, "price": price_value,
        "condition": condition, "seller": seller.strip()[:40],
        "description": (description or "No description added yet.").strip()[:500],
        "pickup": pickup, "emoji": EMOJI_BY_CATEGORY.get(category, "✨"), "demo": False,
    }
    updated = [new_item] + list(listings)
    return "Your item has been added to this session's marketplace preview. It is not saved or visible to other devices.", updated, render_listings(updated, query, filter_category), gr.update(choices=listing_choices(updated), value=new_item["id"])


def improve_description(title, category, condition, price, description):
    if not (title or "").strip():
        return "Add an item title first, then ask Gemma to polish the listing."
    prompt = f"""You are helping a student write an honest listing for a college-campus second-hand marketplace.
Rewrite this item listing so it is clear, friendly, accurate, and easy for another student to understand.
Do not invent features, condition details, warranties, or claims. Keep it under 90 words. Return only the improved listing description, with no preamble.
Item title: {title.strip()}
Category: {category}
Condition: {condition}
Asking price: ₹{price}
Current description: {(description or '').strip() or 'No description supplied.'}
Include a gentle reminder to inspect the item at the campus pickup point if appropriate."""
    try:
        # Exactly one model inference for this click.
        return ask(prompt)
    except Exception as exc:
        return f"Gemma couldn't complete the request. Check your .env and internet connection. Error type: {type(exc).__name__}"


def review_photo(image_file, title, condition):
    if image_file is None:
        return "Upload a product photo first."
    prompt = f"""You are a careful marketplace listing assistant for a college campus. Review the uploaded item's photo for listing quality.
Item title entered by seller: {title or 'Not provided'}
Claimed condition: {condition or 'Not provided'}
In 3 short bullet points, describe only visible details, note whether the photo is clear enough for a listing, and suggest one extra photo angle a buyer may want. Do not identify people, infer personal traits, or claim the item works based on a photo. Do not estimate price."""
    try:
        # Exactly one model inference for this click; the helper handles image upload.
        return ask_with_image(prompt, image_file)
    except Exception as exc:
        return f"Photo review failed. Check your .env and internet connection. Error type: {type(exc).__name__}"


def draft_buyer_message(selected_id, buyer_nickname, listings):
    item = next((entry for entry in listings if entry["id"] == selected_id), None)
    if item is None:
        return "Choose a listing first."
    nickname = (buyer_nickname or "a fellow student").strip()[:40]
    prompt = f"""You help students communicate politely about items on a college-campus marketplace.
Draft one short, friendly, non-pushy message from buyer nickname '{nickname}' to ask about this listing:
Item: {item['title']}
Price: ₹{item['price']}
Condition: {item['condition']}
Pickup point: {item['pickup']}
Do not invent phone numbers, usernames, payment links, or facts. Ask whether the item is still available and propose meeting in a public campus spot. Output only the message."""
    try:
        # make_chat creates a fresh chat; one send_message means one Gemma inference for this click.
        chat = make_chat()
        response = chat.send_message(prompt)
        return (getattr(response, "text", None) or "Gemma returned an empty response.").strip()
    except Exception as exc:
        return f"Message drafting failed. Check your .env and internet connection. Error type: {type(exc).__name__}"


CSS = r"""
:root { --ink:#14251f; --muted:#66756f; --green:#1e5a46; --lime:#c7f36b; --cream:#f8f8f1; --line:#e3e8e0; }
.gradio-container { max-width: 1440px !important; margin: 0 auto !important; background: var(--cream) !important; font-family: Inter, ui-sans-serif, system-ui, sans-serif !important; }
body, .contain { background: var(--cream) !important; }
#hero { background: #173f32; color:#fff; padding:28px 32px 26px; border-radius:22px; margin: 4px 0 18px; position:relative; overflow:hidden; }
#hero:after { content:""; position:absolute; width:260px; height:260px; border-radius:50%; background:rgba(199,243,107,.12); right:5%; top:-145px; }
.brandline { display:flex; align-items:center; gap:10px; font-size:13px; letter-spacing:1.6px; text-transform:uppercase; color:#d2e4dc; font-weight:750; }
.brandmark { background:var(--lime); color:#183b30; width:32px; height:32px; border-radius:10px; display:inline-grid; place-items:center; font-size:19px; }
.hero-title { font-size:clamp(32px, 4vw, 50px); line-height:1.02; font-weight:850; letter-spacing:-1.8px; margin:20px 0 10px; max-width:800px; }
.hero-title em { color:var(--lime); font-style:normal; }
.hero-copy { color:#d5e4dd; max-width:660px; font-size:15px; line-height:1.6; margin:0; }
.hero-tags { display:flex; flex-wrap:wrap; gap:8px; margin-top:20px; }
.hero-tag { font-size:12px; color:#edf5ef; border:1px solid #4d7565; padding:7px 10px; border-radius:100px; }
.section-heading h2 { color:var(--ink); font-size:21px; letter-spacing:-.4px; margin:0 0 4px; }
.section-heading p { color:var(--muted); margin:0 0 14px; font-size:13px; }
.panel { background:white; border:1px solid var(--line); border-radius:18px; padding:18px; }
.panel-heading { color:var(--ink); font-size:17px; font-weight:780; margin:0 0 3px; }
.panel-sub { color:var(--muted); font-size:12px; margin:0 0 14px; }
#listing-grid { background:transparent; border:0; padding:0; }
.listings-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }
.listing-card { min-width:0; overflow:hidden; background:#fff; border:1px solid #e5e9e2; border-radius:16px; box-shadow:0 3px 12px rgba(26,45,35,.035); }
.item-art { height:104px; display:flex; align-items:center; justify-content:center; position:relative; background:linear-gradient(135deg,#e4f1d6,#f2f6e9); }
.item-art span { font-size:44px; filter:drop-shadow(0 4px 4px rgba(30,60,42,.10)); }
.demo-pill,.fresh-pill { position:absolute; top:9px; left:9px; font-size:9px; letter-spacing:.5px; font-weight:800; padding:5px 6px; border-radius:6px; background:#f6f7f2; color:#6c776e; }
.fresh-pill { background:#e6f8bf; color:#315b2a; }
.item-content { padding:13px; }
.item-meta { display:flex; gap:5px; flex-wrap:wrap; color:#78847c; font-size:10px; font-weight:650; margin-bottom:6px; }
.item-content h3 { color:var(--ink); font-size:15px; line-height:1.3; margin:0 0 6px; font-weight:780; }
.item-description { color:#66736b; font-size:11px; line-height:1.5; min-height:34px; margin:0 0 14px; }
.item-bottom { padding-top:10px; border-top:1px solid #edf0ea; display:flex; justify-content:space-between; gap:8px; align-items:end; }
.item-bottom strong { display:block; font-size:17px; color:#1d533d; }
.item-bottom small { display:block; color:#7b867e; font-size:10px; margin-top:3px; }
.pickup { font-size:10px; text-align:right; color:#718077; }
.result-count { color:#738078; font-size:11px; margin:9px 0 0 2px; }
.empty-state { text-align:center; background:white; border:1px dashed #dbe2d8; padding:36px 15px; border-radius:16px; color:#66756f; }
.empty-icon { font-size:30px; margin-bottom:8px; }
.empty-state b { color:#20382d; }
.empty-state p { font-size:12px; }
.primary-btn button { background:#c7f36b !important; color:#193d30 !important; border:0 !important; border-radius:12px !important; font-weight:800 !important; }
.secondary-btn button { border:1px solid #dbe4da !important; background:#f5f8f0 !important; color:#244c3b !important; border-radius:12px !important; font-weight:750 !important; }
button { transition:transform .15s ease, box-shadow .15s ease; }
button:hover { transform:translateY(-1px); }
label span { color:#33483c !important; font-weight:650 !important; }
input, textarea, select { border-radius:10px !important; }
.output-card { background:#f6f9f2; border:1px solid #e0e9d8; border-radius:12px; padding:14px; color:#273a2f; font-size:13px; line-height:1.6; white-space:pre-wrap; }
#fine-print { color:#718078; font-size:11px; text-align:center; padding:18px 0 4px; }
@media (max-width: 1000px) { .listings-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width: 650px) { #hero { padding:23px 19px; border-radius:17px; } .listings-grid { grid-template-columns:1fr; } .item-art { height:95px; } }
"""

with gr.Blocks(title="CampusLoop · Student Marketplace") as demo:
    listings_state = gr.State(SEED_LISTINGS.copy())

    gr.HTML("""
    <header id="hero">
      <div class="brandline"><span class="brandmark">↗</span> CampusLoop <span style="opacity:.65;font-weight:500">/ Student-to-student marketplace</span></div>
      <div class="hero-title">Good stuff deserves<br><em>a second campus life.</em></div>
      <p class="hero-copy">Buy and sell the things students actually need — books, room essentials, gadgets and more. Keep it local, affordable, and circular.</p>
      <div class="hero-tags"><span class="hero-tag">♻️ Give items another life</span><span class="hero-tag">🎓 Made for campus</span><span class="hero-tag">📍 Meet at public pickup spots</span></div>
    </header>
    """)

    with gr.Row(equal_height=False):
        with gr.Column(scale=5, min_width=300):
            gr.HTML('<div class="section-heading"><h2>Put an item up for sale</h2><p>List it in a few details. No account required for this demo.</p></div>')
            with gr.Group(elem_classes=["panel"]):
                gr.HTML('<div class="panel-heading">Create a listing</div><div class="panel-sub">Be honest about its condition. Buyers appreciate the details.</div>')
                item_title = gr.Textbox(label="Item name", placeholder="e.g. First-year physics textbook", max_lines=1)
                with gr.Row():
                    item_category = gr.Dropdown(CATEGORIES, value="Books & Notes", label="Category", scale=2)
                    item_price = gr.Number(label="Price (₹)", value=100, precision=0, minimum=0, maximum=100000, scale=1)
                with gr.Row():
                    item_condition = gr.Dropdown(["Like new", "Good", "Used", "For parts / repair"], value="Good", label="Condition")
                    seller_name = gr.Textbox(label="Seller nickname", placeholder="e.g. Adi", max_lines=1)
                item_description = gr.Textbox(label="Description", placeholder="Mention what is included, any wear, and useful details…", lines=3, max_lines=4)
                pickup_point = gr.Dropdown(PICKUP_POINTS, value="Library Entrance", label="Suggested public campus pickup")
                add_button = gr.Button("＋  Add listing to marketplace", elem_classes=["primary-btn"], variant="primary")
                listing_status = gr.Markdown()

            gr.HTML('<div style="height:12px"></div><div class="section-heading"><h2>Gemma listing assistant</h2><p>Helpful AI tools, each triggered only when you click.</p></div>')
            with gr.Group(elem_classes=["panel"]):
                gr.HTML('<div class="panel-heading">Polish your description</div><div class="panel-sub">Gemma keeps it clear without inventing item details.</div>')
                improve_button = gr.Button("✦  Improve with Gemma", elem_classes=["secondary-btn"])
                improved_description = gr.Textbox(label="Improved description", lines=4, interactive=False, placeholder="Your improved copy will appear here.")
                improve_button.click(
                    fn=improve_description,
                    inputs=[item_title, item_category, item_condition, item_price, item_description],
                    outputs=improved_description,
                )

            with gr.Group(elem_classes=["panel"]):
                gr.HTML('<div class="panel-heading">Check your product photo</div><div class="panel-sub">Get practical listing-photo feedback, not a made-up appraisal.</div>')
                photo_file = gr.File(label="Upload a product photo", file_types=["image"], type="filepath")
                photo_button = gr.Button("▧  Review photo with Gemma", elem_classes=["secondary-btn"])
                photo_feedback = gr.Textbox(label="Photo feedback", lines=4, interactive=False, placeholder="Photo tips will appear here.")
                photo_button.click(fn=review_photo, inputs=[photo_file, item_title, item_condition], outputs=photo_feedback)

        with gr.Column(scale=7, min_width=360):
            gr.HTML('<div class="section-heading"><h2>Explore campus finds</h2><p>Sample listings are included so the marketplace looks alive on first launch.</p></div>')
            with gr.Row():
                search_box = gr.Textbox(placeholder="Search books, lamps, mouse…", label="Find an item", scale=3, max_lines=1)
                category_filter = gr.Dropdown(["All categories"] + CATEGORIES, value="All categories", label="Category", scale=2)
            listing_grid = gr.HTML(render_listings(SEED_LISTINGS), elem_id="listing-grid")
            search_box.change(fn=update_marketplace, inputs=[listings_state, search_box, category_filter], outputs=listing_grid)
            category_filter.change(fn=update_marketplace, inputs=[listings_state, search_box, category_filter], outputs=listing_grid)

            with gr.Group(elem_classes=["panel"]):
                gr.HTML('<div class="panel-heading">Interested in something?</div><div class="panel-sub">Draft a friendly message and arrange a public campus meetup. This demo does not send messages.</div>')
                selected_listing = gr.Dropdown(choices=listing_choices(SEED_LISTINGS), value=SEED_LISTINGS[0]["id"], label="Choose a listing")
                buyer_nickname = gr.Textbox(label="Your nickname (optional)", placeholder="e.g. Adi", max_lines=1)
                draft_button = gr.Button("✦  Draft a buyer message with Gemma", elem_classes=["secondary-btn"])
                buyer_message = gr.Textbox(label="Message draft", lines=4, interactive=False, placeholder="Your message draft will appear here.")
                draft_button.click(fn=draft_buyer_message, inputs=[selected_listing, buyer_nickname, listings_state], outputs=buyer_message)

            gr.HTML("""
            <div style="margin-top:12px;border:1px solid #e0e8d9;border-radius:16px;padding:15px 17px;background:#eef5e7;">
              <div style="font-weight:800;color:#234b37;font-size:14px;margin-bottom:6px">Campus-safe exchange checklist</div>
              <div style="font-size:12px;line-height:1.7;color:#52695a">✓ Meet in a busy public campus location<br>✓ Inspect the item before paying<br>✓ Agree on the price directly and never share passwords or OTPs<br>✓ Keep personal phone numbers and home addresses out of listings</div>
            </div>
            """)

    gr.HTML('<div id="fine-print">CampusLoop is a hackathon prototype · Listings stay in this browser session only · No payments, messaging, login, or database</div>')

    add_button.click(
        fn=add_listing,
        inputs=[item_title, item_category, item_price, item_condition, seller_name, item_description, pickup_point, listings_state, search_box, category_filter],
        outputs=[listing_status, listings_state, listing_grid, selected_listing],
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(primary_hue="green", neutral_hue="slate"), css=CSS)
